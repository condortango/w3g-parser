package w3g

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

// Race represents a player's race.
type Race uint8

const (
	RaceHuman      Race = 0x01
	RaceOrc        Race = 0x02
	RaceNightElf   Race = 0x04
	RaceUndead     Race = 0x08
	RaceRandom     Race = 0x20
	RaceSelectable Race = 0x40
	RaceUnknown    Race = 0xFF
)

func (r Race) String() string {
	switch r {
	case RaceHuman:
		return "Human"
	case RaceOrc:
		return "Orc"
	case RaceNightElf:
		return "NightElf"
	case RaceUndead:
		return "Undead"
	case RaceRandom:
		return "Random"
	case RaceSelectable:
		return "Selectable"
	default:
		return "Unknown"
	}
}

// MarshalJSON implements json.Marshaler for Race.
func (r Race) MarshalJSON() ([]byte, error) {
	return json.Marshal(r.String())
}

// RaceFromFlags converts race flags byte to Race.
func RaceFromFlags(flags uint8) Race {
	switch {
	case flags&0x01 != 0:
		return RaceHuman
	case flags&0x02 != 0:
		return RaceOrc
	case flags&0x04 != 0:
		return RaceNightElf
	case flags&0x08 != 0:
		return RaceUndead
	case flags&0x20 != 0:
		return RaceRandom
	case flags&0x40 != 0:
		return RaceSelectable
	default:
		return RaceUnknown
	}
}

// SlotStatus represents slot status in game lobby.
type SlotStatus uint8

const (
	SlotEmpty  SlotStatus = 0x00
	SlotClosed SlotStatus = 0x01
	SlotUsed   SlotStatus = 0x02
)

func (s SlotStatus) String() string {
	switch s {
	case SlotEmpty:
		return "Empty"
	case SlotClosed:
		return "Closed"
	case SlotUsed:
		return "Used"
	default:
		return "Unknown"
	}
}

// LeaveResult represents the result when player leaves.
type LeaveResult uint8

const (
	LeaveResultLeft         LeaveResult = 0x01
	LeaveResultLeftAlt      LeaveResult = 0x07
	LeaveResultLost         LeaveResult = 0x08
	LeaveResultWon          LeaveResult = 0x09
	LeaveResultDraw         LeaveResult = 0x0A
	LeaveResultObserverLeft LeaveResult = 0x0B
)

func (r LeaveResult) String() string {
	switch r {
	case LeaveResultLeft, LeaveResultLeftAlt:
		return "Left"
	case LeaveResultLost:
		return "Lost"
	case LeaveResultWon:
		return "Won"
	case LeaveResultDraw:
		return "Draw"
	case LeaveResultObserverLeft:
		return "ObserverLeft"
	default:
		return "Unknown"
	}
}

// MarshalJSON implements json.Marshaler for LeaveResult.
func (r LeaveResult) MarshalJSON() ([]byte, error) {
	return json.Marshal(r.String())
}

// ReplayHeader contains W3G file header information.
type ReplayHeader struct {
	Magic               []byte `json:"-"`
	HeaderSize          uint32 `json:"header_size"`
	CompressedSize      uint32 `json:"compressed_size"`
	HeaderVersion       uint32 `json:"header_version"`
	DecompressedSize    uint32 `json:"decompressed_size"`
	NumCompressedBlocks uint32 `json:"num_compressed_blocks"`

	// SubHeader fields
	GameIdentifier string `json:"game_identifier"`
	Version        uint32 `json:"version"`
	BuildNumber    uint16 `json:"build_number"`
	Flags          uint16 `json:"flags"`
	DurationMs     uint32 `json:"duration_ms"`
	CRC32          uint32 `json:"crc32"`

	// Raw data
	RawHeader []byte `json:"-"`
}

// Duration returns replay duration as time.Duration.
func (h *ReplayHeader) Duration() time.Duration {
	return time.Duration(h.DurationMs) * time.Millisecond
}

// IsMultiplayer returns true if replay is from multiplayer game.
func (h *ReplayHeader) IsMultiplayer() bool {
	return h.Flags&0x8000 != 0
}

// IsReforged returns true if this is a Reforged replay.
func (h *ReplayHeader) IsReforged() bool {
	return h.Version >= ReforgedVersionThreshold || h.GameIdentifier == GameIDReforged
}

// IsExpansion returns true if this is Frozen Throne or Reforged.
func (h *ReplayHeader) IsExpansion() bool {
	return h.GameIdentifier == GameIDTFT || h.GameIdentifier == GameIDReforged
}

