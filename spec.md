# W3G Replay Parser Specification & LLM Prompt

## Overview

This document serves as a comprehensive prompt for an LLM to create a robust Warcraft 3 replay (.w3g) parser in Go. There is NO official documentation for this format, so the implementation must heavily rely on reverse-engineering, inference, and research from existing implementations.

---

## Research Phase (CRITICAL - Do This First)

Before writing ANY code, you MUST thoroughly research existing w3g parsers and documentation by:

### 1. Search GitHub Extensively

Search for existing w3g parsers in any language:

- **Search queries to use:**
  - `w3g parser`
  - `warcraft 3 replay parser`
  - `w3g replay`
  - `wc3 replay parser`
  - `warcraft reforged replay`

- **Look for implementations in:** JavaScript, Python, C++, Go, Rust, PHP, Java, C#

- **Pay special attention to these types of repos:**
  - `w3gjs` (JavaScript) - commonly referenced
  - `w3g-replay-parser`
  - Any Reforged-compatible parsers
  - W3Champions related tools
  - Back2Warcraft community tools

- **For each repo found:**
  - Study the source code to understand the binary format structure
  - Note any format documentation in their READMEs or comments
  - Check their issue trackers for format-related discussions
  - Look at their test files for format edge cases

### 2. Identify Format Differences Between Versions

Research and document differences between:

- **Classic Warcraft 3 (pre-Reforged)**
  - Versions 1.00 - 1.31
  - Original TFT format
  - Note header structure, magic bytes, compression

- **Reforged (1.32+)**
  - New header fields
  - Potential compression changes
  - Additional metadata
  - Account ID handling vs old player IDs

- **Document specific version breakpoints** where format changed significantly

### 3. Document the Binary Format

As you research, build a comprehensive format specification:

```
HEADER STRUCTURE:
- Offset 0x00: Magic bytes (what are they?)
- Offset 0x??: Header size
- Offset 0x??: Compressed data size
- Offset 0x??: Version information
- ... etc

COMPRESSED BLOCKS:
- Block header structure
- Compression algorithm (zlib? deflate? other?)
- Block chaining method

DECOMPRESSED DATA:
- Game metadata structure
- Player data records
- Map information
- Game settings/options

ACTION BLOCKS:
- Action header format
- Action type IDs
- Player action payloads
- Timestamp encoding

CHAT MESSAGES:
- Message block format
- Player ID encoding
- Message type flags
```

### 4. Additional Research Sources

- **W3Champions** - Competitive replay platform, may have documentation
- **Liquipedia Warcraft** - Community wiki with technical info
- **WC3Maps/Hive Workshop** - Modding community with format knowledge
- **Reddit r/WC3** - Community discussions about replay analysis
- **Old forum archives** - wcreplays.com, etc.

---

## Implementation Requirements

### Project Structure (Go Module)

```
w3g-parser/
├── go.mod                      # Go module definition
├── go.sum                      # Dependency checksums
├── cmd/
│   └── w3g-parse/
│       └── main.go             # CLI entry point
├── pkg/
│   └── w3g/
│       ├── w3g.go              # Public API exports
│       ├── parser.go           # Main parser orchestration
│       ├── models.go           # Data structures and types
│       ├── header.go           # Header parsing logic
│       ├── decompressor.go     # Block decompression
│       ├── actions.go          # Game action parsing
│       ├── chat.go             # Chat message parsing
│       ├── players.go          # Player data parsing
│       ├── encoded.go          # Encoded string decoding
│       ├── constants.go        # Magic bytes, action IDs, etc.
│       └── errors.go           # Custom error types
├── internal/
│   └── binary/
│       └── reader.go           # Binary reading utilities
├── tests/
│   ├── parser_test.go
│   ├── header_test.go
│   ├── decompressor_test.go
│   ├── actions_test.go
│   └── testdata/               # Sample replay files
├── docs/
│   └── FORMAT.md               # Discovered format documentation
├── README.md
└── LICENSE
```

### go.mod Template

```go
module github.com/yourusername/w3g-parser

go 1.21

require (
    github.com/spf13/cobra v1.8.0
)
```

---

