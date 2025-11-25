package w3g

import (
	"encoding/binary"
	"fmt"
	"math"
)

// decodeItemID decodes a 4-byte item/ability ID to human-readable string.
//
// Item IDs come in two formats:
// 1. String IDs: 4 ASCII chars in reverse order (e.g., "tlah" -> "halt")
// 2. Numeric IDs: XX XX 0D 00 format for ability commands
func decodeItemID(itemBytes []byte) string {
	if len(itemBytes) != 4 {
		return fmt.Sprintf("%x", itemBytes)
	}

	// Check if numeric ID (XX XX 0D 00)
	if itemBytes[2] == 0x0d && itemBytes[3] == 0x00 {
		abilityNum := binary.LittleEndian.Uint16(itemBytes[0:2])
		key := fmt.Sprintf("ability_%d", abilityNum)
		if name, ok := ItemIDNames[key]; ok {
			return name
		}
		return key
	}

	// Try to decode as string ID
	isValid := true
	for _, b := range itemBytes {
		if b != 0 && (b < 0x20 || b > 0x7E) {
			isValid = false
			break
		}
	}

	if isValid {
		// Reverse the string (WC3 stores them backwards)
		code := make([]byte, 0, 4)
		for i := 3; i >= 0; i-- {
			if itemBytes[i] != 0 {
				code = append(code, itemBytes[i])
			}
		}
		codeStr := string(code)
		if name, ok := ItemIDNames[codeStr]; ok {
			return name
		}
		if len(codeStr) > 0 {
			return codeStr
		}
	}

	return fmt.Sprintf("%x", itemBytes)
}

