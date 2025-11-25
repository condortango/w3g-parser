package w3g

import (
	"encoding/binary"
	"io"
	"os"
)

// Parser is the main W3G replay parser.
type Parser struct {
	Strict bool // If true, fail on unknown data; otherwise skip and log
}

// NewParser creates a new parser instance.
func NewParser() *Parser {
	return &Parser{Strict: false}
}

// Parse parses a complete replay file.
func (p *Parser) Parse(filepath string) (*W3GReplay, error) {
	f, err := os.Open(filepath)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	// 1. Parse header
	header, _, err := parseHeader(f)
	if err != nil {
		return nil, err
	}

	// 2. Seek to first data block (header already read, seek to header size position)
	_, err = f.Seek(int64(header.HeaderSize), 0)
	if err != nil {
		return nil, err
	}

	// 3. Decompress all blocks
	decompressed, err := decompressBlocks(f, header)
	if err != nil {
		return nil, err
	}

	// 4. Parse game data
	return p.parseGameData(header, decompressed)
}

// ParseStream parses a replay from an io.Reader.
func (p *Parser) ParseStream(r io.Reader) (*W3GReplay, error) {
	// 1. Parse header
	header, _, err := parseHeader(r)
	if err != nil {
		return nil, err
	}

	// 2. Decompress all blocks
	decompressed, err := decompressBlocks(r, header)
	if err != nil {
		return nil, err
	}

	// 3. Parse game data
	return p.parseGameData(header, decompressed)
}

// ParseHeaderOnly parses just the header (for quick metadata access).
func (p *Parser) ParseHeaderOnly(filepath string) (*ReplayHeader, error) {
	f, err := os.Open(filepath)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	header, _, err := parseHeader(f)
	return header, err
}

// IterActions returns a channel for iterating actions without loading all into memory.
func (p *Parser) IterActions(filepath string) (<-chan *GameAction, <-chan error) {
	actionCh := make(chan *GameAction)
	errCh := make(chan error, 1)

	go func() {
		defer close(actionCh)
		defer close(errCh)

		replay, err := p.Parse(filepath)
		if err != nil {
			errCh <- err
			return
		}

		for _, action := range replay.Actions {
			actionCh <- action
		}
	}()

	return actionCh, errCh
}