## Code Requirements

### 1. Data Models (models.go)

```go
package w3g

import (
    "encoding/json"
    "time"
)

// Race represents a player's race
type Race uint8

const (
    RaceHuman    Race = 0x01
    RaceOrc      Race = 0x02
    RaceNightElf Race = 0x04
    RaceUndead   Race = 0x08
    RaceRandom   Race = 0x20
    RaceUnknown  Race = 0xFF
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
    default:
        return "Unknown"
    }
}

// RaceFromFlags converts race flags byte to Race
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
    default:
        return RaceUnknown
    }
}

// W3GVersion represents the replay version type
type W3GVersion uint8

const (
    VersionClassicRoC W3GVersion = iota
    VersionClassicTFT
    VersionReforged
    VersionUnknown
)

// SlotStatus represents slot status in game lobby
type SlotStatus uint8

const (
    SlotEmpty  SlotStatus = 0x00
    SlotClosed SlotStatus = 0x01
    SlotUsed   SlotStatus = 0x02
)

// LeaveResult represents the result when player leaves
type LeaveResult uint8

const (
    LeaveResultLeft        LeaveResult = 0x01
    LeaveResultLeftAlt     LeaveResult = 0x07
    LeaveResultLost        LeaveResult = 0x08
    LeaveResultWon         LeaveResult = 0x09
    LeaveResultDraw        LeaveResult = 0x0A
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

// ReplayHeader contains W3G file header information
type ReplayHeader struct {
    Magic               []byte
    HeaderSize          uint32
    CompressedSize      uint32
    HeaderVersion       uint32
    DecompressedSize    uint32
    NumCompressedBlocks uint32

    // SubHeader fields
    GameIdentifier string // 'WAR3', 'W3XP', 'PX3W'
    Version        uint32
    BuildNumber    uint16
    Flags          uint16
    DurationMs     uint32
    CRC32          uint32

    // Raw data
    RawHeader []byte
}

// Duration returns replay duration as time.Duration
func (h *ReplayHeader) Duration() time.Duration {
    return time.Duration(h.DurationMs) * time.Millisecond
}

// IsMultiplayer returns true if replay is from multiplayer game
func (h *ReplayHeader) IsMultiplayer() bool {
    return h.Flags&0x8000 != 0
}

// IsReforged returns true if this is a Reforged replay
func (h *ReplayHeader) IsReforged() bool {
    return h.Version >= 29 || h.GameIdentifier == "PX3W"
}

// IsExpansion returns true if this is Frozen Throne or Reforged
func (h *ReplayHeader) IsExpansion() bool {
    return h.GameIdentifier == "W3XP" || h.GameIdentifier == "PX3W"
}

// VersionString returns human-readable version string
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

// PlayerInfo contains information about a player
type PlayerInfo struct {
    ID          uint8
    Name        string
    Race        Race
    Team        uint8
    Color       uint8
    Handicap    uint8
    IsHost      bool
    IsComputer  bool
    IsObserver  bool
    SlotStatus  SlotStatus
    RuntimeMs   uint32    // For ladder games
    ActionCount int
    APM         float64
    LeaveResult *LeaveResult
    LeaveTimeMs *uint32
}

// GameSettings contains game configuration
type GameSettings struct {
    Speed             uint8  // 0=slow, 1=normal, 2=fast
    Visibility        uint8
    Observers         uint8
    TeamsTogether     bool
    LockTeams         bool
    FullSharedControl bool
    RandomHero        bool
    RandomRaces       bool
    Referees          bool
    MapChecksum       []byte
}

// SpeedName returns human-readable speed name
func (s *GameSettings) SpeedName() string {
    names := []string{"Slow", "Normal", "Fast"}
    if int(s.Speed) < len(names) {
        return names[s.Speed]
    }
    return "Unknown"
}

// ChatMessage represents an in-game chat message
type ChatMessage struct {
    TimestampMs uint32
    PlayerID    uint8
    PlayerName  string
    Message     string
    Mode        uint32 // 0=all, 1=allies, 2=observers, 3+=specific player
    IsStartup   bool
}

// Timestamp returns message timestamp as time.Duration
func (c *ChatMessage) Timestamp() time.Duration {
    return time.Duration(c.TimestampMs) * time.Millisecond
}

// ModeName returns human-readable mode name
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

// GameAction represents a player action/command
type GameAction struct {
    TimestampMs uint32
    PlayerID    uint8
    ActionType  uint8
    ActionName  string
    Payload     []byte
    Data        map[string]interface{}
}

// Timestamp returns action timestamp as time.Duration
func (a *GameAction) Timestamp() time.Duration {
    return time.Duration(a.TimestampMs) * time.Millisecond
}

// W3GReplay represents a complete parsed replay
type W3GReplay struct {
    Header        *ReplayHeader
    GameName      string
    MapName       string
    MapPath       string
    HostName      string
    Settings      *GameSettings
    Players       []*PlayerInfo
    ChatMessages  []*ChatMessage
    Actions       []*GameAction

    // Raw data for advanced users
    RawDecompressed []byte
}

// GetPlayer returns player by ID
func (r *W3GReplay) GetPlayer(playerID uint8) *PlayerInfo {
    for _, p := range r.Players {
        if p.ID == playerID {
            return p
        }
    }
    return nil
}

// GetPlayerByName returns player by name (case-insensitive)
func (r *W3GReplay) GetPlayerByName(name string) *PlayerInfo {
    nameLower := strings.ToLower(name)
    for _, p := range r.Players {
        if strings.ToLower(p.Name) == nameLower {
            return p
        }
    }
    return nil
}

// Winner returns the winning player, if determinable
func (r *W3GReplay) Winner() *PlayerInfo {
    for _, p := range r.Players {
        if p.LeaveResult != nil && *p.LeaveResult == LeaveResultWon {
            return p
        }
    }
    return nil
}

// ToJSON exports replay to JSON
func (r *W3GReplay) ToJSON(indent bool) ([]byte, error) {
    if indent {
        return json.MarshalIndent(r.toDict(), "", "  ")
    }
    return json.Marshal(r.toDict())
}

func (r *W3GReplay) toDict() map[string]interface{} {
    // Implementation for JSON serialization
    // ...
}
```

