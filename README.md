# W3G Parser

A flexible Warcraft 3 replay (.w3g) parser supporting Classic and Reforged versions.

## Installation

```bash
pip install w3g-parser
```

Or with uv:

```bash
uv add w3g-parser
```

## Usage

### Python API

```python
from w3g_parser import W3GParser, W3GReplay

# Simple usage via class method
replay = W3GReplay.parse("my_replay.w3g")

# Or use parser instance for more control
parser = W3GParser(strict=False)
replay = parser.parse("my_replay.w3g")

# Access parsed data
print(f"Game: {replay.game_name}")
print(f"Map: {replay.map_name}")
print(f"Duration: {replay.header.duration}")
print(f"Version: {replay.header.version_string}")

# Players
for player in replay.players:
    print(f"  {player.name} ({player.race.name}) - APM: {player.apm:.1f}")

# Chat log
for chat in replay.chat_messages:
    print(f"[{chat.timestamp}] {chat.player_name}: {chat.message}")

# Export to JSON
replay.to_json("output.json")
data = replay.to_dict()

# Quick header check (no full parse)
header = W3GParser().parse_header_only("replay.w3g")
print(f"Version: {header.version_string}, Duration: {header.duration}")

# Memory-efficient action iteration
for action in parser.iter_actions("large_replay.w3g"):
    print(action.action_name)
```

### Command-Line Interface

```bash
# Parse and display replay info
uv run w3g-parse parse replay.w3g

# Output as JSON
uv run w3g-parse parse replay.w3g --format json

# Show player information
uv run w3g-parse players replay.w3g

# Show chat messages
uv run w3g-parse chat replay.w3g

# Quick header info (fast)
uv run w3g-parse info replay.w3g

# Show actions
uv run w3g-parse actions replay.w3g

# Show detailed actions with decoded unit/ability names and coordinates
uv run w3g-parse actions replay.w3g --detail

# Filter actions by type (e.g., building placements)
uv run w3g-parse actions replay.w3g --detail --filter ability_position

# Batch process multiple replays
uv run w3g-parse batch *.w3g --output results.json
```

## Supported Versions

- Classic Warcraft III (Reign of Chaos)
- The Frozen Throne (all patches)
- Reforged (1.32+)

## Format Documentation

See [docs/FORMAT.md](docs/FORMAT.md) for detailed binary format documentation.

## License

MIT
