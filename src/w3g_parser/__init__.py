"""W3G Replay Parser - A flexible Warcraft 3 replay (.w3g) parser."""

from w3g_parser.models import (
    ChatMessage,
    GameAction,
    GameSettings,
    PlayerInfo,
    Race,
    ReplayHeader,
    W3GReplay,
)
from w3g_parser.parser import W3GParser

__all__ = [
    "W3GParser",
    "W3GReplay",
    "ReplayHeader",
    "PlayerInfo",
    "GameSettings",
    "ChatMessage",
    "GameAction",
    "Race",
]

__version__ = "0.1.0"