### 2. Parser Structure (parser.go)

```go
package w3g

import (
    "io"
    "os"
)

// Parser is the main W3G replay parser
type Parser struct {
    Strict bool // If true, fail on unknown data; otherwise skip and log
}

// NewParser creates a new parser instance
func NewParser() *Parser {
    return &Parser{Strict: false}
}

// Parse parses a complete replay file
func (p *Parser) Parse(filepath string) (*W3GReplay, error) {
    f, err := os.Open(filepath)
    if err != nil {
        return nil, err
    }
    defer f.Close()

    return p.ParseStream(f)
}

// ParseStream parses a replay from an io.Reader
func (p *Parser) ParseStream(r io.Reader) (*W3GReplay, error) {
    // 1. Parse header
    header, headerBytes, err := parseHeader(r)
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

// ParseHeaderOnly parses just the header (for quick metadata access)
func (p *Parser) ParseHeaderOnly(filepath string) (*ReplayHeader, error) {
    f, err := os.Open(filepath)
    if err != nil {
        return nil, err
    }
    defer f.Close()

    header, _, err := parseHeader(f)
    return header, err
}

// IterActions returns a channel for iterating actions without loading all into memory
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
```

### 3. Error Handling (errors.go)

```go
package w3g

import "fmt"

// ParseError is the base error type for parsing errors
type ParseError struct {
    Message string
    Offset  *int
}

func (e *ParseError) Error() string {
    if e.Offset != nil {
        return fmt.Sprintf("%s at offset 0x%X", e.Message, *e.Offset)
    }
    return e.Message
}

// InvalidHeaderError indicates invalid or unrecognized header format
type InvalidHeaderError struct {
    ParseError
}

// UnsupportedVersionError indicates replay version not supported
type UnsupportedVersionError struct {
    ParseError
    Version string
}

// DecompressionError indicates failed to decompress data block
type DecompressionError struct {
    ParseError
}

// UnknownActionError indicates unknown action type encountered
type UnknownActionError struct {
    ParseError
    ActionID uint8
}

// TruncatedDataError indicates data was truncated unexpectedly
type TruncatedDataError struct {
    ParseError
}

// Helper functions for creating errors
func newInvalidHeaderError(msg string) *InvalidHeaderError {
    return &InvalidHeaderError{ParseError{Message: msg}}
}

func newDecompressionError(msg string, offset int) *DecompressionError {
    return &DecompressionError{ParseError{Message: msg, Offset: &offset}}
}

func newTruncatedDataError(msg string, offset int) *TruncatedDataError {
    return &TruncatedDataError{ParseError{Message: msg, Offset: &offset}}
}
```

