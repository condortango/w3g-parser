package w3g

// decodeEncodedString decodes the encoded string format used in W3G.
//
// The encoding uses a control-byte scheme where every even byte-value
// was incremented by 1 (so all encoded bytes are odd). Control bytes
// use bits 1-7 to indicate whether the next 7 bytes are encoded
// (bit=0: subtract 1) or literal (bit=1).
func decodeEncodedString(data []byte, offset int) ([]byte, int) {
	result := make([]byte, 0, 256)
	pos := offset

	for pos < len(data) {
		// Read control byte
		if pos >= len(data) {
			break
		}
		control := data[pos]
		pos++

		if control == 0 {
			// End of encoded string
			break
		}

		// Process next 7 bytes based on control bits
		for bit := 0; bit < 7; bit++ {
			if pos >= len(data) {
				break
			}

			b := data[pos]
			pos++

			if b == 0 {
				// End of string
				result = append(result, 0)
				return result, pos
			}

			// Check if this byte is encoded (bit is 0) or literal (bit is 1)
			if (control & (1 << (bit + 1))) == 0 {
				// Encoded: subtract 1
				result = append(result, b-1)
			} else {
				// Literal
				result = append(result, b)
			}
		}
	}

	return result, pos
}

// parseEncodedSettings parses game settings from encoded string.
//
// The encoded string contains:
// - Game settings (13 bytes)
// - Null byte
// - Map path (null-terminated)
// - Map creator name (null-terminated)
func parseEncodedSettings(encodedData []byte) (*GameSettings, string, string) {
	settings := &GameSettings{
		Speed: 2, // Default to fast
	}
	mapPath := ""
	mapName := ""

	if len(encodedData) < 13 {
		return settings, mapPath, mapName
	}

	// Parse settings from first 13 bytes
	// Byte 0: Speed (bits 0-1)
	settings.Speed = encodedData[0] & 0x03

	// Byte 1: Visibility and observers
	byte1 := encodedData[1]
	settings.Visibility = byte1 & 0x0F
	settings.Observers = (byte1 >> 4) & 0x03
	settings.TeamsTogether = (byte1 & 0x40) != 0

	// Byte 2: Fixed teams
	settings.LockTeams = (encodedData[2] & 0x06) != 0

	// Byte 3: Game options
	byte3 := encodedData[3]
	settings.FullSharedControl = (byte3 & 0x01) != 0
	settings.RandomHero = (byte3 & 0x02) != 0
	settings.RandomRaces = (byte3 & 0x04) != 0
	settings.Referees = (byte3 & 0x40) != 0

	// Bytes 9-12: Map checksum
	if len(encodedData) >= 13 {
		settings.MapChecksum = make([]byte, 4)
		copy(settings.MapChecksum, encodedData[9:13])
	}

	// Parse map path and name after settings
	offset := 13

	// Skip null byte if present
	if offset < len(encodedData) && encodedData[offset] == 0 {
		offset++
	}

	// Map path
	pathStart := offset
	for offset < len(encodedData) && encodedData[offset] != 0 {
		offset++
	}
	if offset > pathStart {
		mapPath = string(encodedData[pathStart:offset])
		// Extract map name from path
		mapName = extractMapName(mapPath)
	}

	return settings, mapPath, mapName
}

// extractMapName extracts the map name from a map path.
func extractMapName(mapPath string) string {
	mapName := mapPath

	// Find last path separator
	for i := len(mapPath) - 1; i >= 0; i-- {
		if mapPath[i] == '/' || mapPath[i] == '\\' {
			mapName = mapPath[i+1:]
			break
		}
	}

	// Remove .w3x or .w3m extension
	if len(mapName) > 4 {
		ext := mapName[len(mapName)-4:]
		if ext == ".w3x" || ext == ".w3m" || ext == ".W3X" || ext == ".W3M" {
			mapName = mapName[:len(mapName)-4]
		}
	}

	return mapName
}
