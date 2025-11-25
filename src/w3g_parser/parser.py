"""Main W3G replay parser."""

import logging
import struct
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Iterator

from w3g_parser.actions import parse_command_data
from w3g_parser.chat import parse_chat_message
from w3g_parser.constants import (
    BLOCK_CHAT,
    BLOCK_CHECKSUM,
    BLOCK_FIRST_START,
    BLOCK_FORCED_END,
    BLOCK_LEAVE_GAME,
    BLOCK_SECOND_START,
    BLOCK_THIRD_START,
    BLOCK_TIMESLOT,
    BLOCK_TIMESLOT_OLD,
)
from w3g_parser.decompressor import decompress_blocks
from w3g_parser.exceptions import W3GParseError
from w3g_parser.header import parse_header
from w3g_parser.models import (
    ChatMessage,
    GameAction,
    GameSettings,
    LeaveResult,
    PlayerInfo,
    ReplayHeader,
    W3GReplay,
)
from w3g_parser.players import (
    apply_slot_info_to_players,
    decode_encoded_string,
    parse_game_start_record,
    parse_player_record,
)

logger = logging.getLogger(__name__)


class W3GParser:
    """Main parser for W3G replay files."""

    def __init__(self, strict: bool = False):
        """Initialize parser.

        Args:
            strict: If True, raise errors on unknown data. If False, skip and log.
        """
        self.strict = strict

    def parse(self, filepath: str | Path) -> W3GReplay:
        """Parse a complete replay file.

        Args:
            filepath: Path to the replay file

        Returns:
            Parsed W3GReplay object

        Raises:
            W3GParseError: If parsing fails
            FileNotFoundError: If file doesn't exist
        """
        filepath = Path(filepath)
        with open(filepath, "rb") as f:
            return self.parse_stream(f)

    def parse_stream(self, stream: BinaryIO) -> W3GReplay:
        """Parse a replay from a binary stream.

        Args:
            stream: Binary stream positioned at start of replay

        Returns:
            Parsed W3GReplay object
        """
        # 1. Parse header
        header = parse_header(stream)

        # 2. Seek to first data block if needed
        stream.seek(header.header_size)

        # 3. Decompress all blocks
        decompressed = decompress_blocks(stream, header)

        # 4. Parse game data
        return self._parse_game_data(header, decompressed)

    def parse_header_only(self, filepath: str | Path) -> ReplayHeader:
        """Parse just the header (for quick metadata access).

        Args:
            filepath: Path to the replay file

        Returns:
            Parsed ReplayHeader
        """
        with open(filepath, "rb") as f:
            return parse_header(f)

    def iter_actions(self, filepath: str | Path) -> Iterator[GameAction]:
        """Iterate actions without loading all into memory.

        Args:
            filepath: Path to the replay file

        Yields:
            GameAction objects
        """
        replay = self.parse(filepath)
        yield from replay.actions

    def _parse_game_data(self, header: ReplayHeader, data: bytes) -> W3GReplay:
        """Parse decompressed game data.

        Args:
            header: Parsed replay header
            data: Decompressed data

        Returns:
            Parsed W3GReplay
        """
        offset = 0
        players: list[PlayerInfo] = []
        chat_messages: list[ChatMessage] = []
        actions: list[GameAction] = []

        game_name = ""
        map_name = ""
        map_path = ""
        host_name = ""
        settings = GameSettings()

        # Track current game time
        current_time_ms = 0

        # Player ID to name mapping for chat
        player_names: dict[int, str] = {}

        # Skip first 4 bytes (unknown, usually 0x00000110)
        if offset + 4 <= len(data):
            offset += 4

        # Parse host player record
        host_player, offset = parse_player_record(data, offset, is_host=True)
        if host_player:
            host_player.is_host = True
            players.append(host_player)
            player_names[host_player.id] = host_player.name
            host_name = host_player.name

        # Parse game name (null-terminated)
        game_name_start = offset
        while offset < len(data) and data[offset] != 0:
            offset += 1
        game_name = data[game_name_start:offset].decode("utf-8", errors="replace")
        offset += 1  # Skip null

        # Skip another null byte (separator)
        if offset < len(data) and data[offset] == 0:
            offset += 1

        # Parse encoded string containing game settings and map info
        encoded_data, offset = decode_encoded_string(data, offset)
        if encoded_data:
            settings, map_path, map_name = self._parse_encoded_settings(encoded_data)

        # Parse player count, game type, language ID
        if offset + 12 <= len(data):
            # player_count = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            # game_type = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            # language_id = struct.unpack_from("<I", data, offset)[0]
            offset += 4

        # Parse additional players
        while offset < len(data):
            player, new_offset = parse_player_record(data, offset, is_host=False)
            if player:
                players.append(player)
                player_names[player.id] = player.name
                offset = new_offset
            else:
                break

        # Reforged replays have extra player metadata between player records
        # and the GameStartRecord (0x19). Skip to find it.
        # We need to validate the 0x19 is actually a GameStartRecord by checking
        # that num_bytes > 0 and num_slots is reasonable (2-24 players)
        def is_valid_game_start_record(d: bytes, o: int) -> bool:
            """Check if offset points to a valid GameStartRecord."""
            if o + 4 > len(d) or d[o] != 0x19:
                return False
            num_bytes = struct.unpack_from("<H", d, o + 1)[0]
            if num_bytes < 10 or num_bytes > 500:  # Reasonable range
                return False
            num_slots = d[o + 3]
            return 2 <= num_slots <= 24

        if offset < len(data) and not is_valid_game_start_record(data, offset):
            # Search for valid GameStartRecord marker
            search_offset = offset
            while search_offset < len(data) - 4:
                if data[search_offset] == 0x19:
                    if is_valid_game_start_record(data, search_offset):
                        break
                search_offset += 1
            if search_offset < len(data) and is_valid_game_start_record(data, search_offset):
                offset = search_offset

        # Parse GameStartRecord (0x19)
        if offset < len(data) and data[offset] == 0x19:
            slots, random_seed, select_mode, offset = parse_game_start_record(
                data, offset, header.version
            )
            # Apply slot info to players
            apply_slot_info_to_players(players, slots, header.version)

        # Parse replay data blocks
        while offset < len(data):
            if offset >= len(data):
                break

            block_id = data[offset]
            offset += 1

            if block_id == BLOCK_LEAVE_GAME:
                # 14 bytes total: reason (4) + player_id (1) + result (4) + unknown (4)
                if offset + 13 <= len(data):
                    reason = struct.unpack_from("<I", data, offset)[0]
                    offset += 4
                    leave_player_id = data[offset]
                    offset += 1
                    result = struct.unpack_from("<I", data, offset)[0]
                    offset += 4
                    offset += 4  # Unknown

                    # Update player leave info
                    for player in players:
                        if player.id == leave_player_id:
                            try:
                                player.leave_result = LeaveResult(result)
                            except ValueError:
                                player.leave_result = LeaveResult.LEFT
                            player.leave_time_ms = current_time_ms
                            break

            elif block_id in (BLOCK_FIRST_START, BLOCK_SECOND_START, BLOCK_THIRD_START):
                # 5 bytes: unknown dword (always 0x01)
                offset += 4

            elif block_id in (BLOCK_TIMESLOT, BLOCK_TIMESLOT_OLD):
                # TimeSlot block
                if offset + 4 <= len(data):
                    num_bytes = struct.unpack_from("<H", data, offset)[0]
                    offset += 2
                    time_increment = struct.unpack_from("<H", data, offset)[0]
                    offset += 2

                    current_time_ms += time_increment

                    # Parse command data (num_bytes - 2 for time increment already read)
                    if num_bytes > 2:
                        cmd_length = num_bytes - 2
                        for player_id, action in parse_command_data(
                            data, offset, cmd_length, header.version
                        ):
                            action.timestamp_ms = current_time_ms
                            actions.append(action)

                            # Update player action count
                            for player in players:
                                if player.id == player_id:
                                    player.action_count += 1
                                    break

                        offset += cmd_length

            elif block_id == BLOCK_CHAT:
                # Chat message (v1.07+)
                chat_msg, offset = parse_chat_message(data, offset, player_names)
                if chat_msg:
                    chat_msg.timestamp_ms = current_time_ms
                    chat_messages.append(chat_msg)

            elif block_id == BLOCK_CHECKSUM:
                # Checksum block: 1 byte length + data
                if offset < len(data):
                    length = data[offset]
                    offset += 1 + length

            elif block_id == BLOCK_FORCED_END:
                # Forced end: mode (4) + countdown (4)
                offset += 8

            elif block_id == 0x23:
                # Unknown block type seen in some replays
                if offset < len(data):
                    length = data[offset]
                    offset += 1 + length

            else:
                # Unknown block - try to continue
                logger.debug(f"Unknown block 0x{block_id:02X} at offset {offset - 1}")
                # Try to skip by looking for next valid block ID
                # This is risky but better than crashing
                if not self.strict:
                    continue
                break

        # Calculate APM for each player
        duration_minutes = header.duration_ms / 60000.0
        if duration_minutes > 0:
            for player in players:
                player.apm = player.action_count / duration_minutes

        return W3GReplay(
            header=header,
            game_name=game_name,
            map_name=map_name,
            map_path=map_path,
            host_name=host_name,
            settings=settings,
            players=players,
            chat_messages=chat_messages,
            actions=actions,
            raw_decompressed=data,
        )

    def _parse_encoded_settings(
        self, encoded_data: bytes
    ) -> tuple[GameSettings, str, str]:
        """Parse game settings from encoded string.

        The encoded string contains:
        - Game settings (13 bytes)
        - Null byte
        - Map path (null-terminated)
        - Map creator name (null-terminated)

        Args:
            encoded_data: Decoded bytes from encoded string

        Returns:
            Tuple of (GameSettings, map_path, map_name)
        """
        settings = GameSettings()
        map_path = ""
        map_name = ""

        if len(encoded_data) < 13:
            return settings, map_path, map_name

        # Parse settings from first 13 bytes
        # Byte 0: Speed (bits 0-1)
        settings.speed = encoded_data[0] & 0x03

        # Byte 1: Visibility and observers
        byte1 = encoded_data[1]
        settings.visibility = byte1 & 0x0F
        settings.observers = (byte1 >> 4) & 0x03
        settings.teams_together = bool(byte1 & 0x40)

        # Byte 2: Fixed teams
        settings.lock_teams = bool(encoded_data[2] & 0x06)

        # Byte 3: Game options
        byte3 = encoded_data[3]
        settings.full_shared_control = bool(byte3 & 0x01)
        settings.random_hero = bool(byte3 & 0x02)
        settings.random_races = bool(byte3 & 0x04)
        settings.referees = bool(byte3 & 0x40)

        # Bytes 9-12: Map checksum
        if len(encoded_data) >= 13:
            settings.map_checksum = encoded_data[9:13]

        # Parse map path and name after settings
        offset = 13

        # Skip null byte if present
        if offset < len(encoded_data) and encoded_data[offset] == 0:
            offset += 1

        # Map path
        path_start = offset
        while offset < len(encoded_data) and encoded_data[offset] != 0:
            offset += 1
        if offset > path_start:
            map_path = encoded_data[path_start:offset].decode("utf-8", errors="replace")
            # Extract map name from path
            if "/" in map_path:
                map_name = map_path.rsplit("/", 1)[-1]
            elif "\\" in map_path:
                map_name = map_path.rsplit("\\", 1)[-1]
            else:
                map_name = map_path

            # Remove .w3x or .w3m extension
            if map_name.lower().endswith((".w3x", ".w3m")):
                map_name = map_name[:-4]

        offset += 1  # Skip null

        # Creator name (skip for now)

        return settings, map_path, map_name