### 4. Constants (constants.go)

```go
package w3g

// MagicString is the magic bytes identifying W3G replay files (28 bytes)
var MagicString = []byte("Warcraft III recorded game\x1a\x00")

// Header sizes
const (
    BaseHeaderSize   = 0x30 // 48 bytes
    SubHeaderV0Size  = 0x10 // 16 bytes
    SubHeaderV1Size  = 0x14 // 20 bytes
    HeaderV0Total    = 0x40 // 64 bytes
    HeaderV1Total    = 0x44 // 68 bytes
)

// Game identifiers
const (
    GameIDClassic  = "WAR3"
    GameIDTFT      = "W3XP"
    GameIDReforged = "PX3W"
)

// Flags
const (
    FlagSinglePlayer = 0x0000
    FlagMultiplayer  = 0x8000
)

// Observer team IDs
const (
    ObserverTeamClassic  = 12
    ObserverTeamReforged = 24
)

// Version threshold for Reforged
const ReforgedVersionThreshold = 29

// Block IDs
const (
    BlockLeaveGame   = 0x17
    BlockFirstStart  = 0x1A
    BlockSecondStart = 0x1B
    BlockThirdStart  = 0x1C
    BlockGameStart   = 0x19
    BlockTimeSlotOld = 0x1E
    BlockTimeSlot    = 0x1F
    BlockChat        = 0x20
    BlockChecksum    = 0x22
    BlockForcedEnd   = 0x2F
)

// Record IDs
const (
    RecordHost             = 0x00
    RecordAdditionalPlayer = 0x16
)

// Action IDs
const (
    ActionPause            = 0x01
    ActionResume           = 0x02
    ActionSetSpeed         = 0x03
    ActionIncSpeed         = 0x04
    ActionDecSpeed         = 0x05
    ActionSaveGame         = 0x06
    ActionSaveFinished     = 0x07
    ActionAbilityNoParams  = 0x10
    ActionAbilityTargetPos = 0x11
    ActionAbilityPosObject = 0x12
    ActionAbilityDropItem  = 0x13
    ActionAbilityTwoPos    = 0x14
    ActionChangeSelection  = 0x16
    ActionAssignGroup      = 0x17
    ActionSelectGroup      = 0x18
    ActionSelectSubgroup   = 0x19
    ActionPreSubselection  = 0x1A
    ActionSyncSelection    = 0x1B
    ActionSelectGroundItem = 0x1C
    ActionCancelHeroRevival = 0x1D
    ActionRemoveFromQueue  = 0x1E
    ActionAllyOptions      = 0x50
    ActionTransferResources = 0x51
    ActionTriggerCommand   = 0x60
    ActionEscPressed       = 0x61
    ActionScenarioTrigger  = 0x62
    ActionHeroSkillMenu    = 0x66
    ActionBuildingMenu     = 0x67
    ActionMinimapSignal    = 0x68
    ActionContinueGameB    = 0x69
    ActionContinueGameA    = 0x6A
    ActionUnknown75        = 0x75
)

// Chat flags
const (
    ChatFlagStartup = 0x10
    ChatFlagNormal  = 0x20
)

// Chat modes
const (
    ChatModeAll       = 0x00
    ChatModeAllies    = 0x01
    ChatModeObservers = 0x02
)

// Action names for human-readable output
var ActionNames = map[uint8]string{
    ActionPause:            "pause",
    ActionResume:           "resume",
    ActionSetSpeed:         "set_speed",
    ActionIncSpeed:         "increase_speed",
    ActionDecSpeed:         "decrease_speed",
    ActionSaveGame:         "save_game",
    ActionSaveFinished:     "save_finished",
    ActionAbilityNoParams:  "ability",
    ActionAbilityTargetPos: "ability_position",
    ActionAbilityPosObject: "ability_object",
    ActionAbilityDropItem:  "drop_item",
    ActionAbilityTwoPos:    "ability_two_positions",
    ActionChangeSelection:  "select_units",
    ActionAssignGroup:      "assign_group",
    ActionSelectGroup:      "select_group",
    ActionSelectSubgroup:   "select_subgroup",
    ActionPreSubselection:  "pre_subselection",
    ActionSyncSelection:    "sync_selection",
    ActionSelectGroundItem: "select_item",
    ActionCancelHeroRevival: "cancel_revival",
    ActionRemoveFromQueue:  "remove_from_queue",
    ActionAllyOptions:      "ally_options",
    ActionTransferResources: "transfer_resources",
    ActionTriggerCommand:   "trigger_command",
    ActionEscPressed:       "escape",
    ActionScenarioTrigger:  "scenario_trigger",
    ActionHeroSkillMenu:    "hero_skill_menu",
    ActionBuildingMenu:     "building_menu",
    ActionMinimapSignal:    "minimap_ping",
    ActionContinueGameB:    "continue_game_b",
    ActionContinueGameA:    "continue_game_a",
    ActionUnknown75:        "unknown_75",
}
```

