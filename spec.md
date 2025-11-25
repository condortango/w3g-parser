# W3G Replay Parser Specification & LLM Prompt

## Overview

This document serves as a comprehensive prompt for an LLM to create a robust Warcraft 3 replay (.w3g) parser in Python. There is NO official documentation for this format, so the implementation must heavily rely on reverse-engineering, inference, and research from existing implementations.

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

### Project Structure (uv/Modern Python Standards)

```
w3g-parser/
├── pyproject.toml              # uv/PEP 621 compliant
├── uv.lock                     # Lock file (generated)
├── src/
│   └── w3g_parser/
│       ├── __init__.py         # Public API exports
│       ├── parser.py           # Main parser orchestration
│       ├── models.py           # Pydantic/dataclass models
│       ├── header.py           # Header parsing logic
│       ├── decompressor.py     # Block decompression
│       ├── actions.py          # Game action parsing
│       ├── chat.py             # Chat message parsing
│       ├── players.py          # Player data parsing
│       ├── versions.py         # Version detection & handling
│       ├── constants.py        # Magic bytes, action IDs, etc.
│       ├── exceptions.py       # Custom exceptions
│       └── cli.py              # Command-line interface
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures
│   ├── test_parser.py
│   ├── test_header.py
│   ├── test_decompressor.py
│   ├── test_actions.py
│   └── test_versions.py
├── docs/
│   └── FORMAT.md               # Discovered format documentation
├── README.md
└── LICENSE
```

### pyproject.toml Template

```toml
[project]
name = "w3g-parser"
version = "0.1.0"
description = "A flexible Warcraft 3 replay (.w3g) parser supporting Classic and Reforged"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
authors = [
    { name = "Your Name", email = "you@example.com" }
]
keywords = ["warcraft", "wc3", "replay", "parser", "w3g", "reforged"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Games/Entertainment :: Real Time Strategy",
]

dependencies = [
    "pydantic>=2.0",
    "click>=8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.1.0",
    "mypy>=1.0",
]

[project.scripts]
w3g-parse = "w3g_parser.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/w3g_parser"]

[tool.ruff]
target-version = "py311"
line-length = 100
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
```

---

## Code Requirements

### 1. Version Detection & Handling

```python
# Example architecture for version handling

from abc import ABC, abstractmethod
from enum import Enum

class W3GVersion(Enum):
    CLASSIC_ROC = "roc"           # Reign of Chaos
    CLASSIC_TFT = "tft"           # The Frozen Throne (pre-1.32)
    REFORGED = "reforged"         # 1.32+
    UNKNOWN = "unknown"

class VersionHandler(ABC):
    """Abstract base for version-specific parsing logic."""
    
    @abstractmethod
    def parse_header(self, data: bytes) -> "ReplayHeader":
        ...
    
    @abstractmethod
    def parse_player_record(self, data: bytes, offset: int) -> tuple["PlayerInfo", int]:
        ...
    
    @abstractmethod
    def parse_action(self, action_id: int, data: bytes, offset: int) -> tuple["GameAction", int]:
        ...

class ClassicHandler(VersionHandler):
    """Handler for Classic WC3 replays (pre-1.32)."""
    ...

class ReforgedHandler(VersionHandler):
    """Handler for Reforged replays (1.32+)."""
    ...

def detect_version(header_bytes: bytes) -> tuple[W3GVersion, VersionHandler]:
    """Auto-detect replay version from header magic/fields."""
    ...
```

### 2. Data Models

Use dataclasses or Pydantic models for all structures:

