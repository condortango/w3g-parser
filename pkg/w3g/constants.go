// Package w3g provides a parser for Warcraft III replay (.w3g) files.
package w3g

// MagicString is the magic bytes identifying W3G replay files (28 bytes)
var MagicString = []byte("Warcraft III recorded game\x1a\x00")

// Header sizes
const (
	BaseHeaderSize  = 0x30 // 48 bytes for base header
	SubHeaderV0Size = 0x10 // 16 bytes
	SubHeaderV1Size = 0x14 // 20 bytes
	HeaderV0Total   = 0x40 // 64 bytes
	HeaderV1Total   = 0x44 // 68 bytes
)

// Game identifiers (little-endian representation)
const (
	GameIDClassic  = "WAR3" // Reign of Chaos / Classic
	GameIDTFT      = "W3XP" // The Frozen Throne
	GameIDReforged = "PX3W" // Alternative Reforged identifier
)

// Flags
const (
	FlagSinglePlayer = 0x0000
	FlagMultiplayer  = 0x8000
)

// Observer team IDs
const (
	ObserverTeamClassic  = 12
	ObserverTeamReforged = 24
)

// Version threshold for Reforged
const ReforgedVersionThreshold = 29

// Block IDs
const (
	BlockLeaveGame   = 0x17
	BlockGameStart   = 0x19
	BlockFirstStart  = 0x1A
	BlockSecondStart = 0x1B
	BlockThirdStart  = 0x1C
	BlockTimeSlotOld = 0x1E
	BlockTimeSlot    = 0x1F
	BlockChat        = 0x20
	BlockChecksum    = 0x22
	BlockForcedEnd   = 0x2F
)

// Record IDs
const (
	RecordHost             = 0x00
	RecordAdditionalPlayer = 0x16
)

// Action IDs
const (
	ActionPause             = 0x01
	ActionResume            = 0x02
	ActionSetSpeed          = 0x03
	ActionIncSpeed          = 0x04
	ActionDecSpeed          = 0x05
	ActionSaveGame          = 0x06
	ActionSaveFinished      = 0x07
	ActionAbilityNoParams   = 0x10
	ActionAbilityTargetPos  = 0x11
	ActionAbilityPosObject  = 0x12
	ActionAbilityDropItem   = 0x13
	ActionAbilityTwoPos     = 0x14
	ActionChangeSelection   = 0x16
	ActionAssignGroup       = 0x17
	ActionSelectGroup       = 0x18
	ActionSelectSubgroup    = 0x19
	ActionPreSubselection   = 0x1A
	ActionSyncSelection     = 0x1B
	ActionSelectGroundItem  = 0x1C
	ActionCancelHeroRevival = 0x1D
	ActionRemoveFromQueue   = 0x1E
	ActionAllyOptions       = 0x50
	ActionTransferResources = 0x51
	ActionTriggerCommand    = 0x60
	ActionEscPressed        = 0x61
	ActionScenarioTrigger   = 0x62
	ActionHeroSkillMenu     = 0x66
	ActionBuildingMenu      = 0x67
	ActionMinimapSignal     = 0x68
	ActionContinueGameB     = 0x69
	ActionContinueGameA     = 0x6A
	ActionUnknown75         = 0x75
)

// Chat flags
const (
	ChatFlagStartup = 0x10
	ChatFlagNormal  = 0x20
)

// Chat modes
const (
	ChatModeAll       = 0x00
	ChatModeAllies    = 0x01
	ChatModeObservers = 0x02
)

// ActionNames maps action IDs to human-readable names
var ActionNames = map[uint8]string{
	ActionPause:             "pause",
	ActionResume:            "resume",
	ActionSetSpeed:          "set_speed",
	ActionIncSpeed:          "increase_speed",
	ActionDecSpeed:          "decrease_speed",
	ActionSaveGame:          "save_game",
	ActionSaveFinished:      "save_finished",
	ActionAbilityNoParams:   "ability",
	ActionAbilityTargetPos:  "ability_position",
	ActionAbilityPosObject:  "ability_object",
	ActionAbilityDropItem:   "drop_item",
	ActionAbilityTwoPos:     "ability_two_positions",
	ActionChangeSelection:   "select_units",
	ActionAssignGroup:       "assign_group",
	ActionSelectGroup:       "select_group",
	ActionSelectSubgroup:    "select_subgroup",
	ActionPreSubselection:   "pre_subselection",
	ActionSyncSelection:     "sync_selection",
	ActionSelectGroundItem:  "select_item",
	ActionCancelHeroRevival: "cancel_revival",
	ActionRemoveFromQueue:   "remove_from_queue",
	ActionAllyOptions:       "ally_options",
	ActionTransferResources: "transfer_resources",
	ActionTriggerCommand:    "trigger_command",
	ActionEscPressed:        "escape",
	ActionScenarioTrigger:   "scenario_trigger",
	ActionHeroSkillMenu:     "hero_skill_menu",
	ActionBuildingMenu:      "building_menu",
	ActionMinimapSignal:     "minimap_ping",
	ActionContinueGameB:     "continue_game_b",
	ActionContinueGameA:     "continue_game_a",
	ActionUnknown75:         "unknown_75",
}

// ItemIDNames maps common ability/item IDs to human-readable names
var ItemIDNames = map[string]string{
	// Move/Attack commands (numeric IDs)
	"ability_3":  "Right-click / Smart",
	"ability_6":  "Move",
	"ability_7":  "Attack",
	"ability_12": "Hold Position",
	"ability_13": "Patrol",
	"ability_19": "Stop",
	"ability_89": "Rally Point",

	// Human buildings
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

	// Human units
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

	// Human heroes
	"Hamg": "Archmage",
	"Hblm": "Blood Mage",
	"Hmkg": "Mountain King",
	"Hpal": "Paladin",

	// Orc buildings
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

	// Orc units
	"opeo": "Peon",
	"ogru": "Grunt",
	"ohun": "Headhunter",
	"orai": "Raider",
	"okod": "Kodo Beast",
	"oshm": "Shaman",
	"odoc": "Witch Doctor",
	"ospw": "Spirit Walker",
	"owyv": "Wind Rider",
	"otbr": "Troll Batrider",

	// Orc heroes
	"Obla": "Blademaster",
	"Ofar": "Far Seer",
	"Otch": "Tauren Chieftain",
	"Oshd": "Shadow Hunter",

	// Night Elf buildings
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

	// Night Elf units
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

	// Night Elf heroes
	"Edem": "Demon Hunter",
	"Ekee": "Keeper of the Grove",
	"Emoo": "Priestess of the Moon",
	"Ewar": "Warden",

	// Undead buildings
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

	// Undead units
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

	// Undead heroes
	"Udea": "Death Knight",
	"Udre": "Dread Lord",
	"Ulic": "Lich",
	"Ucrl": "Crypt Lord",
}