### 5. Header Parsing (header.go)

```go
package w3g

import (
    "bytes"
    "encoding/binary"
    "io"
)

// parseHeader parses the W3G file header from a reader
func parseHeader(r io.Reader) (*ReplayHeader, []byte, error) {
    // Read base header (48 bytes)
    baseHeader := make([]byte, BaseHeaderSize)
    if _, err := io.ReadFull(r, baseHeader); err != nil {
        return nil, nil, newTruncatedDataError("file too small for header", len(baseHeader))
    }

    // Validate magic string
    magic := baseHeader[:28]
    if !bytes.Equal(magic, MagicString) {
        return nil, nil, newInvalidHeaderError(
            fmt.Sprintf("invalid magic string: %v, expected %v", magic, MagicString),
        )
    }

    // Parse base header fields using little-endian
    headerSize := binary.LittleEndian.Uint32(baseHeader[0x1C:])
    compressedSize := binary.LittleEndian.Uint32(baseHeader[0x20:])
    headerVersion := binary.LittleEndian.Uint32(baseHeader[0x24:])
    decompressedSize := binary.LittleEndian.Uint32(baseHeader[0x28:])
    numBlocks := binary.LittleEndian.Uint32(baseHeader[0x2C:])

    // Determine subheader size based on version
    var subHeaderSize int
    switch headerVersion {
    case 0:
        subHeaderSize = SubHeaderV0Size
    case 1:
        subHeaderSize = SubHeaderV1Size
    default:
        return nil, nil, newInvalidHeaderError(
            fmt.Sprintf("unknown header version: %d", headerVersion),
        )
    }

    // Read subheader
    subHeader := make([]byte, subHeaderSize)
    if _, err := io.ReadFull(r, subHeader); err != nil {
        return nil, nil, newTruncatedDataError("file too small for subheader", BaseHeaderSize)
    }

    header := &ReplayHeader{
        Magic:               magic,
        HeaderSize:          headerSize,
        CompressedSize:      compressedSize,
        HeaderVersion:       headerVersion,
        DecompressedSize:    decompressedSize,
        NumCompressedBlocks: numBlocks,
    }

    // Parse subheader based on version
    if headerVersion == 0 {
        // Version 0 (Classic, patches <= 1.06)
        header.Version = uint32(binary.LittleEndian.Uint16(subHeader[0x02:]))
        header.BuildNumber = binary.LittleEndian.Uint16(subHeader[0x04:])
        header.Flags = binary.LittleEndian.Uint16(subHeader[0x06:])
        header.DurationMs = binary.LittleEndian.Uint32(subHeader[0x08:])
        header.CRC32 = binary.LittleEndian.Uint32(subHeader[0x0C:])
        header.GameIdentifier = "WAR3"
    } else {
        // Version 1 (Expansion, patches >= 1.07)
        header.GameIdentifier = string(subHeader[0x00:0x04])
        header.Version = binary.LittleEndian.Uint32(subHeader[0x04:])
        header.BuildNumber = binary.LittleEndian.Uint16(subHeader[0x08:])
        header.Flags = binary.LittleEndian.Uint16(subHeader[0x0A:])
        header.DurationMs = binary.LittleEndian.Uint32(subHeader[0x0C:])
        header.CRC32 = binary.LittleEndian.Uint32(subHeader[0x10:])
    }

    rawHeader := append(baseHeader, subHeader...)
    header.RawHeader = rawHeader

    return header, rawHeader, nil
}
```