```python
from dataclasses import dataclass, field
from datetime import timedelta
from enum import IntEnum

class Race(IntEnum):
    HUMAN = 0x01
    ORC = 0x02
    NIGHT_ELF = 0x04
    UNDEAD = 0x08
    RANDOM = 0x20
    # ... add others as discovered

@dataclass
class ReplayHeader:
    """W3G file header information."""
    magic: bytes
    header_size: int
    compressed_size: int
    header_version: int
    decompressed_size: int
    num_compressed_blocks: int
    version_string: str
    build_number: int
    flags: int  # Single player, multiplayer, etc.
    duration_ms: int
    crc32: int
    
    # Derived properties
    @property
    def duration(self) -> timedelta:
        return timedelta(milliseconds=self.duration_ms)

@dataclass
class PlayerInfo:
    """Information about a player in the replay."""
    id: int
    name: str
    race: Race
    team: int
    color: int
    handicap: int
    is_host: bool = False
    is_computer: bool = False
    
    # Computed during action parsing
    actions: list["GameAction"] = field(default_factory=list)
    apm: float = 0.0

@dataclass
class GameSettings:
    """Game configuration and settings."""
    speed: int  # 0=slow, 1=normal, 2=fast
    visibility: int
    observers: int
    teams_together: bool
    lock_teams: bool
    full_shared_control: bool
    random_hero: bool
    random_races: bool
    # ... other settings

@dataclass
class ChatMessage:
    """In-game chat message."""
    timestamp_ms: int
    player_id: int
    player_name: str
    message: str
    mode: int  # All, allies, observers, etc.
    
    @property
    def timestamp(self) -> timedelta:
        return timedelta(milliseconds=self.timestamp_ms)

@dataclass
class GameAction:
    """A player action/command."""
    timestamp_ms: int
    player_id: int
    action_type: int
    action_name: str
    payload: bytes
    # Parsed data varies by action type
    data: dict = field(default_factory=dict)

@dataclass
class W3GReplay:
    """Complete parsed replay."""
    header: ReplayHeader
    game_name: str
    map_name: str
    map_path: str
    host_name: str
    settings: GameSettings
    players: list[PlayerInfo]
    chat_messages: list[ChatMessage]
    actions: list[GameAction]
    
    # Raw data for advanced users
    raw_header: bytes = b""
    raw_decompressed: bytes = b""
```

### 3. Parsing Strategy

```python
class W3GParser:
    """Main parser with streaming/chunked support."""
    
    def __init__(self, strict: bool = False):
        self.strict = strict  # Fail on unknown data vs. skip
        self._version_handler: VersionHandler | None = None
    
    def parse(self, filepath: str | Path) -> W3GReplay:
        """Parse a complete replay file."""
        with open(filepath, "rb") as f:
            return self.parse_stream(f)
    
    def parse_stream(self, stream: BinaryIO) -> W3GReplay:
        """Parse from any binary stream."""
        # 1. Read and parse header
        header_data = stream.read(HEADER_SIZE)
        header = self._parse_header(header_data)
        
        # 2. Detect version and get appropriate handler
        self._version_handler = detect_version(header_data)
        
        # 3. Read and decompress data blocks
        decompressed = self._decompress_blocks(stream, header.num_compressed_blocks)
        
        # 4. Parse game data
        game_data = self._parse_game_data(decompressed)
        
        # 5. Parse actions (can be done lazily)
        actions = self._parse_actions(decompressed, game_data.actions_offset)
        
        return self._build_replay(header, game_data, actions)
    
    def parse_header_only(self, filepath: str | Path) -> ReplayHeader:
        """Quick parse of just the header (for batch processing)."""
        ...
    
    def iter_actions(self, filepath: str | Path) -> Iterator[GameAction]:
        """Lazily iterate actions without loading all into memory."""
        ...
```

### 4. Error Handling

```python
# exceptions.py

class W3GParseError(Exception):
    """Base exception for parsing errors."""
    def __init__(self, message: str, offset: int | None = None):
        self.offset = offset
        super().__init__(f"{message}" + (f" at offset 0x{offset:X}" if offset else ""))

class InvalidHeaderError(W3GParseError):
    """Invalid or unrecognized header format."""
    pass

class UnsupportedVersionError(W3GParseError):
    """Replay version not supported."""
    def __init__(self, version: str):
        super().__init__(f"Unsupported replay version: {version}")
        self.version = version

class DecompressionError(W3GParseError):
    """Failed to decompress data block."""
    pass

class UnknownActionError(W3GParseError):
    """Unknown action type encountered."""
    def __init__(self, action_id: int, offset: int):
        super().__init__(f"Unknown action type 0x{action_id:02X}", offset)
        self.action_id = action_id

# Usage in parser:
def _parse_action(self, action_id: int, data: bytes, offset: int) -> GameAction | None:
    try:
        return self._version_handler.parse_action(action_id, data, offset)
    except UnknownActionError as e:
        if self.strict:
            raise
        # Log warning and skip
        logger.warning(f"Skipping unknown action: {e}")
        return None
```

