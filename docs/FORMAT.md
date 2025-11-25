# W3G Binary Format Specification

This document describes the W3G replay format as reverse-engineered from existing parsers and replay analysis.

## Sources

- [scopatz/w3g](https://github.com/scopatz/w3g) - Python parser with format documentation
- [PBug90/w3gjs](https://github.com/PBug90/w3gjs) - TypeScript/JavaScript parser
- [aesteve/w3rs](https://github.com/aesteve/w3rs) - Rust parser for Reforged
- [w3g_format.txt](http://w3g.deepnode.de/files/w3g_format.txt) - Original format documentation
- [w3g_actions.txt](https://www.gamedevs.org/uploads/w3g_actions.txt) - Action format documentation

## File Structure Overview

```
+------------------+
|     Header       |  48-68 bytes
+------------------+
| Compressed Block |  Variable
+------------------+
| Compressed Block |  Variable
+------------------+
|      ...         |
+------------------+
```

## Header Structure

### Base Header (0x00 - 0x2F, 48 bytes)

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x00 | 28 bytes | string | Magic: "Warcraft III recorded game\x1A\x00" |
| 0x1C | 4 bytes | u32 | First data block offset (0x40 or 0x44) |
| 0x20 | 4 bytes | u32 | Total compressed file size |
| 0x24 | 4 bytes | u32 | Header version (0 or 1) |
| 0x28 | 4 bytes | u32 | Decompressed data size |
| 0x2C | 4 bytes | u32 | Number of compressed blocks |

### SubHeader Version 0 (Classic, patches ≤1.06)

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x30 | 2 bytes | u16 | Unknown (always 0) |
| 0x32 | 2 bytes | u16 | Patch version (e.g., 0x0106 for 1.06) |
| 0x34 | 2 bytes | u16 | Build number |
| 0x36 | 2 bytes | u16 | Flags (0x0000=SP, 0x8000=MP) |
| 0x38 | 4 bytes | u32 | Duration in milliseconds |
| 0x3C | 4 bytes | u32 | CRC32 checksum |

**Total header size: 0x40 (64 bytes)**

### SubHeader Version 1 (Expansion, patches ≥1.07)

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x30 | 4 bytes | string | Game ID: 'WAR3' (RoC), 'W3XP' (TFT), 'PX3W' (Reforged) |
| 0x34 | 4 bytes | u32 | Version number |
| 0x38 | 2 bytes | u16 | Build number |
| 0x3A | 2 bytes | u16 | Flags (0x0000=SP, 0x8000=MP) |
| 0x3C | 4 bytes | u32 | Duration in milliseconds |
| 0x40 | 4 bytes | u32 | CRC32 checksum |

**Total header size: 0x44 (68 bytes)**

## Compressed Data Blocks

### Classic Block Format (8-byte header)

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x00 | 2 bytes | u16 | Compressed data size |
| 0x02 | 2 bytes | u16 | Decompressed size (typically 8192) |
| 0x04 | 4 bytes | u32 | Checksum (unknown algorithm) |
| 0x08 | n bytes | - | Raw deflate compressed data |

### Reforged Block Format (12-byte header)

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x00 | 2 bytes | u16 | Compressed data size |
| 0x02 | 2 bytes | u16 | Unknown (always 0) |
| 0x04 | 4 bytes | u32 | Decompressed size (typically 8192) |
| 0x08 | 4 bytes | u32 | Checksum |
| 0x0C | n bytes | - | Zlib compressed data (with header) |

**Key difference:** Reforged uses zlib with headers (0x78 prefix), Classic uses raw deflate.

## Decompressed Data Structure

After decompressing all blocks and concatenating, the data contains:

1. **Unknown (4 bytes)**: Usually 0x00000110
2. **Host Player Record**
3. **Game Name** (null-terminated string)
4. **Null byte**
5. **Encoded String** (game settings, map info)
6. **Player Count** (4 bytes)
7. **Game Type** (4 bytes)
8. **Language ID** (4 bytes)
9. **Additional Player Records**
10. **Game Start Record** (0x19)
11. **Replay Data Blocks**

## Player Record

| Size | Type | Description |
|------|------|-------------|
| 1 byte | u8 | Record ID: 0x00 (host), 0x16 (additional) |
| 1 byte | u8 | Player ID |
| n bytes | string | Player name (null-terminated) |
| 1 byte | u8 | Extra data size: 0x01 (custom), 0x08 (ladder) |
| 1-8 bytes | - | Extra data |

**Ladder extra data (8 bytes):**
- 4 bytes: Runtime in milliseconds
- 4 bytes: Race flags

## Encoded String Format

The encoded string uses a control-byte scheme:
- Every even byte value is incremented by 1 (all encoded bytes are odd)
- Control byte precedes every 7-byte block
- Bits 1-7 of control byte indicate if corresponding byte is encoded (0) or literal (1)

Decoding algorithm:
```
for each control byte:
    for bit in 1..7:
        if (control & (1 << bit)) == 0:
            decoded = encoded_byte - 1
        else:
            decoded = encoded_byte
```

## Game Settings (from Encoded String)

| Offset | Bits | Field |
|--------|------|-------|
| 0x00 | 0-1 | Speed: 0=slow, 1=normal, 2=fast |
| 0x01 | 0-3 | Visibility |
| 0x01 | 4-5 | Observer mode |
| 0x01 | 6 | Teams together |
| 0x02 | 1-2 | Fixed teams |
| 0x03 | 0 | Full shared unit control |
| 0x03 | 1 | Random hero |
| 0x03 | 2 | Random races |
| 0x03 | 6 | Referees |
| 0x09-0x0C | - | Map checksum (4 bytes) |

## Game Start Record (0x19)

| Size | Type | Description |
|------|------|-------------|
| 1 byte | u8 | Record ID (0x19) |
| 2 bytes | u16 | Data byte count |
| 1 byte | u8 | Number of slot records |
| n bytes | - | Slot records |
| 4 bytes | u32 | Random seed |
| 1 byte | u8 | Select mode |
| 1 byte | u8 | Start spot count |

## Slot Record

| Offset | Size | Description |
|--------|------|-------------|
| 0x00 | 1 byte | Player ID (0x00 for AI) |
| 0x01 | 1 byte | Download % (0x64 custom, 0xFF ladder) |
| 0x02 | 1 byte | Slot status: 0=empty, 1=closed, 2=used |
| 0x03 | 1 byte | Computer flag: 0=human, 1=AI |
| 0x04 | 1 byte | Team number (12/24 = observer) |
| 0x05 | 1 byte | Color index |
| 0x06 | 1 byte | Race flags |
| 0x07 | 1 byte | AI strength (v1.03+) |
| 0x08 | 1 byte | Handicap % (v1.07+) |

**Race flags:**
- 0x01: Human
- 0x02: Orc
- 0x04: Night Elf
- 0x08: Undead
- 0x20: Random
- 0x40: Selectable/Fixed

## Replay Data Blocks

### Block 0x17 - LeaveGame (14 bytes)

| Size | Description |
|------|-------------|
| 4 bytes | Reason: 0x01=remote, 0x0C=local |
| 1 byte | Player ID |
| 4 bytes | Result: 0x01/0x07=left, 0x08=lost, 0x09=won, 0x0A=draw |
| 4 bytes | Unknown |

### Block 0x1A, 0x1B, 0x1C - Start Blocks (5 bytes)

| Size | Description |
|------|-------------|
| 4 bytes | Unknown (always 0x01) |

### Block 0x1E/0x1F - TimeSlot

| Size | Description |
|------|-------------|
| 2 bytes | Byte count (n) |
| 2 bytes | Time increment (milliseconds) |
| n-2 bytes | Command data |

**Command Data:**
| Size | Description |
|------|-------------|
| 1 byte | Player ID |
| 2 bytes | Action block length |
| n bytes | Action blocks |

### Block 0x20 - Chat Message (v1.07+)

| Size | Description |
|------|-------------|
| 1 byte | Sender ID |
| 2 bytes | Message length |
| 1 byte | Flags: 0x10=startup, 0x20=normal |
| 4 bytes | Chat mode (if flag=0x20) |
| n bytes | Message (null-terminated) |

**Chat modes:** 0=all, 1=allies, 2=observers, 3+=specific player

### Block 0x22 - Checksum (5 bytes)

| Size | Description |
|------|-------------|
| 1 byte | Length (0x04) |
| 4 bytes | Random value |

### Block 0x2F - Forced Game End (9 bytes)

| Size | Description |
|------|-------------|
| 4 bytes | Mode: 0=running, 1=over |
| 4 bytes | Countdown (seconds) |

## Action Types

| ID | Name | Size |
|----|------|------|
| 0x01 | Pause | 1 |
| 0x02 | Resume | 1 |
| 0x03 | Set Speed | 2 |
| 0x10 | Ability (no params) | 14-15 |
| 0x11 | Ability (target pos) | 21-22 |
| 0x12 | Ability (pos + object) | 29-30 |
| 0x13 | Give/Drop Item | 37-38 |
| 0x14 | Ability (2 pos) | 42-43 |
| 0x16 | Change Selection | 4+n*8 |
| 0x17 | Assign Group | 4+n*8 |
| 0x18 | Select Group | 3 |
| 0x19 | Select Subgroup | varies |
| 0x1A | Pre-Subselection | 1 |
| 0x1D | Cancel Hero Revival | 9 |
| 0x1E | Remove from Queue | 6 |
| 0x50 | Ally Options | 6 |
| 0x51 | Transfer Resources | 10 |
| 0x60 | Trigger Command | variable |
| 0x61 | ESC Pressed | 1 |
| 0x66 | Hero Skill Menu | 1 |
| 0x67 | Building Menu | 1 |
| 0x68 | Minimap Signal | 13 |

**Note:** Action sizes vary by version. v1.13+ uses 2-byte AbilityFlags instead of 1-byte.

## Version Differences

### Observer Team IDs
- Classic (v < 29): Team 12 = Observer
- Reforged (v ≥ 29): Team 24 = Observer

### Block Compression
- Classic: Raw deflate (wbits=-15)
- Reforged: Zlib with header (wbits=15)

### Block Header Size
- Classic: 8 bytes
- Reforged: 12 bytes

### Game Identifier
- Classic: 'WAR3' (RoC) or 'W3XP' (TFT)
- Reforged: 'PX3W' (little-endian 'W3XP')

## Unknown/Undocumented

- Block 0x23: Unknown structure, appears in some replays
- Action 0x1B: Selection sync/verification (10 bytes), doesn't count for APM
  - Structure: 1 byte flag (0x01) + 4 bytes ObjectID1 + 4 bytes ObjectID2
  - Appears frequently in Reforged replays, possibly trigger-related
- Action 0x75: Unknown, 2 bytes
- Various checksum algorithms are not documented