### 6. Decompression (decompressor.go)

```go
package w3g

import (
    "bytes"
    "compress/zlib"
    "encoding/binary"
    "io"
)

// decompressBlocks decompresses all data blocks from reader
func decompressBlocks(r io.Reader, header *ReplayHeader) ([]byte, error) {
    var result bytes.Buffer
    isReforged := header.IsReforged()

    for i := uint32(0); i < header.NumCompressedBlocks; i++ {
        var compressedSize, decompressedSize uint32

        if isReforged {
            // Reforged: 12-byte header
            blockHeader := make([]byte, 12)
            if _, err := io.ReadFull(r, blockHeader); err != nil {
                return nil, newTruncatedDataError(
                    fmt.Sprintf("block %d header truncated", i), int(result.Len()),
                )
            }
            compressedSize = uint32(binary.LittleEndian.Uint16(blockHeader[0:]))
            decompressedSize = binary.LittleEndian.Uint32(blockHeader[4:])
        } else {
            // Classic: 8-byte header
            blockHeader := make([]byte, 8)
            if _, err := io.ReadFull(r, blockHeader); err != nil {
                return nil, newTruncatedDataError(
                    fmt.Sprintf("block %d header truncated", i), int(result.Len()),
                )
            }
            compressedSize = uint32(binary.LittleEndian.Uint16(blockHeader[0:]))
            decompressedSize = uint32(binary.LittleEndian.Uint16(blockHeader[2:]))
        }

        // Read compressed data
        compressedData := make([]byte, compressedSize)
        if _, err := io.ReadFull(r, compressedData); err != nil {
            return nil, newTruncatedDataError(
                fmt.Sprintf("block %d data truncated: expected %d bytes", i, compressedSize),
                int(result.Len()),
            )
        }

        // Decompress
        var decompressed []byte
        var err error

        if isReforged {
            // Reforged uses zlib with header
            decompressed, err = decompressZlib(compressedData)
        } else {
            // Classic uses raw deflate
            decompressed, err = decompressDeflate(compressedData)
            if err != nil {
                // Fallback to zlib with header
                decompressed, err = decompressZlib(compressedData)
            }
        }

        if err != nil {
            return nil, newDecompressionError(
                fmt.Sprintf("block %d decompression failed: %v", i, err),
                int(result.Len()),
            )
        }

        result.Write(decompressed)
    }

    return result.Bytes(), nil
}

func decompressZlib(data []byte) ([]byte, error) {
    r, err := zlib.NewReader(bytes.NewReader(data))
    if err != nil {
        return nil, err
    }
    defer r.Close()

    return io.ReadAll(r)
}

func decompressDeflate(data []byte) ([]byte, error) {
    // For raw deflate, we need to use flate package directly
    // zlib.NewReader expects a zlib header, so we use flate.NewReader
    r := flate.NewReader(bytes.NewReader(data))
    defer r.Close()

    return io.ReadAll(r)
}
```

---

## CLI Requirements (cmd/w3g-parse/main.go)