### 5. Output Formats

```python
import json
from dataclasses import asdict

class W3GReplay:
    # ... other methods ...
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self, filepath: str | Path | None = None, indent: int = 2) -> str:
        """Export to JSON string or file."""
        data = self.to_dict()
        # Handle bytes and special types
        json_str = json.dumps(data, indent=indent, default=self._json_serializer)
        
        if filepath:
            Path(filepath).write_text(json_str)
        return json_str
    
    @staticmethod
    def _json_serializer(obj):
        if isinstance(obj, bytes):
            return obj.hex()
        if isinstance(obj, timedelta):
            return obj.total_seconds()
        raise TypeError(f"Not JSON serializable: {type(obj)}")
    
    def to_dataframe(self) -> "pd.DataFrame":
        """Convert actions to pandas DataFrame (requires pandas)."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas required for DataFrame export: pip install pandas")
        
        return pd.DataFrame([asdict(a) for a in self.actions])
```

---

## CLI Requirements

```python
# cli.py
import click
import json
from pathlib import Path
from .parser import W3GParser

@click.group()
@click.version_option()
def main():
    """W3G Replay Parser - Parse Warcraft 3 replay files."""
    pass

@main.command()
@click.argument("replay", type=click.Path(exists=True))
@click.option("--format", "-f", type=click.Choice(["text", "json"]), default="text")
@click.option("--output", "-o", type=click.Path(), help="Output file (default: stdout)")
@click.option("--indent", type=int, default=2, help="JSON indent level")
def parse(replay: str, format: str, output: str | None, indent: int):
    """Parse a replay file and display information."""
    parser = W3GParser()
    result = parser.parse(replay)
    
    if format == "json":
        out = result.to_json(indent=indent)
    else:
        out = format_replay_text(result)
    
    if output:
        Path(output).write_text(out)
    else:
        click.echo(out)

@main.command()
@click.argument("replay", type=click.Path(exists=True))
def players(replay: str):
    """Show player information."""
    parser = W3GParser()
    result = parser.parse(replay)
    
    for p in result.players:
        click.echo(f"{p.name} - {p.race.name} (Team {p.team}) - APM: {p.apm:.1f}")

@main.command()
@click.argument("replay", type=click.Path(exists=True))
def chat(replay: str):
    """Show chat messages."""
    parser = W3GParser()
    result = parser.parse(replay)
    
    for msg in result.chat_messages:
        ts = str(msg.timestamp).split(".")[0]  # Remove microseconds
        click.echo(f"[{ts}] {msg.player_name}: {msg.message}")

@main.command()
@click.argument("replay", type=click.Path(exists=True))
def info(replay: str):
    """Show basic replay information (fast, header only)."""
    parser = W3GParser()
    header = parser.parse_header_only(replay)
    
    click.echo(f"Version: {header.version_string}")
    click.echo(f"Duration: {header.duration}")
    click.echo(f"Build: {header.build_number}")

@main.command()
@click.argument("replays", type=click.Path(exists=True), nargs=-1)
@click.option("--output", "-o", type=click.Path(), required=True)
def batch(replays: tuple[str], output: str):
    """Parse multiple replays to a JSON array."""
    parser = W3GParser(strict=False)
    results = []
    
    for replay_path in replays:
        try:
            result = parser.parse(replay_path)
            results.append(result.to_dict())
        except Exception as e:
            click.echo(f"Error parsing {replay_path}: {e}", err=True)
    
    Path(output).write_text(json.dumps(results, indent=2, default=str))
    click.echo(f"Parsed {len(results)} replays to {output}")

if __name__ == "__main__":
    main()
```

---

## Target Public API

```python
from w3g_parser import W3GReplay, W3GParser

# Simple usage - class method
replay = W3GReplay.parse("my_replay.w3g")

# Or via parser instance for configuration
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

# Iterate actions
for action in replay.actions:
    if action.action_name == "unit_order":
        print(f"{action.timestamp_ms}ms: Player {action.player_id} - {action.data}")

# Export
replay.to_json("output.json")
data = replay.to_dict()

# Quick header check (no full parse)
header = W3GParser().parse_header_only("replay.w3g")
print(f"Version: {header.version_string}, Duration: {header.duration}")

# Memory-efficient action iteration
for action in parser.iter_actions("large_replay.w3g"):
    process_action(action)
```

