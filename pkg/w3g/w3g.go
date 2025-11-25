// Package w3g provides a parser for Warcraft III replay (.w3g) files.
//
// The package supports both Classic Warcraft III and Reforged replay formats.
//
// Basic usage:
//
//	parser := w3g.NewParser()
//	replay, err := parser.Parse("my_replay.w3g")
//	if err != nil {
//	    log.Fatal(err)
//	}
//
//	fmt.Printf("Game: %s\n", replay.GameName)
//	fmt.Printf("Map: %s\n", replay.MapName)
//	fmt.Printf("Duration: %s\n", replay.Header.Duration())
//
//	for _, player := range replay.Players {
//	    fmt.Printf("  %s (%s) - APM: %.1f\n",
//	        player.Name, player.Race.String(), player.APM)
//	}
package w3g

// Parse is a convenience function to parse a replay file.
func Parse(filepath string) (*W3GReplay, error) {
	return NewParser().Parse(filepath)
}

// ParseHeaderOnly is a convenience function to parse just the header.
func ParseHeaderOnly(filepath string) (*ReplayHeader, error) {
	return NewParser().ParseHeaderOnly(filepath)
}

// DecodeItemID decodes a 4-byte item/ability ID to human-readable string.
// Exported for use by CLI and other packages.
func DecodeItemID(itemBytes []byte) string {
	return decodeItemID(itemBytes)
}

// FormatDuration formats a duration as HH:MM:SS or MM:SS.
// Exported for use by CLI and other packages.
func FormatDuration(ms uint32) string {
	totalSeconds := ms / 1000
	hours := totalSeconds / 3600
	minutes := (totalSeconds % 3600) / 60
	seconds := totalSeconds % 60
	if hours > 0 {
		return formatDurationParts(int(hours), int(minutes), int(seconds))
	}
	return formatDurationMinSec(int(minutes), int(seconds))
}

func formatDurationParts(h, m, s int) string {
	return padInt(h) + ":" + padInt(m) + ":" + padInt(s)
}

func formatDurationMinSec(m, s int) string {
	return intToStr(m) + ":" + padInt(s)
}

func padInt(n int) string {
	if n < 10 {
		return "0" + intToStr(n)
	}
	return intToStr(n)
}

func intToStr(n int) string {
	if n == 0 {
		return "0"
	}
	digits := make([]byte, 0, 10)
	for n > 0 {
		digits = append([]byte{byte('0' + n%10)}, digits...)
		n /= 10
	}
	return string(digits)
}
