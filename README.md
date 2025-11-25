# W3G Parser

A flexible Warcraft 3 replay (.w3g) parser written in Go, supporting Classic and Reforged versions.

## Installation

### From Source

```bash
go install github.com/condor/w3g-parser/cmd/w3g-parse@latest
```

### Build Locally

```bash
git clone https://github.com/condor/w3g-parser.git
cd w3g-parser
go build ./cmd/w3g-parse
```

## Usage

### Go API

```go
package main

import (
    "fmt"
    "log"

    "github.com/condor/w3g-parser/pkg/w3g"
)

func main() {
    // Simple usage - parse a file
    parser := w3g.NewParser()
    replay, err := parser.Parse("my_replay.w3g")
    if err != nil {
        log.Fatal(err)
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
        fmt.Printf("%s: %s\n", action.ActionName, action.Timestamp())
    }
    if err := <-errCh; err != nil {
        log.Fatal(err)
    }
}
```

### Command-Line Interface

```bash
# Parse and display replay info
./w3g-parse parse replay.w3g

# Output as JSON
./w3g-parse parse replay.w3g --format json

# Show player information
./w3g-parse players replay.w3g

# Show chat messages
./w3g-parse chat replay.w3g

# Quick header info (fast)
./w3g-parse info replay.w3g

# Show actions
./w3g-parse actions replay.w3g

# Show detailed actions with decoded unit/ability names and coordinates
./w3g-parse actions replay.w3g --detail

# Filter actions by type (e.g., building placements)
./w3g-parse actions replay.w3g --detail -F ability_position

# Batch process multiple replays
./w3g-parse batch *.w3g --output results.json
```

## Supported Versions

- Classic Warcraft III (Reign of Chaos)
- The Frozen Throne (all patches)
- Reforged (1.32+)

## Format Documentation

See [docs/FORMAT.md](docs/FORMAT.md) for detailed binary format documentation.

## Project Structure

```
w3g-parser/
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
├── docs/
│   └── FORMAT.md               # Binary format documentation
├── go.mod
├── go.sum
├── README.md
└── LICENSE
```

## License

MIT
