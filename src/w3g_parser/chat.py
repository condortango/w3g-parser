"""Chat message parsing for W3G replay files."""

import struct

from w3g_parser.constants import CHAT_FLAG_NORMAL, CHAT_FLAG_STARTUP
from w3g_parser.models import ChatMessage


def parse_chat_message(
    data: bytes, offset: int, player_names: dict[int, str]
) -> tuple[ChatMessage | None, int]:
    """Parse a chat message block.

    Chat message structure (v1.07+):
    - 1 byte: Sender ID
    - 1 word: Message length (n)
    - 1 byte: Flags (0x10=startup, 0x20=normal)
    - 1 dword: Chat mode (if flag=0x20): 0=all, 1=allies, 2=observers, 3+=player
    - n bytes: Message text (null-terminated)

    Args:
        data: Block data (after block ID)
        offset: Starting offset
        player_names: Mapping of player ID to name

    Returns:
        Tuple of (ChatMessage or None, new offset)
    """
    if offset + 4 > len(data):
        return None, offset

    player_id = data[offset]
    offset += 1

    msg_length = struct.unpack_from("<H", data, offset)[0]
    offset += 2

    flags = data[offset]
    offset += 1

    mode = 0
    is_startup = False

    if flags == CHAT_FLAG_STARTUP:
        is_startup = True
    elif flags == CHAT_FLAG_NORMAL:
        if offset + 4 <= len(data):
            mode = struct.unpack_from("<I", data, offset)[0]
            offset += 4
    else:
        # Unknown flag, try to continue
        pass

    # Read message text
    msg_start = offset
    while offset < len(data) and data[offset] != 0:
        offset += 1
    message = data[msg_start:offset].decode("utf-8", errors="replace")
    offset += 1  # Skip null terminator

    player_name = player_names.get(player_id, f"Player {player_id}")

    return ChatMessage(
        timestamp_ms=0,  # Set by caller
        player_id=player_id,
        player_name=player_name,
        message=message,
        mode=mode,
        is_startup=is_startup,
    ), offset
