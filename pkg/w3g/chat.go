package w3g

import (
	"encoding/binary"
	"fmt"
)

// parseChatMessage parses a chat message block.
//
// Chat message structure (v1.07+):
//   - 1 byte: Sender ID
//   - 1 word: Message length (n)
//   - 1 byte: Flags (0x10=startup, 0x20=normal)
//   - 1 dword: Chat mode (if flag=0x20): 0=all, 1=allies, 2=observers, 3+=player
//   - n bytes: Message text (null-terminated)
func parseChatMessage(data []byte, offset int, playerNames map[uint8]string) (*ChatMessage, int) {
	if offset+4 > len(data) {
		return nil, offset
	}

	playerID := data[offset]
	offset++

	_ = binary.LittleEndian.Uint16(data[offset:]) // msgLength - not used
	offset += 2

	flags := data[offset]
	offset++

	mode := uint32(0)
	isStartup := false

	if flags == ChatFlagStartup {
		isStartup = true
	} else if flags == ChatFlagNormal {
		if offset+4 <= len(data) {
			mode = binary.LittleEndian.Uint32(data[offset:])
			offset += 4
		}
	}
	// Unknown flag - try to continue

	// Read message text
	msgStart := offset
	for offset < len(data) && data[offset] != 0 {
		offset++
	}
	message := string(data[msgStart:offset])
	offset++ // Skip null terminator

	playerName := playerNames[playerID]
	if playerName == "" {
		playerName = fmt.Sprintf("Player %d", playerID)
	}

	return &ChatMessage{
		TimestampMs: 0, // Set by caller
		PlayerID:    playerID,
		PlayerName:  playerName,
		Message:     message,
		Mode:        mode,
		IsStartup:   isStartup,
	}, offset
}
