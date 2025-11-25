"""Action parsing for W3G replay files."""

import struct
import logging
from typing import Iterator

from w3g_parser.constants import (
    ACTION_ABILITY_DROP_ITEM,
    ACTION_ABILITY_NO_PARAMS,
    ACTION_ABILITY_POS_OBJECT,
    ACTION_ABILITY_TARGET_POS,
    ACTION_ABILITY_TWO_POS,
    ACTION_ALLY_OPTIONS,
    ACTION_ASSIGN_GROUP,
    ACTION_BUILDING_MENU,
    ACTION_CANCEL_HERO_REVIVAL,
    ACTION_CHANGE_SELECTION,
    ACTION_CONTINUE_GAME_A,
    ACTION_CONTINUE_GAME_B,
    ACTION_DEC_SPEED,
    ACTION_ESC_PRESSED,
    ACTION_HERO_SKILL_MENU,
    ACTION_INC_SPEED,
    ACTION_MINIMAP_SIGNAL,
    ACTION_PAUSE,
    ACTION_PRE_SUBSELECTION,
    ACTION_REMOVE_FROM_QUEUE,
    ACTION_RESUME,
    ACTION_SAVE_FINISHED,
    ACTION_SAVE_GAME,
    ACTION_SCENARIO_TRIGGER,
    ACTION_SELECT_GROUND_ITEM,
    ACTION_SELECT_GROUP,
    ACTION_SELECT_SUBGROUP,
    ACTION_SET_SPEED,
    ACTION_TRANSFER_RESOURCES,
    ACTION_TRIGGER_COMMAND,
    ACTION_UNKNOWN_1B,
    ACTION_UNKNOWN_75,
)
from w3g_parser.models import GameAction

logger = logging.getLogger(__name__)

# Action names for human-readable output
ACTION_NAMES: dict[int, str] = {
    ACTION_PAUSE: "pause",
    ACTION_RESUME: "resume",
    ACTION_SET_SPEED: "set_speed",
    ACTION_INC_SPEED: "increase_speed",
    ACTION_DEC_SPEED: "decrease_speed",
    ACTION_SAVE_GAME: "save_game",
    ACTION_SAVE_FINISHED: "save_finished",
    ACTION_ABILITY_NO_PARAMS: "ability",
    ACTION_ABILITY_TARGET_POS: "ability_position",
    ACTION_ABILITY_POS_OBJECT: "ability_object",
    ACTION_ABILITY_DROP_ITEM: "drop_item",
    ACTION_ABILITY_TWO_POS: "ability_two_positions",
    ACTION_CHANGE_SELECTION: "select_units",
    ACTION_ASSIGN_GROUP: "assign_group",
    ACTION_SELECT_GROUP: "select_group",
    ACTION_SELECT_SUBGROUP: "select_subgroup",
    ACTION_PRE_SUBSELECTION: "pre_subselection",
    ACTION_UNKNOWN_1B: "unknown_1b",
    ACTION_SELECT_GROUND_ITEM: "select_item",
    ACTION_CANCEL_HERO_REVIVAL: "cancel_revival",
    ACTION_REMOVE_FROM_QUEUE: "remove_from_queue",
    ACTION_ALLY_OPTIONS: "ally_options",
    ACTION_TRANSFER_RESOURCES: "transfer_resources",
    ACTION_TRIGGER_COMMAND: "trigger_command",
    ACTION_ESC_PRESSED: "escape",
    ACTION_SCENARIO_TRIGGER: "scenario_trigger",
    ACTION_HERO_SKILL_MENU: "hero_skill_menu",
    ACTION_BUILDING_MENU: "building_menu",
    ACTION_MINIMAP_SIGNAL: "minimap_ping",
    ACTION_CONTINUE_GAME_B: "continue_game_b",
    ACTION_CONTINUE_GAME_A: "continue_game_a",
    ACTION_UNKNOWN_75: "unknown_75",
}

# Cheat action IDs (single player only)
CHEAT_ACTIONS = set(range(0x20, 0x33))