// VersionString returns human-readable version string.
func (h *ReplayHeader) VersionString() string {
	if h.IsReforged() {
		buildToVersion := map[uint16]string{
			6105: "1.32.0", 6106: "1.32.1", 6108: "1.32.2",
			6110: "1.32.3", 6111: "1.32.4", 6112: "1.32.5",
			6113: "1.32.6", 6114: "1.32.7", 6115: "1.32.8",
			6116: "1.32.9", 6117: "1.32.10", 6118: "1.33.0",
			6119: "1.34.0", 6120: "1.35.0", 6121: "1.36.0",
			6122: "1.36.1", 6123: "1.36.2",
		}
		if v, ok := buildToVersion[h.BuildNumber]; ok {
			return v
		}
		return fmt.Sprintf("1.3x (build %d)", h.BuildNumber)
	}

	if h.Version >= 10000 {
		major := h.Version / 10000
		minor := (h.Version % 10000) / 100
		patch := h.Version % 100
		if patch > 0 {
			return fmt.Sprintf("%d.%d.%d", major, minor, patch)
		}
		return fmt.Sprintf("%d.%d", major, minor)
	}
	return fmt.Sprintf("1.%d", h.Version)
}

// PlayerInfo contains information about a player.
type PlayerInfo struct {
	ID          uint8        `json:"id"`
	Name        string       `json:"name"`
	Race        Race         `json:"race"`
	Team        uint8        `json:"team"`
	Color       uint8        `json:"color"`
	Handicap    uint8        `json:"handicap"`
	IsHost      bool         `json:"is_host"`
	IsComputer  bool         `json:"is_computer"`
	IsObserver  bool         `json:"is_observer"`
	SlotStatus  SlotStatus   `json:"-"`
	RuntimeMs   uint32       `json:"-"`
	ActionCount int          `json:"action_count"`
	APM         float64      `json:"apm"`
	LeaveResult *LeaveResult `json:"leave_result,omitempty"`
	LeaveTimeMs *uint32      `json:"-"`
}

// GameSettings contains game configuration.
type GameSettings struct {
	Speed             uint8  `json:"speed"`
	Visibility        uint8  `json:"visibility"`
	Observers         uint8  `json:"observers"`
	TeamsTogether     bool   `json:"teams_together"`
	LockTeams         bool   `json:"lock_teams"`
	FullSharedControl bool   `json:"full_shared_control"`
	RandomHero        bool   `json:"random_hero"`
	RandomRaces       bool   `json:"random_races"`
	Referees          bool   `json:"referees"`
	MapChecksum       []byte `json:"-"`
}

// SpeedName returns human-readable speed name.
func (s *GameSettings) SpeedName() string {
	names := []string{"Slow", "Normal", "Fast"}
	if int(s.Speed) < len(names) {
		return names[s.Speed]
	}
	return "Unknown"
}

// ChatMessage represents an in-game chat message.
type ChatMessage struct {
	TimestampMs uint32 `json:"timestamp_ms"`
	PlayerID    uint8  `json:"player_id"`
	PlayerName  string `json:"player_name"`
	Message     string `json:"message"`
	Mode        uint32 `json:"mode"`
	IsStartup   bool   `json:"is_startup,omitempty"`
}

// Timestamp returns message timestamp as time.Duration.
func (c *ChatMessage) Timestamp() time.Duration {
	return time.Duration(c.TimestampMs) * time.Millisecond
}

// ModeName returns human-readable mode name.
func (c *ChatMessage) ModeName() string {
	switch c.Mode {
	case 0:
		return "All"
	case 1:
		return "Allies"
	case 2:
		return "Observers"
	default:
		return fmt.Sprintf("Player %d", c.Mode-2)
	}
}

// GameAction represents a player action/command.
type GameAction struct {
	TimestampMs uint32                 `json:"timestamp_ms"`
	PlayerID    uint8                  `json:"player_id"`
	ActionType  uint8                  `json:"action_type"`
	ActionName  string                 `json:"action_name"`
	Payload     []byte                 `json:"-"`
	Data        map[string]interface{} `json:"data,omitempty"`
}

// Timestamp returns action timestamp as time.Duration.
func (a *GameAction) Timestamp() time.Duration {
	return time.Duration(a.TimestampMs) * time.Millisecond
}

// SlotRecord represents a slot in the game lobby.
type SlotRecord struct {
	PlayerID        uint8
	DownloadPercent uint8
	SlotStatus      uint8
	IsComputer      bool
	Team            uint8
	Color           uint8
	RaceFlags       uint8
	AIStrength      uint8
	Handicap        uint8
}