```go
package main

import (
    "encoding/json"
    "fmt"
    "os"
    "time"

    "github.com/spf13/cobra"
    "github.com/yourusername/w3g-parser/pkg/w3g"
)

func formatDuration(d time.Duration) string {
    h := int(d.Hours())
    m := int(d.Minutes()) % 60
    s := int(d.Seconds()) % 60
    if h > 0 {
        return fmt.Sprintf("%d:%02d:%02d", h, m, s)
    }
    return fmt.Sprintf("%d:%02d", m, s)
}

func main() {
    rootCmd := &cobra.Command{
        Use:   "w3g-parse",
        Short: "W3G Replay Parser - Parse Warcraft 3 replay files",
    }

    // parse command
    parseCmd := &cobra.Command{
        Use:   "parse [replay]",
        Short: "Parse a replay file and display information",
        Args:  cobra.ExactArgs(1),
        RunE:  runParse,
    }
    parseCmd.Flags().StringP("format", "f", "text", "Output format (text/json)")
    parseCmd.Flags().StringP("output", "o", "", "Output file")
    parseCmd.Flags().Int("indent", 2, "JSON indent level")

    // players command
    playersCmd := &cobra.Command{
        Use:   "players [replay]",
        Short: "Show player information",
        Args:  cobra.ExactArgs(1),
        RunE:  runPlayers,
    }

    // chat command
    chatCmd := &cobra.Command{
        Use:   "chat [replay]",
        Short: "Show chat messages",
        Args:  cobra.ExactArgs(1),
        RunE:  runChat,
    }

    // info command
    infoCmd := &cobra.Command{
        Use:   "info [replay]",
        Short: "Show basic replay information (fast, header only)",
        Args:  cobra.ExactArgs(1),
        RunE:  runInfo,
    }

    // actions command
    actionsCmd := &cobra.Command{
        Use:   "actions [replay]",
        Short: "Show game actions",
        Args:  cobra.ExactArgs(1),
        RunE:  runActions,
    }
    actionsCmd.Flags().IntP("limit", "n", 50, "Maximum actions to show")
    actionsCmd.Flags().BoolP("detail", "d", false, "Show detailed action information")
    actionsCmd.Flags().StringP("filter", "f", "", "Filter by action type")

    // batch command
    batchCmd := &cobra.Command{
        Use:   "batch [replays...]",
        Short: "Parse multiple replays to a JSON array",
        Args:  cobra.MinimumNArgs(1),
        RunE:  runBatch,
    }
    batchCmd.Flags().StringP("output", "o", "", "Output JSON file (required)")
    batchCmd.MarkFlagRequired("output")

    rootCmd.AddCommand(parseCmd, playersCmd, chatCmd, infoCmd, actionsCmd, batchCmd)

    if err := rootCmd.Execute(); err != nil {
        os.Exit(1)
    }
}

func runParse(cmd *cobra.Command, args []string) error {
    parser := w3g.NewParser()
    replay, err := parser.Parse(args[0])
    if err != nil {
        return err
    }

    format, _ := cmd.Flags().GetString("format")
    output, _ := cmd.Flags().GetString("output")

    var result string
    if format == "json" {
        data, _ := replay.ToJSON(true)
        result = string(data)
    } else {
        result = formatReplayText(replay)
    }

    if output != "" {
        return os.WriteFile(output, []byte(result), 0644)
    }

    fmt.Println(result)
    return nil
}

// Additional command implementations...
```

---

## Target Public API

```go
package main

import (
    "fmt"
    "github.com/yourusername/w3g-parser/pkg/w3g"
)

func main() {
    // Simple usage - parse a file
    parser := w3g.NewParser()
    replay, err := parser.Parse("my_replay.w3g")
    if err != nil {
        panic(err)
    }

    // Access parsed data
    fmt.Printf("Game: %s\n", replay.GameName)
    fmt.Printf("Map: %s\n", replay.MapName)
    fmt.Printf("Duration: %s\n", replay.Header.Duration())
    fmt.Printf("Version: %s\n", replay.Header.VersionString())

    // Players
    for _, player := range replay.Players {
        fmt.Printf("  %s (%s) - APM: %.1f\n",
            player.Name, player.Race.String(), player.APM)
    }

    // Chat log
    for _, chat := range replay.ChatMessages {
        fmt.Printf("[%s] %s: %s\n",
            chat.Timestamp(), chat.PlayerName, chat.Message)
    }

    // Iterate actions
    for _, action := range replay.Actions {
        if action.ActionName == "ability_position" {
            fmt.Printf("%dms: Player %d - %v\n",
                action.TimestampMs, action.PlayerID, action.Data)
        }
    }

    // Export to JSON
    jsonData, _ := replay.ToJSON(true)
    fmt.Println(string(jsonData))

    // Quick header check (no full parse)
    header, _ := parser.ParseHeaderOnly("replay.w3g")
    fmt.Printf("Version: %s, Duration: %s\n",
        header.VersionString(), header.Duration())

    // Memory-efficient action iteration
    actionCh, errCh := parser.IterActions("large_replay.w3g")
    for action := range actionCh {
        processAction(action)
    }
    if err := <-errCh; err != nil {
        panic(err)
    }
}
```