def parse_action(
    data: bytes, offset: int, version: int
) -> tuple[GameAction | None, int]:
    """Parse a single action from action block data.

    Args:
        data: Action block data
        offset: Starting offset
        version: Game version for format differences

    Returns:
        Tuple of (GameAction or None, new offset)
    """
    if offset >= len(data):
        return None, offset

    action_id = data[offset]
    start_offset = offset
    offset += 1

    action_name = ACTION_NAMES.get(action_id, f"unknown_{action_id:02x}")
    action_data: dict = {}

    try:
        if action_id == ACTION_PAUSE:
            pass  # 1 byte total

        elif action_id == ACTION_RESUME:
            pass  # 1 byte total

        elif action_id == ACTION_SET_SPEED:
            if offset < len(data):
                action_data["speed"] = data[offset]
                offset += 1

        elif action_id in (ACTION_INC_SPEED, ACTION_DEC_SPEED):
            pass  # 1 byte total

        elif action_id == ACTION_SAVE_GAME:
            # Variable: null-terminated filename
            name_start = offset
            while offset < len(data) and data[offset] != 0:
                offset += 1
            action_data["filename"] = data[name_start:offset].decode("utf-8", errors="replace")
            offset += 1  # Skip null

        elif action_id == ACTION_SAVE_FINISHED:
            offset += 4  # Unknown dword

        elif action_id == ACTION_ABILITY_NO_PARAMS:
            # AbilityFlags (1 word for v1.13+, 1 byte for older)
            # ItemID (4 bytes)
            # Unknown data
            if version >= 13:
                action_size = 14  # 1 (id) + 2 (flags) + 4 (item) + 8 (unknowns)
            else:
                action_size = 13
            if offset + action_size - 1 <= len(data):
                flags_size = 2 if version >= 13 else 1
                action_data["ability_flags"] = int.from_bytes(
                    data[offset : offset + flags_size], "little"
                )
                offset += flags_size
                action_data["item_id"] = data[offset : offset + 4]
                offset += action_size - 1 - flags_size

        elif action_id == ACTION_ABILITY_TARGET_POS:
            if version >= 13:
                action_size = 21
            else:
                action_size = 20
            if offset + action_size - 1 <= len(data):
                flags_size = 2 if version >= 13 else 1
                action_data["ability_flags"] = int.from_bytes(
                    data[offset : offset + flags_size], "little"
                )
                offset += flags_size
                action_data["item_id"] = data[offset : offset + 4]
                offset += 4
                # Skip unknowns and read coordinates
                offset += 4  # unknowns
                if offset + 8 <= len(data):
                    x, y = struct.unpack_from("<ff", data, offset)
                    action_data["target_x"] = x
                    action_data["target_y"] = y
                offset += 8

        elif action_id == ACTION_ABILITY_POS_OBJECT:
            if version >= 13:
                action_size = 29
            else:
                action_size = 28
            if offset + action_size - 1 <= len(data):
                flags_size = 2 if version >= 13 else 1
                action_data["ability_flags"] = int.from_bytes(
                    data[offset : offset + flags_size], "little"
                )
                offset += flags_size
                action_data["item_id"] = data[offset : offset + 4]
                offset += 4
                offset += 4  # unknowns
                if offset + 8 <= len(data):
                    x, y = struct.unpack_from("<ff", data, offset)
                    action_data["target_x"] = x
                    action_data["target_y"] = y
                offset += 8
                # Object IDs
                action_data["object_id_1"] = data[offset : offset + 4]
                offset += 4
                action_data["object_id_2"] = data[offset : offset + 4]
                offset += 4

        elif action_id == ACTION_ABILITY_DROP_ITEM:
            if version >= 13:
                action_size = 37
            else:
                action_size = 36
            offset += action_size - 1

        elif action_id == ACTION_ABILITY_TWO_POS:
            if version >= 13:
                action_size = 42
            else:
                action_size = 41
            offset += action_size - 1

        elif action_id == ACTION_CHANGE_SELECTION:
            # 1 byte: select mode (1=add, 2=remove)
            # 1 word: unit count
            # n * 8 bytes: object IDs
            if offset + 3 <= len(data):
                action_data["select_mode"] = data[offset]
                offset += 1
                unit_count = struct.unpack_from("<H", data, offset)[0]
                offset += 2
                action_data["unit_count"] = unit_count
                offset += unit_count * 8

        elif action_id == ACTION_ASSIGN_GROUP:
            # 1 byte: group number
            # 1 word: unit count
            # n * 8 bytes: object IDs
            if offset + 3 <= len(data):
                action_data["group"] = data[offset]
                offset += 1
                unit_count = struct.unpack_from("<H", data, offset)[0]
                offset += 2
                action_data["unit_count"] = unit_count
                offset += unit_count * 8

        elif action_id == ACTION_SELECT_GROUP:
            # 1 byte: group number
            # 1 byte: unknown
            if offset + 2 <= len(data):
                action_data["group"] = data[offset]
                offset += 2

        elif action_id == ACTION_SELECT_SUBGROUP:
            # Variable based on version
            if version >= 14:  # 1.14b+
                # ItemID (4) + ObjectID1 (4) + ObjectID2 (4)
                offset += 12
            else:
                # Just subgroup number (1 byte)
                offset += 1

        elif action_id == ACTION_PRE_SUBSELECTION:
            pass  # 1 byte total

        elif action_id == ACTION_UNKNOWN_1B:
            offset += 9

        elif action_id == ACTION_SELECT_GROUND_ITEM:
            # 1 byte: flags
            # 8 bytes: 2x ObjectID
            offset += 9

        elif action_id == ACTION_CANCEL_HERO_REVIVAL:
            # 8 bytes: 2x UnitID
            offset += 8

        elif action_id == ACTION_REMOVE_FROM_QUEUE:
            # 1 byte: slot number
            # 4 bytes: ItemID
            if offset + 5 <= len(data):
                action_data["slot"] = data[offset]
                offset += 1
                action_data["item_id"] = data[offset : offset + 4]
                offset += 4

        elif action_id == ACTION_ALLY_OPTIONS:
            # 1 byte: player slot
            # 4 bytes: flags
            if offset + 5 <= len(data):
                action_data["player_slot"] = data[offset]
                offset += 1
                action_data["flags"] = struct.unpack_from("<I", data, offset)[0]
                offset += 4

        elif action_id == ACTION_TRANSFER_RESOURCES:
            # 1 byte: player slot
            # 4 bytes: gold
            # 4 bytes: lumber
            if offset + 9 <= len(data):
                action_data["player_slot"] = data[offset]
                offset += 1
                action_data["gold"] = struct.unpack_from("<I", data, offset)[0]
                offset += 4
                action_data["lumber"] = struct.unpack_from("<I", data, offset)[0]
                offset += 4

        elif action_id == ACTION_TRIGGER_COMMAND:
            # Skip 8 bytes of unknowns, then null-terminated string
            offset += 8
            str_start = offset
            while offset < len(data) and data[offset] != 0:
                offset += 1
            action_data["command"] = data[str_start:offset].decode("utf-8", errors="replace")
            offset += 1

        elif action_id == ACTION_ESC_PRESSED:
            pass  # 1 byte total

        elif action_id == ACTION_SCENARIO_TRIGGER:
            offset += 12

        elif action_id in (ACTION_HERO_SKILL_MENU, ACTION_BUILDING_MENU):
            pass  # 1 byte total

        elif action_id == ACTION_MINIMAP_SIGNAL:
            if offset + 12 <= len(data):
                x, y = struct.unpack_from("<ff", data, offset)
                action_data["x"] = x
                action_data["y"] = y
                offset += 12

        elif action_id in (ACTION_CONTINUE_GAME_B, ACTION_CONTINUE_GAME_A):
            offset += 16

        elif action_id == ACTION_UNKNOWN_75:
            offset += 1

        elif action_id in CHEAT_ACTIONS:
            # Skip cheat actions (single player)
            # Most are 1 byte, some are up to 6
            action_name = "cheat"
            # Simple heuristic: skip a few bytes
            offset += min(5, len(data) - offset)

        else:
            # Unknown action - try to skip safely
            # This is risky as we don't know the size
            logger.debug(f"Unknown action 0x{action_id:02X} at offset {start_offset}")
            return None, offset

    except Exception as e:
        logger.debug(f"Error parsing action 0x{action_id:02X}: {e}")
        return None, offset

    payload = data[start_offset:offset]

    return GameAction(
        timestamp_ms=0,  # Set by caller
        player_id=0,  # Set by caller
        action_type=action_id,
        action_name=action_name,
        payload=payload,
        data=action_data,
    ), offset


def parse_command_data(
    data: bytes, offset: int, length: int, version: int
) -> Iterator[tuple[int, GameAction]]:
    """Parse CommandData block containing player actions.

    CommandData structure:
    - 1 byte: Player ID
    - 1 word: Action block length
    - n bytes: Action blocks

    Args:
        data: TimeSlot data
        offset: Starting offset
        length: Total length of command data
        version: Game version

    Yields:
        Tuples of (player_id, GameAction)
    """
    end = offset + length

    while offset < end:
        if offset + 3 > len(data):
            break

        player_id = data[offset]
        offset += 1

        action_length = struct.unpack_from("<H", data, offset)[0]
        offset += 2

        action_end = offset + action_length

        while offset < action_end:
            action, offset = parse_action(data, offset, version)
            if action:
                action.player_id = player_id
                yield player_id, action
            else:
                # Skip remaining bytes if we can't parse
                break

        # Ensure we don't go past the action block
        offset = action_end
