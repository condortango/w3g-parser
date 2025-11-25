"""Action parsing for W3G replay files."""

import struct
import logging
from typing import Iterator

logger = logging.getLogger(__name__)


# Common ability/item ID mappings (4-char codes reversed)
ITEM_ID_NAMES: dict[str, str] = {
    # Move/Attack commands (numeric IDs)
    "ability_3": "Right-click / Smart",
    "ability_6": "Move",
    "ability_7": "Attack",
    "ability_12": "Hold Position",
    "ability_13": "Patrol",
    "ability_19": "Stop",

    # Hero abilities (numeric IDs)
    "ability_89": "Rally Point",
    "ability_121": "Blink",
    "ability_122": "Fan of Knives",
    "ability_123": "Mana Burn",
    "ability_124": "Immolation",
    "ability_125": "Metamorphosis",
    "ability_126": "Evasion",
    "ability_127": "Shadow Strike",
    "ability_128": "Vengeance",
    "ability_129": "Spirit of Vengeance",

    # Human buildings
    "halt": "Altar of Kings",
    "hbar": "Barracks",
    "hbla": "Blacksmith",
    "hhou": "Farm",
    "hgra": "Gryphon Aviary",
    "hars": "Arcane Sanctum",
    "hlum": "Lumber Mill",
    "htow": "Town Hall",
    "hkee": "Keep",
    "hcas": "Castle",
    "harm": "Workshop",
    "hwtw": "Scout Tower",
    "hgtw": "Guard Tower",
    "hctw": "Cannon Tower",
    "hatw": "Arcane Tower",

    # Human units
    "hpea": "Peasant",
    "hfoo": "Footman",
    "hrif": "Rifleman",
    "hkni": "Knight",
    "hmpr": "Priest",
    "hsor": "Sorceress",
    "hspt": "Spell Breaker",
    "hmtm": "Mortar Team",
    "hgyr": "Flying Machine",
    "hgry": "Gryphon Rider",
    "hmtt": "Siege Engine",

    # Human heroes
    "Hamg": "Archmage",
    "Hblm": "Blood Mage",
    "Hmkg": "Mountain King",
    "Hpal": "Paladin",

    # Orc buildings
    "oalt": "Altar of Storms",
    "obar": "Barracks",
    "ofor": "War Mill",
    "ogre": "Great Hall",
    "ostr": "Stronghold",
    "ofrt": "Fortress",
    "obea": "Beastiary",
    "osld": "Spirit Lodge",
    "otrb": "Orc Burrow",
    "ovln": "Voodoo Lounge",
    "otau": "Tauren Totem",
    "owtw": "Watch Tower",

    # Orc units
    "opeo": "Peon",
    "ogru": "Grunt",
    "ohun": "Headhunter",
    "orai": "Raider",
    "okod": "Kodo Beast",
    "oshm": "Shaman",
    "odoc": "Witch Doctor",
    "ospw": "Spirit Walker",
    "otau": "Tauren",
    "owyv": "Wind Rider",
    "otbr": "Troll Batrider",

    # Orc heroes
    "Obla": "Blademaster",
    "Ofar": "Far Seer",
    "Otch": "Tauren Chieftain",
    "Oshd": "Shadow Hunter",

    # Night Elf buildings
    "eate": "Altar of Elders",
    "eaom": "Ancient of War",
    "eaow": "Ancient of Wonders",
    "eaoe": "Ancient of Lore",
    "edob": "Hunter's Hall",
    "etol": "Tree of Life",
    "etoa": "Tree of Ages",
    "etoe": "Tree of Eternity",
    "emow": "Moon Well",
    "eden": "Ancient of Wind",
    "edos": "Chimaera Roost",

    # Night Elf units
    "ewsp": "Wisp",
    "earc": "Archer",
    "esen": "Huntress",
    "ebal": "Glaive Thrower",
    "edry": "Dryad",
    "edot": "Druid of the Talon",
    "edoc": "Druid of the Claw",
    "emtg": "Mountain Giant",
    "efdr": "Faerie Dragon",
    "ehip": "Hippogryph",
    "echm": "Chimaera",

    # Night Elf heroes
    "Edem": "Demon Hunter",
    "Ekee": "Keeper of the Grove",
    "Emoo": "Priestess of the Moon",
    "Ewar": "Warden",

    # Undead buildings
    "uaod": "Altar of Darkness",
    "unpl": "Necropolis",
    "unp1": "Halls of the Dead",
    "unp2": "Black Citadel",
    "usep": "Crypt",
    "ugrv": "Graveyard",
    "uzig": "Ziggurat",
    "uzg1": "Spirit Tower",
    "uzg2": "Nerubian Tower",
    "uslh": "Slaughterhouse",
    "utod": "Temple of the Damned",
    "usap": "Sacrificial Pit",
    "ubon": "Boneyard",
    "utom": "Tomb of Relics",

    # Undead units
    "uaco": "Acolyte",
    "ugho": "Ghoul",
    "ucry": "Crypt Fiend",
    "ugar": "Gargoyle",
    "uabo": "Abomination",
    "umtw": "Meat Wagon",
    "unec": "Necromancer",
    "uban": "Banshee",
    "uobs": "Obsidian Statue",
    "ubsp": "Destroyer",
    "ufro": "Frost Wyrm",
    "ushd": "Shade",

    # Undead heroes
    "Udea": "Death Knight",
    "Udre": "Dread Lord",
    "Ulic": "Lich",
    "Ucrl": "Crypt Lord",
}