---

## Documentation Requirements

Create a `docs/FORMAT.md` that documents everything discovered:

```markdown
# W3G Binary Format Specification

This document describes the W3G replay format as reverse-engineered from
existing parsers and replay analysis.

## Sources

- [repo1](url) - Description of what was learned
- [repo2](url) - Description
- ...

## Header Structure

### Classic Format (pre-1.32)

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x00   | 28   | char | Magic string "Warcraft III recorded game\x1A" |
| 0x1C   | 4    | u32  | Header size (offset to compressed data) |
| ...    | ...  | ...  | ... |

### Reforged Format (1.32+)

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| ...    | ...  | ...  | ... |

## Compressed Data Blocks

...

## Action Types

| ID   | Name           | Payload Structure |
|------|----------------|-------------------|
| 0x10 | Unit Ability   | ... |
| 0x11 | Unit Order     | ... |
| ...  | ...            | ... |

## Unknown/Undocumented Fields

- Offset 0x?? in header: Unknown 4 bytes, observed values: ...
- Action 0x??: Unknown action, appears in Reforged only
```

---

## Testing Strategy

```python
# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def sample_replay_path():
    """Path to a sample replay for testing (user must provide)."""
    path = Path("tests/fixtures/sample.w3g")
    if not path.exists():
        pytest.skip("No sample replay available")
    return path

@pytest.fixture
def mock_classic_header():
    """Minimal valid classic header bytes for unit testing."""
    return bytes([
        # Magic string (28 bytes)
        *b"Warcraft III recorded game\x1A\x00",
        # Header size (4 bytes, little endian)
        0x44, 0x00, 0x00, 0x00,
        # ... etc
    ])

# tests/test_header.py
def test_detect_classic_version(mock_classic_header):
    from w3g_parser.versions import detect_version, W3GVersion
    
    version, handler = detect_version(mock_classic_header)
    assert version == W3GVersion.CLASSIC_TFT

def test_parse_header(mock_classic_header):
    from w3g_parser.header import parse_header
    
    header = parse_header(mock_classic_header)
    assert header.magic == b"Warcraft III recorded game\x1A\x00"
    # ... more assertions

# tests/test_parser.py
def test_full_parse(sample_replay_path):
    from w3g_parser import W3GParser
    
    parser = W3GParser()
    replay = parser.parse(sample_replay_path)
    
    assert replay.header is not None
    assert len(replay.players) > 0
    assert replay.map_name != ""

def test_partial_parse_on_corruption():
    """Parser should extract what it can from corrupted replays."""
    from w3g_parser import W3GParser
    
    parser = W3GParser(strict=False)
    # Create truncated/corrupted data
    # ... test that header parsing still works
```

---

## Important Implementation Notes

1. **The format is NOT officially documented** - Your code IS the documentation. Add extensive comments explaining:
   - What each byte/field means
   - How you determined its purpose
   - Which existing parser you learned this from

2. **Mark uncertainty clearly:**
   ```python
   # Unknown field - possibly CRC or reserved
   # Observed values: 0x00000000, 0xFFFFFFFF
   # See: github.com/example/w3gjs/blob/main/src/parser.js#L123
   self.unknown_field_1 = struct.unpack("<I", data[offset:offset+4])[0]
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
   - Provide lazy iteration options
   - Consider memory-mapped file access for very large files

---

## Checklist Before Completion

- [ ] Researched at least 5 existing w3g parser implementations
- [ ] Documented discovered format in FORMAT.md
- [ ] Parser handles Classic WC3 replays
- [ ] Parser handles Reforged replays  
- [ ] Version auto-detection works
- [ ] All data models have full type hints
- [ ] Error handling is graceful in non-strict mode
- [ ] CLI tool works with all commands
- [ ] JSON export works correctly
- [ ] Unit tests pass
- [ ] Code passes ruff and mypy checks
- [ ] README has usage examples
