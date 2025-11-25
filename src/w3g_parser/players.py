"""Player data parsing for W3G replay files."""

import struct
import logging

from w3g_parser.constants import (
    OBSERVER_TEAM_CLASSIC,
    OBSERVER_TEAM_REFORGED,
    RECORD_ADDITIONAL_PLAYER,
    RECORD_HOST,
    REFORGED_VERSION_THRESHOLD,
    SLOT_USED,
)
from w3g_parser.models import PlayerInfo, Race, SlotStatus

logger = logging.getLogger(__name__)


def decode_encoded_string(data: bytes, offset: int) -> tuple[bytes, int]:
    """Decode the encoded string format used in W3G.

    The encoding uses a control-byte scheme where every even byte-value
    was incremented by 1 (so all encoded bytes are odd). Control bytes
    use bits 1-7 to indicate whether the next 7 bytes are encoded
    (bit=0: subtract 1) or literal (bit=1).

    Args:
        data: Raw data
        offset: Starting offset

    Returns:
        Tuple of (decoded bytes, new offset after string)
    """
    result = bytearray()
    pos = offset

    while pos < len(data):
        # Read control byte
        if pos >= len(data):
            break
        control = data[pos]
        pos += 1

        if control == 0:
            # End of encoded string
            break

        # Process next 7 bytes based on control bits
        for bit in range(7):
            if pos >= len(data):
                break

            byte = data[pos]
            pos += 1

            if byte == 0:
                # End of string
                result.append(0)
                return bytes(result), pos

            # Check if this byte is encoded (bit is 0) or literal (bit is 1)
            if (control & (1 << (bit + 1))) == 0:
                # Encoded: subtract 1
                result.append(byte - 1)
            else:
                # Literal
                result.append(byte)

    return bytes(result), pos


def parse_player_record(data: bytes, offset: int, is_host: bool = False) -> tuple[PlayerInfo | None, int]:
    """Parse a player record from decompressed data.

    Player record structure:
    - 1 byte: Record ID (0x00 for host, 0x16 for additional)
    - 1 byte: Player ID
    - n bytes: Player name (null-terminated)
    - 1 byte: Additional data size (0x01 for custom, 0x08 for ladder)
    - Additional data (1 or 8 bytes)

    Args:
        data: Decompressed data
        offset: Starting offset
        is_host: Whether this is the host record

    Returns:
        Tuple of (PlayerInfo or None, new offset)
    """
    if offset >= len(data):
        return None, offset

    record_id = data[offset]
    offset += 1

    # Validate record ID
    expected_id = RECORD_HOST if is_host else RECORD_ADDITIONAL_PLAYER
    if record_id != expected_id:
        # Not a player record, backtrack
        return None, offset - 1

    if offset >= len(data):
        return None, offset

    player_id = data[offset]
    offset += 1

    # Read player name (null-terminated)
    name_start = offset
    while offset < len(data) and data[offset] != 0:
        offset += 1
    name = data[name_start:offset].decode("utf-8", errors="replace")
    offset += 1  # Skip null terminator

    if offset >= len(data):
        return PlayerInfo(id=player_id, name=name, is_host=is_host), offset

    # Additional data size
    extra_size = data[offset]
    offset += 1

    runtime_ms = 0
    race = Race.UNKNOWN

    if extra_size == 0x01:
        # Custom game: 1 null byte
        offset += 1
    elif extra_size == 0x08:
        # Ladder game: 4 bytes runtime + 4 bytes race flags
        if offset + 8 <= len(data):
            runtime_ms = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            race_flags = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            race = Race.from_flags(race_flags)
    else:
        # Unknown format, skip reported bytes
        offset += extra_size

    return PlayerInfo(
        id=player_id,
        name=name,
        race=race,
        is_host=is_host,
        runtime_ms=runtime_ms,
    ), offset