// parseAction parses a single action from action block data.
func parseAction(data []byte, offset int, version uint32) (*GameAction, int) {
	if offset >= len(data) {
		return nil, offset
	}

	actionID := data[offset]
	startOffset := offset
	offset++

	actionName := ActionNames[actionID]
	if actionName == "" {
		actionName = fmt.Sprintf("unknown_%02x", actionID)
	}
	actionData := make(map[string]interface{})

	switch actionID {
	case ActionPause:
		// 1 byte total

	case ActionResume:
		// 1 byte total

	case ActionSetSpeed:
		if offset < len(data) {
			actionData["speed"] = data[offset]
			offset++
		}

	case ActionIncSpeed, ActionDecSpeed:
		// 1 byte total

	case ActionSaveGame:
		// Variable: null-terminated filename
		nameStart := offset
		for offset < len(data) && data[offset] != 0 {
			offset++
		}
		actionData["filename"] = string(data[nameStart:offset])
		offset++ // Skip null

	case ActionSaveFinished:
		offset += 4 // Unknown dword

	case ActionAbilityNoParams:
		// AbilityFlags (1 word for v1.13+, 1 byte for older)
		// ItemID (4 bytes)
		// Unknown data
		actionSize := 14
		if version < 13 {
			actionSize = 13
		}
		if offset+actionSize-1 <= len(data) {
			flagsSize := 2
			if version < 13 {
				flagsSize = 1
			}
			if flagsSize == 2 {
				actionData["ability_flags"] = binary.LittleEndian.Uint16(data[offset:])
			} else {
				actionData["ability_flags"] = uint16(data[offset])
			}
			offset += flagsSize
			actionData["item_id"] = data[offset : offset+4]
			offset += actionSize - 1 - flagsSize
		}

	case ActionAbilityTargetPos:
		// Structure: flags(2) + item_id(4) + unknown(8) + x(4) + y(4) = 22 bytes
		actionSize := 22
		if version < 13 {
			actionSize = 21
		}
		if offset+actionSize-1 <= len(data) {
			flagsSize := 2
			if version < 13 {
				flagsSize = 1
			}
			if flagsSize == 2 {
				actionData["ability_flags"] = binary.LittleEndian.Uint16(data[offset:])
			} else {
				actionData["ability_flags"] = uint16(data[offset])
			}
			offset += flagsSize
			actionData["item_id"] = data[offset : offset+4]
			offset += 4
			offset += 8 // unknowns
			if offset+8 <= len(data) {
				x := math.Float32frombits(binary.LittleEndian.Uint32(data[offset:]))
				y := math.Float32frombits(binary.LittleEndian.Uint32(data[offset+4:]))
				actionData["target_x"] = x
				actionData["target_y"] = y
			}
			offset += 8
		}

	case ActionAbilityPosObject:
		// Structure: flags(2) + item_id(4) + unknown(8) + x(4) + y(4) + obj1(4) + obj2(4)
		actionSize := 26
		if version < 13 {
			actionSize = 25
		}
		if offset+actionSize-1 <= len(data) {
			flagsSize := 2
			if version < 13 {
				flagsSize = 1
			}
			if flagsSize == 2 {
				actionData["ability_flags"] = binary.LittleEndian.Uint16(data[offset:])
			} else {
				actionData["ability_flags"] = uint16(data[offset])
			}
			offset += flagsSize
			actionData["item_id"] = data[offset : offset+4]
			offset += 4
			offset += 8 // unknowns
			if offset+8 <= len(data) {
				x := math.Float32frombits(binary.LittleEndian.Uint32(data[offset:]))
				y := math.Float32frombits(binary.LittleEndian.Uint32(data[offset+4:]))
				actionData["target_x"] = x
				actionData["target_y"] = y
			}
			offset += 8
			// Object IDs
			if offset+4 <= len(data) {
				actionData["object_id_1"] = binary.LittleEndian.Uint32(data[offset:])
				offset += 4
			}
			if offset+4 <= len(data) {
				actionData["object_id_2"] = binary.LittleEndian.Uint32(data[offset:])
				offset += 4
			}
		}

	case ActionAbilityDropItem:
		actionSize := 37
		if version >= 13 {
			actionSize = 38
		}
		offset += actionSize - 1

	case ActionAbilityTwoPos:
		actionSize := 42
		if version >= 13 {
			actionSize = 43
		}
		offset += actionSize - 1

	case ActionChangeSelection:
		// 1 byte: select mode (1=add, 2=remove)
		// 1 word: unit count
		// n * 8 bytes: object IDs (2 dwords per unit)
		if offset+3 <= len(data) {
			actionData["select_mode"] = data[offset]
			offset++
			unitCount := binary.LittleEndian.Uint16(data[offset:])
			offset += 2
			actionData["unit_count"] = unitCount
			// Parse object IDs
			objectIDs := make([]uint32, 0, unitCount)
			for i := uint16(0); i < unitCount; i++ {
				if offset+8 <= len(data) {
					objID := binary.LittleEndian.Uint32(data[offset:])
					objectIDs = append(objectIDs, objID)
					offset += 8 // Skip both dwords
				} else {
					break
				}
			}
			actionData["object_ids"] = objectIDs
		}

	case ActionAssignGroup:
		// 1 byte: group number
		// 1 word: unit count
		// n * 8 bytes: object IDs
		if offset+3 <= len(data) {
			actionData["group"] = data[offset]
			offset++
			unitCount := binary.LittleEndian.Uint16(data[offset:])
			offset += 2
			actionData["unit_count"] = unitCount
			// Parse object IDs
			objectIDs := make([]uint32, 0, unitCount)
			for i := uint16(0); i < unitCount; i++ {
				if offset+8 <= len(data) {
					objID := binary.LittleEndian.Uint32(data[offset:])
					objectIDs = append(objectIDs, objID)
					offset += 8
				} else {
					break
				}
			}
			actionData["object_ids"] = objectIDs
		}

	case ActionSelectGroup:
		// 1 byte: group number
		// 1 byte: unknown
		if offset+2 <= len(data) {
			actionData["group"] = data[offset]
			offset += 2
		}

	case ActionSelectSubgroup:
		// Variable based on version
		if version >= 14 { // 1.14b+
			// ItemID (4) + ObjectID1 (4) + ObjectID2 (4)
			offset += 12
		} else {
			// Just subgroup number (1 byte)
			offset++
		}

	case ActionPreSubselection:
		// 1 byte total

	case ActionSyncSelection:
		// Sync/selection verification action (10 bytes total)
		// 1 byte: flag (always 0x01)
		// 4 bytes: ObjectID1
		// 4 bytes: ObjectID2
		if offset+9 <= len(data) {
			actionData["flag"] = data[offset]
			offset++
			actionData["object_id_1"] = binary.LittleEndian.Uint32(data[offset:])
			offset += 4
			actionData["object_id_2"] = binary.LittleEndian.Uint32(data[offset:])
			offset += 4
		} else {
			offset += 9
		}

	case ActionSelectGroundItem:
		// 1 byte: flags
		// 8 bytes: 2x ObjectID
		offset += 9

	case ActionCancelHeroRevival:
		// 8 bytes: 2x UnitID
		offset += 8

	case ActionRemoveFromQueue:
		// 1 byte: slot number
		// 4 bytes: ItemID
		if offset+5 <= len(data) {
			actionData["slot"] = data[offset]
			offset++
			actionData["item_id"] = data[offset : offset+4]
			offset += 4
		}

	case ActionAllyOptions:
		// 1 byte: player slot
		// 4 bytes: flags
		if offset+5 <= len(data) {
			actionData["player_slot"] = data[offset]
			offset++
			actionData["flags"] = binary.LittleEndian.Uint32(data[offset:])
			offset += 4
		}

	case ActionTransferResources:
		// 1 byte: player slot
		// 4 bytes: gold
		// 4 bytes: lumber
		if offset+9 <= len(data) {
			actionData["player_slot"] = data[offset]
			offset++
			actionData["gold"] = binary.LittleEndian.Uint32(data[offset:])
			offset += 4
			actionData["lumber"] = binary.LittleEndian.Uint32(data[offset:])
			offset += 4
		}

	case ActionTriggerCommand:
		// Skip 8 bytes of unknowns, then null-terminated string
		offset += 8
		strStart := offset
		for offset < len(data) && data[offset] != 0 {
			offset++
		}
		actionData["command"] = string(data[strStart:offset])
		offset++

	case ActionEscPressed:
		// 1 byte total

	case ActionScenarioTrigger:
		offset += 12

	case ActionHeroSkillMenu, ActionBuildingMenu:
		// 1 byte total

	case ActionMinimapSignal:
		if offset+12 <= len(data) {
			x := math.Float32frombits(binary.LittleEndian.Uint32(data[offset:]))
			y := math.Float32frombits(binary.LittleEndian.Uint32(data[offset+4:]))
			actionData["x"] = x
			actionData["y"] = y
			offset += 12
		}

	case ActionContinueGameB, ActionContinueGameA:
		offset += 16

	case ActionUnknown75:
		offset++

	default:
		// Check for cheat actions (single player)
		if actionID >= 0x20 && actionID <= 0x32 {
			actionName = "cheat"
			if offset+5 <= len(data) {
				offset += 5
			}
		} else {
			// Unknown action - cannot determine size safely
			return nil, offset
		}
	}

	payload := data[startOffset:offset]

	return &GameAction{
		TimestampMs: 0, // Set by caller
		PlayerID:    0, // Set by caller
		ActionType:  actionID,
		ActionName:  actionName,
		Payload:     payload,
		Data:        actionData,
	}, offset
}

// parseCommandData parses CommandData block containing player actions.
//
// CommandData structure:
//   - 1 byte: Player ID
//   - 1 word: Action block length
//   - n bytes: Action blocks
func parseCommandData(data []byte, offset int, length int, version uint32) []struct {
	PlayerID uint8
	Action   *GameAction
} {
	end := offset + length
	var results []struct {
		PlayerID uint8
		Action   *GameAction
	}

	for offset < end {
		if offset+3 > len(data) {
			break
		}

		playerID := data[offset]
		offset++

		actionLength := int(binary.LittleEndian.Uint16(data[offset:]))
		offset += 2

		actionEnd := offset + actionLength

		for offset < actionEnd {
			action, newOffset := parseAction(data, offset, version)
			if action != nil {
				action.PlayerID = playerID
				results = append(results, struct {
					PlayerID uint8
					Action   *GameAction
				}{playerID, action})
				offset = newOffset
			} else {
				// Skip remaining bytes if we can't parse
				break
			}
		}

		// Ensure we don't go past the action block
		offset = actionEnd
	}

	return results
}