---

## Testing Strategy

```go
// tests/parser_test.go
package tests

import (
    "os"
    "path/filepath"
    "testing"

    "github.com/yourusername/w3g-parser/pkg/w3g"
)

func TestParseHeader(t *testing.T) {
    // Test with mock header bytes
    mockHeader := append(
        []byte("Warcraft III recorded game\x1a\x00"),
        // Header size, compressed size, etc.
        0x44, 0x00, 0x00, 0x00, // header size
        // ... more bytes
    )

    // Test header parsing
    // ...
}

func TestFullParse(t *testing.T) {
    samplePath := filepath.Join("testdata", "sample.w3g")
    if _, err := os.Stat(samplePath); os.IsNotExist(err) {
        t.Skip("No sample replay available")
    }

    parser := w3g.NewParser()
    replay, err := parser.Parse(samplePath)
    if err != nil {
        t.Fatalf("Parse failed: %v", err)
    }

    if replay.Header == nil {
        t.Error("Header is nil")
    }

    if len(replay.Players) == 0 {
        t.Error("No players parsed")
    }

    if replay.MapName == "" {
        t.Error("Map name is empty")
    }
}

func TestReforgedReplay(t *testing.T) {
    // Test Reforged-specific parsing
    // ...
}

func TestClassicReplay(t *testing.T) {
    // Test Classic format parsing
    // ...
}
```

---

## Documentation Requirements

Create a `docs/FORMAT.md` that documents everything discovered (see existing Python version for reference).

---

## Important Implementation Notes

1. **The format is NOT officially documented** - Your code IS the documentation. Add extensive comments explaining:
   - What each byte/field means
   - How you determined its purpose
   - Which existing parser you learned this from

2. **Mark uncertainty clearly:**
   ```go
   // Unknown field - possibly CRC or reserved
   // Observed values: 0x00000000, 0xFFFFFFFF
   // See: github.com/example/w3gjs/blob/main/src/parser.js#L123
   unknownField := binary.LittleEndian.Uint32(data[offset:])
   ```

3. **Handle unknowns gracefully:**
   - Log warnings for unknown action types
   - Skip unknown data with length fields
   - Never crash on unexpected data in non-strict mode

4. **Consider edge cases:**
   - Private game replays may have obfuscation
   - Tournament replays may have additional metadata
   - Very old replays (RoC, early TFT) may have format differences
   - Corrupted/truncated replays should partially parse

5. **Performance considerations:**
   - Large replays can have millions of actions
   - Provide lazy iteration options via channels
   - Consider memory-mapped file access for very large files

6. **Go idioms:**
   - Use `io.Reader` interfaces for flexibility
   - Return errors, don't panic
   - Use `encoding/binary` for binary parsing
   - Keep public API minimal and clean
   - Use struct methods for computed properties

---

## Checklist Before Completion

- [ ] Researched at least 5 existing w3g parser implementations
- [ ] Documented discovered format in FORMAT.md
- [ ] Parser handles Classic WC3 replays
- [ ] Parser handles Reforged replays
- [ ] Version auto-detection works
- [ ] All data models have proper Go types
- [ ] Error handling returns proper error types
- [ ] CLI tool works with all commands
- [ ] JSON export works correctly
- [ ] Unit tests pass
- [ ] Code passes `go vet` and `golint` checks
- [ ] README has usage examples