def parse_slot_record(data: bytes, offset: int, version: int) -> tuple[dict, int]:
    """Parse a slot record from GameStartRecord.

    Slot record structure (varies by version):
    - 1 byte: Player ID (0x00 for computer)
    - 1 byte: Download percent
    - 1 byte: Slot status
    - 1 byte: Computer flag
    - 1 byte: Team number
    - 1 byte: Color
    - 1 byte: Race flags
    - 1 byte: AI strength (v1.03+)
    - 1 byte: Handicap (v1.07+)

    Args:
        data: Decompressed data
        offset: Starting offset
        version: Game version number

    Returns:
        Tuple of (slot dict, new offset)
    """
    slot = {}

    # Determine slot size based on version
    if version < 3:
        slot_size = 7
    elif version < 7:
        slot_size = 8
    else:
        slot_size = 9

    if offset + slot_size > len(data):
        return slot, offset

    slot["player_id"] = data[offset]
    slot["download_percent"] = data[offset + 1]
    slot["slot_status"] = data[offset + 2]
    slot["is_computer"] = data[offset + 3] == 0x01
    slot["team"] = data[offset + 4]
    slot["color"] = data[offset + 5]
    slot["race_flags"] = data[offset + 6]

    if slot_size >= 8:
        slot["ai_strength"] = data[offset + 7]
    if slot_size >= 9:
        slot["handicap"] = data[offset + 8]
    else:
        slot["handicap"] = 100

    return slot, offset + slot_size


def parse_game_start_record(
    data: bytes, offset: int, version: int
) -> tuple[list[dict], int, int, int]:
    """Parse the GameStartRecord.

    Structure:
    - 1 byte: Record ID (0x19)
    - 1 word: Number of following data bytes
    - 1 byte: Number of slot records
    - n slot records
    - 1 dword: Random seed
    - 1 byte: Select mode
    - 1 byte: Start spot count

    Args:
        data: Decompressed data
        offset: Starting offset
        version: Game version number

    Returns:
        Tuple of (slot list, random_seed, select_mode, new offset)
    """
    if offset >= len(data) or data[offset] != 0x19:
        return [], 0, 0, offset

    offset += 1

    if offset + 2 > len(data):
        return [], 0, 0, offset

    # Number of following bytes
    num_bytes = struct.unpack_from("<H", data, offset)[0]
    offset += 2

    if offset >= len(data):
        return [], 0, 0, offset

    # Number of slot records
    num_slots = data[offset]
    offset += 1

    # Parse slot records
    slots = []
    for _ in range(num_slots):
        slot, offset = parse_slot_record(data, offset, version)
        if slot:
            slots.append(slot)

    # Random seed
    random_seed = 0
    if offset + 4 <= len(data):
        random_seed = struct.unpack_from("<I", data, offset)[0]
        offset += 4

    # Select mode
    select_mode = 0
    if offset < len(data):
        select_mode = data[offset]
        offset += 1

    # Start spot count
    if offset < len(data):
        offset += 1  # Skip start spot count

    return slots, random_seed, select_mode, offset


def apply_slot_info_to_players(
    players: list[PlayerInfo], slots: list[dict], version: int
) -> None:
    """Apply slot information to player records.

    Args:
        players: List of player info objects
        slots: List of slot dictionaries
        version: Game version for observer detection
    """
    # Build player ID to player mapping
    player_map = {p.id: p for p in players}

    # Observer team ID depends on version
    observer_team = (
        OBSERVER_TEAM_REFORGED
        if version >= REFORGED_VERSION_THRESHOLD
        else OBSERVER_TEAM_CLASSIC
    )

    for slot in slots:
        slot_status = slot.get("slot_status", 0)
        if slot_status != SLOT_USED:
            continue

        player_id = slot.get("player_id", 0)
        is_computer = slot.get("is_computer", False)

        if is_computer:
            # Create computer player
            computer = PlayerInfo(
                id=player_id,
                name=f"Computer {player_id}",
                is_computer=True,
                team=slot.get("team", 0),
                color=slot.get("color", 0),
                race=Race.from_flags(slot.get("race_flags", 0)),
                handicap=slot.get("handicap", 100),
                slot_status=SlotStatus.USED,
            )
            players.append(computer)
        elif player_id in player_map:
            # Update existing player
            player = player_map[player_id]
            player.team = slot.get("team", 0)
            player.color = slot.get("color", 0)
            player.handicap = slot.get("handicap", 100)
            player.slot_status = SlotStatus(slot_status)

            # Set race if not already set from ladder info
            if player.race == Race.UNKNOWN:
                player.race = Race.from_flags(slot.get("race_flags", 0))

            # Check if observer
            if player.team == observer_team:
                player.is_observer = True