// parseGameData parses decompressed game data.
func (p *Parser) parseGameData(header *ReplayHeader, data []byte) (*W3GReplay, error) {
	offset := 0
	players := make([]*PlayerInfo, 0)
	chatMessages := make([]*ChatMessage, 0)
	actions := make([]*GameAction, 0)

	gameName := ""
	mapName := ""
	mapPath := ""
	hostName := ""
	settings := &GameSettings{Speed: 2}

	// Track current game time
	currentTimeMs := uint32(0)

	// Player ID to name mapping for chat
	playerNames := make(map[uint8]string)

	// Skip first 4 bytes (unknown, usually 0x00000110)
	if offset+4 <= len(data) {
		offset += 4
	}

	// Parse host player record
	hostPlayer, newOffset := parsePlayerRecord(data, offset, true)
	if hostPlayer != nil {
		hostPlayer.IsHost = true
		players = append(players, hostPlayer)
		playerNames[hostPlayer.ID] = hostPlayer.Name
		hostName = hostPlayer.Name
		offset = newOffset
	}

	// Parse game name (null-terminated)
	gameNameStart := offset
	for offset < len(data) && data[offset] != 0 {
		offset++
	}
	gameName = string(data[gameNameStart:offset])
	offset++ // Skip null

	// Skip another null byte (separator)
	if offset < len(data) && data[offset] == 0 {
		offset++
	}

	// Parse encoded string containing game settings and map info
	encodedData, newOffset := decodeEncodedString(data, offset)
	offset = newOffset
	if len(encodedData) > 0 {
		settings, mapPath, mapName = parseEncodedSettings(encodedData)
	}

	// Parse player count, game type, language ID
	if offset+12 <= len(data) {
		// playerCount := binary.LittleEndian.Uint32(data[offset:])
		offset += 4
		// gameType := binary.LittleEndian.Uint32(data[offset:])
		offset += 4
		// languageID := binary.LittleEndian.Uint32(data[offset:])
		offset += 4
	}

	// Parse additional players
	for offset < len(data) {
		player, newOffset := parsePlayerRecord(data, offset, false)
		if player != nil {
			players = append(players, player)
			playerNames[player.ID] = player.Name
			offset = newOffset
		} else {
			break
		}
	}

	// Reforged replays have extra player metadata between player records
	// and the GameStartRecord (0x19). Skip to find it.
	if offset < len(data) && !isValidGameStartRecord(data, offset) {
		// Search for valid GameStartRecord marker
		searchOffset := offset
		for searchOffset < len(data)-4 {
			if data[searchOffset] == BlockGameStart {
				if isValidGameStartRecord(data, searchOffset) {
					break
				}
			}
			searchOffset++
		}
		if searchOffset < len(data) && isValidGameStartRecord(data, searchOffset) {
			offset = searchOffset
		}
	}

	// Parse GameStartRecord (0x19)
	if offset < len(data) && data[offset] == BlockGameStart {
		slots, _, _, newOffset := parseGameStartRecord(data, offset, header.Version)
		offset = newOffset
		// Apply slot info to players
		applySlotInfoToPlayers(players, slots, header.Version)
	}

	// Parse replay data blocks
	for offset < len(data) {
		if offset >= len(data) {
			break
		}

		blockID := data[offset]
		offset++

		switch blockID {
		case BlockLeaveGame:
			// 14 bytes total: reason (4) + player_id (1) + result (4) + unknown (4)
			if offset+13 <= len(data) {
				// reason := binary.LittleEndian.Uint32(data[offset:])
				offset += 4
				leavePlayerID := data[offset]
				offset++
				result := binary.LittleEndian.Uint32(data[offset:])
				offset += 4
				offset += 4 // Unknown

				// Update player leave info
				for _, player := range players {
					if player.ID == leavePlayerID {
						leaveResult := LeaveResult(result)
						player.LeaveResult = &leaveResult
						player.LeaveTimeMs = &currentTimeMs
						break
					}
				}
			}

		case BlockFirstStart, BlockSecondStart, BlockThirdStart:
			// 5 bytes: unknown dword (always 0x01)
			offset += 4

		case BlockTimeSlot, BlockTimeSlotOld:
			// TimeSlot block
			if offset+4 <= len(data) {
				numBytes := binary.LittleEndian.Uint16(data[offset:])
				offset += 2
				timeIncrement := binary.LittleEndian.Uint16(data[offset:])
				offset += 2

				currentTimeMs += uint32(timeIncrement)

				// Parse command data (numBytes - 2 for time increment already read)
				if numBytes > 2 {
					cmdLength := int(numBytes - 2)
					cmdActions := parseCommandData(data, offset, cmdLength, header.Version)
					for _, ca := range cmdActions {
						ca.Action.TimestampMs = currentTimeMs
						actions = append(actions, ca.Action)

						// Update player action count
						for _, player := range players {
							if player.ID == ca.PlayerID {
								player.ActionCount++
								break
							}
						}
					}
					offset += cmdLength
				}
			}

		case BlockChat:
			// Chat message (v1.07+)
			chatMsg, newOffset := parseChatMessage(data, offset, playerNames)
			if chatMsg != nil {
				chatMsg.TimestampMs = currentTimeMs
				chatMessages = append(chatMessages, chatMsg)
			}
			offset = newOffset

		case BlockChecksum:
			// Checksum block: 1 byte length + data
			if offset < len(data) {
				length := data[offset]
				offset += 1 + int(length)
			}

		case BlockForcedEnd:
			// Forced end: mode (4) + countdown (4)
			offset += 8

		case 0x23:
			// Unknown block type seen in some replays
			if offset < len(data) {
				length := data[offset]
				offset += 1 + int(length)
			}

		default:
			// Unknown block - try to continue
			if !p.Strict {
				continue
			}
			break
		}
	}

	// Calculate APM for each player
	durationMinutes := float64(header.DurationMs) / 60000.0
	if durationMinutes > 0 {
		for _, player := range players {
			player.APM = float64(player.ActionCount) / durationMinutes
		}
	}

	return &W3GReplay{
		Header:          header,
		GameName:        gameName,
		MapName:         mapName,
		MapPath:         mapPath,
		HostName:        hostName,
		Settings:        settings,
		Players:         players,
		ChatMessages:    chatMessages,
		Actions:         actions,
		RawDecompressed: data,
	}, nil
}