// W3GReplay represents a complete parsed replay.
type W3GReplay struct {
	Header       *ReplayHeader  `json:"header"`
	GameName     string         `json:"game_name"`
	MapName      string         `json:"map_name"`
	MapPath      string         `json:"map_path"`
	HostName     string         `json:"host_name"`
	Settings     *GameSettings  `json:"settings"`
	Players      []*PlayerInfo  `json:"players"`
	ChatMessages []*ChatMessage `json:"chat_messages"`
	Actions      []*GameAction  `json:"-"`

	// Raw data for advanced users
	RawDecompressed []byte `json:"-"`
}

// GetPlayer returns player by ID.
func (r *W3GReplay) GetPlayer(playerID uint8) *PlayerInfo {
	for _, p := range r.Players {
		if p.ID == playerID {
			return p
		}
	}
	return nil
}

// GetPlayerByName returns player by name (case-insensitive).
func (r *W3GReplay) GetPlayerByName(name string) *PlayerInfo {
	nameLower := strings.ToLower(name)
	for _, p := range r.Players {
		if strings.ToLower(p.Name) == nameLower {
			return p
		}
	}
	return nil
}

// Winner returns the winning player, if determinable.
func (r *W3GReplay) Winner() *PlayerInfo {
	for _, p := range r.Players {
		if p.LeaveResult != nil && *p.LeaveResult == LeaveResultWon {
			return p
		}
	}
	return nil
}

// ToJSON exports replay to JSON bytes.
func (r *W3GReplay) ToJSON(indent bool) ([]byte, error) {
	data := r.toDict()
	if indent {
		return json.MarshalIndent(data, "", "  ")
	}
	return json.Marshal(data)
}

func (r *W3GReplay) toDict() map[string]interface{} {
	headerDict := map[string]interface{}{
		"header_size":          r.Header.HeaderSize,
		"compressed_size":      r.Header.CompressedSize,
		"header_version":       r.Header.HeaderVersion,
		"decompressed_size":    r.Header.DecompressedSize,
		"num_compressed_blocks": r.Header.NumCompressedBlocks,
		"game_identifier":      r.Header.GameIdentifier,
		"version":              r.Header.Version,
		"version_string":       r.Header.VersionString(),
		"build_number":         r.Header.BuildNumber,
		"is_multiplayer":       r.Header.IsMultiplayer(),
		"is_reforged":          r.Header.IsReforged(),
		"is_expansion":         r.Header.IsExpansion(),
		"duration_ms":          r.Header.DurationMs,
		"duration":             formatDuration(r.Header.Duration()),
	}

	settingsDict := map[string]interface{}{
		"speed":              r.Settings.Speed,
		"speed_name":         r.Settings.SpeedName(),
		"visibility":         r.Settings.Visibility,
		"observers":          r.Settings.Observers,
		"teams_together":     r.Settings.TeamsTogether,
		"lock_teams":         r.Settings.LockTeams,
		"full_shared_control": r.Settings.FullSharedControl,
		"random_hero":        r.Settings.RandomHero,
		"random_races":       r.Settings.RandomRaces,
	}

	players := make([]map[string]interface{}, len(r.Players))
	for i, p := range r.Players {
		pd := map[string]interface{}{
			"id":           p.ID,
			"name":         p.Name,
			"race":         p.Race.String(),
			"team":         p.Team,
			"color":        p.Color,
			"handicap":     p.Handicap,
			"is_host":      p.IsHost,
			"is_computer":  p.IsComputer,
			"is_observer":  p.IsObserver,
			"action_count": p.ActionCount,
			"apm":          fmt.Sprintf("%.1f", p.APM),
		}
		if p.LeaveResult != nil {
			pd["leave_result"] = p.LeaveResult.String()
		}
		players[i] = pd
	}

	chatMessages := make([]map[string]interface{}, len(r.ChatMessages))
	for i, c := range r.ChatMessages {
		chatMessages[i] = map[string]interface{}{
			"timestamp_ms": c.TimestampMs,
			"timestamp":    formatDuration(c.Timestamp()),
			"player_id":    c.PlayerID,
			"player_name":  c.PlayerName,
			"message":      c.Message,
			"mode":         c.Mode,
			"mode_name":    c.ModeName(),
		}
	}

	return map[string]interface{}{
		"header":        headerDict,
		"game_name":     r.GameName,
		"map_name":      r.MapName,
		"map_path":      r.MapPath,
		"host_name":     r.HostName,
		"settings":      settingsDict,
		"players":       players,
		"chat_messages": chatMessages,
		"action_count":  len(r.Actions),
	}
}

// formatDuration formats a duration as HH:MM:SS or MM:SS.
func formatDuration(d time.Duration) string {
	h := int(d.Hours())
	m := int(d.Minutes()) % 60
	s := int(d.Seconds()) % 60
	if h > 0 {
		return fmt.Sprintf("%d:%02d:%02d", h, m, s)
	}
	return fmt.Sprintf("%d:%02d", m, s)
}
