package w3g

import (
	"encoding/binary"
	"fmt"
)

// parsePlayerRecord parses a player record from decompressed data.
//
// Player record structure:
//   - 1 byte: Record ID (0x00 for host, 0x16 for additional)
//   - 1 byte: Player ID
//   - n bytes: Player name (null-terminated)
//   - 1 byte: Additional data size (0x01 for custom, 0x08 for ladder)
//   - Additional data (1 or 8 bytes)
func parsePlayerRecord(data []byte, offset int, isHost bool) (*PlayerInfo, int) {
	if offset >= len(data) {
		return nil, offset
	}

	recordID := data[offset]
	offset++

	// Validate record ID
	expectedID := uint8(RecordAdditionalPlayer)
	if isHost {
		expectedID = RecordHost
	}
	if recordID != expectedID {
		// Not a player record, backtrack
		return nil, offset - 1
	}

	if offset >= len(data) {
		return nil, offset
	}

	playerID := data[offset]
	offset++

	// Read player name (null-terminated)
	nameStart := offset
	for offset < len(data) && data[offset] != 0 {
		offset++
	}
	name := string(data[nameStart:offset])
	offset++ // Skip null terminator

	if offset >= len(data) {
		return &PlayerInfo{ID: playerID, Name: name, IsHost: isHost, Handicap: 100}, offset
	}

	// Additional data size
	extraSize := data[offset]
	offset++

	runtimeMs := uint32(0)
	race := RaceUnknown

	if extraSize == 0x01 {
		// Custom game: 1 null byte
		offset++
	} else if extraSize == 0x08 {
		// Ladder game: 4 bytes runtime + 4 bytes race flags
		if offset+8 <= len(data) {
			runtimeMs = binary.LittleEndian.Uint32(data[offset:])
			offset += 4
			raceFlags := binary.LittleEndian.Uint32(data[offset:])
			offset += 4
			race = RaceFromFlags(uint8(raceFlags))
		}
	} else {
		// Unknown format, skip reported bytes
		offset += int(extraSize)
	}

	return &PlayerInfo{
		ID:        playerID,
		Name:      name,
		Race:      race,
		IsHost:    isHost,
		RuntimeMs: runtimeMs,
		Handicap:  100,
	}, offset
}

// parseSlotRecord parses a slot record from GameStartRecord.
//
// Slot record structure (varies by version):
//   - 1 byte: Player ID (0x00 for computer)
//   - 1 byte: Download percent
//   - 1 byte: Slot status
//   - 1 byte: Computer flag
//   - 1 byte: Team number
//   - 1 byte: Color
//   - 1 byte: Race flags
//   - 1 byte: AI strength (v1.03+)
//   - 1 byte: Handicap (v1.07+)
func parseSlotRecord(data []byte, offset int, version uint32) (*SlotRecord, int) {
	// Determine slot size based on version
	slotSize := 9
	if version < 3 {
		slotSize = 7
	} else if version < 7 {
		slotSize = 8
	}

	if offset+slotSize > len(data) {
		return nil, offset
	}

	slot := &SlotRecord{
		PlayerID:        data[offset],
		DownloadPercent: data[offset+1],
		SlotStatus:      data[offset+2],
		IsComputer:      data[offset+3] == 0x01,
		Team:            data[offset+4],
		Color:           data[offset+5],
		RaceFlags:       data[offset+6],
		Handicap:        100,
	}

	if slotSize >= 8 {
		slot.AIStrength = data[offset+7]
	}
	if slotSize >= 9 {
		slot.Handicap = data[offset+8]
	}

	return slot, offset + slotSize
}

// parseGameStartRecord parses the GameStartRecord.
//
// Structure:
//   - 1 byte: Record ID (0x19)
//   - 1 word: Number of following data bytes
//   - 1 byte: Number of slot records
//   - n slot records
//   - 1 dword: Random seed
//   - 1 byte: Select mode
//   - 1 byte: Start spot count
func parseGameStartRecord(data []byte, offset int, version uint32) ([]*SlotRecord, uint32, uint8, int) {
	if offset >= len(data) || data[offset] != BlockGameStart {
		return nil, 0, 0, offset
	}

	offset++

	if offset+2 > len(data) {
		return nil, 0, 0, offset
	}

	// Number of following bytes
	// numBytes := binary.LittleEndian.Uint16(data[offset:])
	offset += 2

	if offset >= len(data) {
		return nil, 0, 0, offset
	}

	// Number of slot records
	numSlots := data[offset]
	offset++

	// Parse slot records
	slots := make([]*SlotRecord, 0, numSlots)
	for i := uint8(0); i < numSlots; i++ {
		slot, newOffset := parseSlotRecord(data, offset, version)
		if slot != nil {
			slots = append(slots, slot)
		}
		offset = newOffset
	}

	// Random seed
	randomSeed := uint32(0)
	if offset+4 <= len(data) {
		randomSeed = binary.LittleEndian.Uint32(data[offset:])
		offset += 4
	}

	// Select mode
	selectMode := uint8(0)
	if offset < len(data) {
		selectMode = data[offset]
		offset++
	}

	// Start spot count
	if offset < len(data) {
		offset++ // Skip start spot count
	}

	return slots, randomSeed, selectMode, offset
}

// applySlotInfoToPlayers applies slot information to player records.
func applySlotInfoToPlayers(players []*PlayerInfo, slots []*SlotRecord, version uint32) {
	// Build player ID to player mapping
	playerMap := make(map[uint8]*PlayerInfo)
	for _, p := range players {
		playerMap[p.ID] = p
	}

	// Observer team ID depends on version
	observerTeam := uint8(ObserverTeamClassic)
	if version >= ReforgedVersionThreshold {
		observerTeam = ObserverTeamReforged
	}

	for _, slot := range slots {
		if slot.SlotStatus != uint8(SlotUsed) {
			continue
		}

		if slot.IsComputer {
			// Create computer player
			computer := &PlayerInfo{
				ID:         slot.PlayerID,
				Name:       fmt.Sprintf("Computer %d", slot.PlayerID),
				IsComputer: true,
				Team:       slot.Team,
				Color:      slot.Color,
				Race:       RaceFromFlags(slot.RaceFlags),
				Handicap:   slot.Handicap,
				SlotStatus: SlotUsed,
			}
			players = append(players, computer)
		} else if player, ok := playerMap[slot.PlayerID]; ok {
			// Update existing player
			player.Team = slot.Team
			player.Color = slot.Color
			player.Handicap = slot.Handicap
			player.SlotStatus = SlotStatus(slot.SlotStatus)

			// Set race if not already set from ladder info
			if player.Race == RaceUnknown {
				player.Race = RaceFromFlags(slot.RaceFlags)
			}

			// Check if observer
			if player.Team == observerTeam {
				player.IsObserver = true
			}
		}
	}
}

// isValidGameStartRecord checks if offset points to a valid GameStartRecord.
func isValidGameStartRecord(data []byte, offset int) bool {
	if offset+4 > len(data) || data[offset] != BlockGameStart {
		return false
	}
	numBytes := binary.LittleEndian.Uint16(data[offset+1:])
	if numBytes < 10 || numBytes > 500 { // Reasonable range
		return false
	}
	numSlots := data[offset+3]
	return numSlots >= 2 && numSlots <= 24
}
