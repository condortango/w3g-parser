"""Data models for W3G replay parsing."""

from dataclasses import dataclass, field
from datetime import timedelta
from enum import IntEnum, auto
import json
from pathlib import Path
from typing import Any


class Race(IntEnum):
    """Player race."""

    HUMAN = 0x01
    ORC = 0x02
    NIGHT_ELF = 0x04
    UNDEAD = 0x08
    RANDOM = 0x20
    SELECTABLE = 0x40
    UNKNOWN = 0xFF

    @classmethod
    def from_flags(cls, flags: int) -> "Race":
        """Get race from race flags byte."""
        if flags & 0x01:
            return cls.HUMAN
        if flags & 0x02:
            return cls.ORC
        if flags & 0x04:
            return cls.NIGHT_ELF
        if flags & 0x08:
            return cls.UNDEAD
        if flags & 0x20:
            return cls.RANDOM
        if flags & 0x40:
            return cls.SELECTABLE
        return cls.UNKNOWN


class W3GVersion(IntEnum):
    """W3G replay version type."""

    CLASSIC_ROC = auto()  # Reign of Chaos
    CLASSIC_TFT = auto()  # The Frozen Throne (pre-1.32)
    REFORGED = auto()  # 1.32+
    UNKNOWN = auto()


class SlotStatus(IntEnum):
    """Slot status in game lobby."""

    EMPTY = 0x00
    CLOSED = 0x01
    USED = 0x02


class LeaveResult(IntEnum):
    """Result when player leaves."""

    LEFT = 0x01
    LEFT_ALT = 0x07
    LOST = 0x08
    WON = 0x09
    DRAW = 0x0A
    OBSERVER_LEFT = 0x0B


@dataclass
class ReplayHeader:
    """W3G file header information."""

    magic: bytes
    header_size: int
    compressed_size: int
    header_version: int
    decompressed_size: int
    num_compressed_blocks: int

    # SubHeader fields
    game_identifier: str  # 'WAR3', 'W3XP', 'PX3W'
    version: int
    build_number: int
    flags: int
    duration_ms: int
    crc32: int

    # Raw data
    raw_header: bytes = b""

    @property
    def duration(self) -> timedelta:
        """Get replay duration as timedelta."""
        return timedelta(milliseconds=self.duration_ms)

    @property
    def is_multiplayer(self) -> bool:
        """Check if replay is from multiplayer game."""
        return bool(self.flags & 0x8000)

    @property
    def is_reforged(self) -> bool:
        """Check if this is a Reforged replay."""
        return self.version >= 29 or self.game_identifier == "PX3W"

    @property
    def is_expansion(self) -> bool:
        """Check if this is Frozen Throne or Reforged."""
        return self.game_identifier in ("W3XP", "PX3W")

    @property
    def version_string(self) -> str:
        """Get human-readable version string."""
        # Reforged uses build number for version identification
        if self.is_reforged:
            # Map known build numbers to versions
            build_to_version = {
                6105: "1.32.0",
                6106: "1.32.1",
                6108: "1.32.2",
                6110: "1.32.3",
                6111: "1.32.4",
                6112: "1.32.5",
                6113: "1.32.6",
                6114: "1.32.7",
                6115: "1.32.8",
                6116: "1.32.9",
                6117: "1.32.10",
                6118: "1.33.0",
                6119: "1.34.0",
                6120: "1.35.0",
                6121: "1.36.0",
                6122: "1.36.1",
                6123: "1.36.2",
            }
            if self.build_number in build_to_version:
                return build_to_version[self.build_number]
            # Fallback: estimate version from build
            return f"1.3x (build {self.build_number})"

        # Classic format: version is stored as patch number
        if self.version >= 10000:
            major = self.version // 10000
            minor = (self.version % 10000) // 100
            patch = self.version % 100
            if patch:
                return f"{major}.{minor}.{patch}"
            return f"{major}.{minor}"
        else:
            # Simple version number (e.g., 26 for 1.26)
            return f"1.{self.version}"


@dataclass
class PlayerInfo:
    """Information about a player in the replay."""

    id: int
    name: str
    race: Race = Race.UNKNOWN
    team: int = 0
    color: int = 0
    handicap: int = 100
    is_host: bool = False
    is_computer: bool = False
    is_observer: bool = False
    slot_status: SlotStatus = SlotStatus.USED

    # Runtime for ladder games (ms)
    runtime_ms: int = 0

    # Computed during action parsing
    action_count: int = 0
    apm: float = 0.0

    # Leave information
    leave_result: LeaveResult | None = None
    leave_time_ms: int | None = None


@dataclass
class GameSettings:
    """Game configuration and settings."""

    speed: int = 2  # 0=slow, 1=normal, 2=fast
    visibility: int = 0
    observers: int = 0
    teams_together: bool = False
    lock_teams: bool = False
    full_shared_control: bool = False
    random_hero: bool = False
    random_races: bool = False
    referees: bool = False
    map_checksum: bytes = b""

    @property
    def speed_name(self) -> str:
        """Get human-readable speed name."""
        return ["Slow", "Normal", "Fast"][min(self.speed, 2)]