def decode_item_id(item_bytes: bytes) -> str:
    """Decode a 4-byte item/ability ID to human-readable string.

    Item IDs come in two formats:
    1. String IDs: 4 ASCII chars in reverse order (e.g., b'tlah' -> 'halt')
    2. Numeric IDs: XX XX 0D 00 format for ability commands

    Args:
        item_bytes: 4-byte item ID

    Returns:
        Human-readable name or hex string
    """
    if len(item_bytes) != 4:
        return item_bytes.hex()

    # Check if numeric ID (XX XX 0D 00)
    if item_bytes[2:4] == b'\x0d\x00':
        ability_num = struct.unpack('<H', item_bytes[0:2])[0]
        key = f"ability_{ability_num}"
        return ITEM_ID_NAMES.get(key, key)

    # Try to decode as string ID
    try:
        s = item_bytes.decode('ascii')
        if all(c.isalnum() or c in '_\x00' for c in s):
            # Reverse the string (WC3 stores them backwards)
            code = s.rstrip('\x00')[::-1]
            return ITEM_ID_NAMES.get(code, code)
    except (UnicodeDecodeError, ValueError):
        pass

    return item_bytes.hex()

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
    ACTION_UNKNOWN_1B: "sync_selection",  # Selection verification/sync (doesn't count for APM)
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
            # Structure: flags(2) + item_id(4) + unknown(8) + x(4) + y(4) = 22 bytes
            if version >= 13:
                action_size = 22
            else:
                action_size = 21
            if offset + action_size - 1 <= len(data):
                flags_size = 2 if version >= 13 else 1
                action_data["ability_flags"] = int.from_bytes(
                    data[offset : offset + flags_size], "little"
                )
                offset += flags_size
                action_data["item_id"] = data[offset : offset + 4]
                offset += 4
                # Skip unknowns (8 bytes) and read coordinates
                offset += 8  # unknowns
                if offset + 8 <= len(data):
                    x, y = struct.unpack_from("<ff", data, offset)
                    action_data["target_x"] = x
                    action_data["target_y"] = y
                offset += 8

        elif action_id == ACTION_ABILITY_POS_OBJECT:
            # Structure: flags(2) + item_id(4) + unknown(8) + x(4) + y(4) + obj1(4) + obj2(4) = 30
            # But observed payloads are 27 bytes, so structure may vary
            if version >= 13:
                action_size = 26  # Adjusted based on actual payload
            else:
                action_size = 25
            if offset + action_size - 1 <= len(data):
                flags_size = 2 if version >= 13 else 1
                action_data["ability_flags"] = int.from_bytes(
                    data[offset : offset + flags_size], "little"
                )
                offset += flags_size
                action_data["item_id"] = data[offset : offset + 4]
                offset += 4
                offset += 8  # unknowns (8 bytes)
                if offset + 8 <= len(data):
                    x, y = struct.unpack_from("<ff", data, offset)
                    action_data["target_x"] = x
                    action_data["target_y"] = y
                offset += 8
                # Object IDs
                if offset + 4 <= len(data):
                    action_data["object_id_1"] = data[offset : offset + 4]
                    offset += 4
                if offset + 4 <= len(data):
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
            # n * 8 bytes: object IDs (2 dwords per unit)
            if offset + 3 <= len(data):
                action_data["select_mode"] = data[offset]
                offset += 1
                unit_count = struct.unpack_from("<H", data, offset)[0]
                offset += 2
                action_data["unit_count"] = unit_count
                # Parse object IDs
                object_ids = []
                for _ in range(unit_count):
                    if offset + 8 <= len(data):
                        obj_id = struct.unpack_from("<I", data, offset)[0]
                        object_ids.append(obj_id)
                        offset += 8  # Skip both dwords (obj_id1 and obj_id2)
                    else:
                        break
                action_data["object_ids"] = object_ids

        elif action_id == ACTION_ASSIGN_GROUP:
            # 1 byte: group number
            # 1 word: unit count
            # n * 8 bytes: object IDs (2 dwords per unit)
            if offset + 3 <= len(data):
                action_data["group"] = data[offset]
                offset += 1
                unit_count = struct.unpack_from("<H", data, offset)[0]
                offset += 2
                action_data["unit_count"] = unit_count
                # Parse object IDs
                object_ids = []
                for _ in range(unit_count):
                    if offset + 8 <= len(data):
                        obj_id = struct.unpack_from("<I", data, offset)[0]
                        object_ids.append(obj_id)
                        offset += 8
                    else:
                        break
                action_data["object_ids"] = object_ids

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
            # Sync/selection verification action (10 bytes total)
            # 1 byte: flag (always 0x01)
            # 4 bytes: ObjectID1
            # 4 bytes: ObjectID2 (usually same as ObjectID1)
            if offset + 9 <= len(data):
                action_data["flag"] = data[offset]
                offset += 1
                action_data["object_id_1"] = struct.unpack_from("<I", data, offset)[0]
                offset += 4
                action_data["object_id_2"] = struct.unpack_from("<I", data, offset)[0]
                offset += 4
            else:
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