@dataclass
class ChatMessage:
    """In-game chat message."""

    timestamp_ms: int
    player_id: int
    player_name: str
    message: str
    mode: int  # 0=all, 1=allies, 2=observers, 3+=specific player
    is_startup: bool = False

    @property
    def timestamp(self) -> timedelta:
        """Get message timestamp as timedelta."""
        return timedelta(milliseconds=self.timestamp_ms)

    @property
    def mode_name(self) -> str:
        """Get human-readable mode name."""
        if self.mode == 0:
            return "All"
        elif self.mode == 1:
            return "Allies"
        elif self.mode == 2:
            return "Observers"
        else:
            return f"Player {self.mode - 2}"


@dataclass
class GameAction:
    """A player action/command."""

    timestamp_ms: int
    player_id: int
    action_type: int
    action_name: str
    payload: bytes = b""
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def timestamp(self) -> timedelta:
        """Get action timestamp as timedelta."""
        return timedelta(milliseconds=self.timestamp_ms)


@dataclass
class W3GReplay:
    """Complete parsed replay."""

    header: ReplayHeader
    game_name: str = ""
    map_name: str = ""
    map_path: str = ""
    host_name: str = ""
    settings: GameSettings = field(default_factory=GameSettings)
    players: list[PlayerInfo] = field(default_factory=list)
    chat_messages: list[ChatMessage] = field(default_factory=list)
    actions: list[GameAction] = field(default_factory=list)

    # Raw data for advanced users
    raw_decompressed: bytes = b""

    def get_player(self, player_id: int) -> PlayerInfo | None:
        """Get player by ID."""
        for player in self.players:
            if player.id == player_id:
                return player
        return None

    def get_player_by_name(self, name: str) -> PlayerInfo | None:
        """Get player by name (case-insensitive)."""
        name_lower = name.lower()
        for player in self.players:
            if player.name.lower() == name_lower:
                return player
        return None

    @property
    def winner(self) -> PlayerInfo | None:
        """Get the winning player, if determinable."""
        for player in self.players:
            if player.leave_result == LeaveResult.WON:
                return player
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "header": {
                "magic": self.header.magic.hex(),
                "header_size": self.header.header_size,
                "compressed_size": self.header.compressed_size,
                "header_version": self.header.header_version,
                "decompressed_size": self.header.decompressed_size,
                "num_compressed_blocks": self.header.num_compressed_blocks,
                "game_identifier": self.header.game_identifier,
                "version": self.header.version,
                "version_string": self.header.version_string,
                "build_number": self.header.build_number,
                "is_multiplayer": self.header.is_multiplayer,
                "is_reforged": self.header.is_reforged,
                "is_expansion": self.header.is_expansion,
                "duration_ms": self.header.duration_ms,
                "duration": str(self.header.duration),
            },
            "game_name": self.game_name,
            "map_name": self.map_name,
            "map_path": self.map_path,
            "host_name": self.host_name,
            "settings": {
                "speed": self.settings.speed,
                "speed_name": self.settings.speed_name,
                "visibility": self.settings.visibility,
                "observers": self.settings.observers,
                "teams_together": self.settings.teams_together,
                "lock_teams": self.settings.lock_teams,
                "full_shared_control": self.settings.full_shared_control,
                "random_hero": self.settings.random_hero,
                "random_races": self.settings.random_races,
            },
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "race": p.race.name,
                    "team": p.team,
                    "color": p.color,
                    "handicap": p.handicap,
                    "is_host": p.is_host,
                    "is_computer": p.is_computer,
                    "is_observer": p.is_observer,
                    "action_count": p.action_count,
                    "apm": round(p.apm, 1),
                    "leave_result": p.leave_result.name if p.leave_result else None,
                }
                for p in self.players
            ],
            "chat_messages": [
                {
                    "timestamp_ms": c.timestamp_ms,
                    "timestamp": str(c.timestamp),
                    "player_id": c.player_id,
                    "player_name": c.player_name,
                    "message": c.message,
                    "mode": c.mode,
                    "mode_name": c.mode_name,
                }
                for c in self.chat_messages
            ],
            "action_count": len(self.actions),
        }

    def to_json(self, filepath: str | Path | None = None, indent: int = 2) -> str:
        """Export to JSON string or file."""
        data = self.to_dict()
        json_str = json.dumps(data, indent=indent, ensure_ascii=False)

        if filepath:
            Path(filepath).write_text(json_str, encoding="utf-8")
        return json_str

    @classmethod
    def parse(cls, filepath: str | Path) -> "W3GReplay":
        """Parse a replay file. Convenience method."""
        from w3g_parser.parser import W3GParser

        return W3GParser().parse(filepath)
