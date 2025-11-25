"""Header parsing for W3G replay files."""

import struct
from typing import BinaryIO

from w3g_parser.constants import (
    BASE_HEADER_SIZE,
    HEADER_V0_TOTAL,
    HEADER_V1_TOTAL,
    MAGIC_STRING,
    SUBHEADER_V0_SIZE,
    SUBHEADER_V1_SIZE,
)
from w3g_parser.exceptions import InvalidHeaderError, TruncatedDataError
from w3g_parser.models import ReplayHeader


def parse_header(stream: BinaryIO) -> ReplayHeader:
    """Parse the W3G file header from a stream.

    The header consists of:
    - Base header (0x30 bytes)
    - SubHeader (0x10 bytes for v0, 0x14 bytes for v1)

    Args:
        stream: Binary stream positioned at start of file

    Returns:
        Parsed ReplayHeader

    Raises:
        InvalidHeaderError: If header is invalid
        TruncatedDataError: If not enough data
    """
    # Read base header (48 bytes)
    base_header = stream.read(BASE_HEADER_SIZE)
    if len(base_header) < BASE_HEADER_SIZE:
        raise TruncatedDataError("File too small for header", len(base_header))

    # Validate magic string
    magic = base_header[:28]
    if magic != MAGIC_STRING:
        raise InvalidHeaderError(
            f"Invalid magic string: {magic!r}, expected {MAGIC_STRING!r}"
        )

    # Parse base header fields
    # Offset 0x1C: First data block offset (header size)
    # Offset 0x20: Compressed file size
    # Offset 0x24: Header version (0 or 1)
    # Offset 0x28: Decompressed data size
    # Offset 0x2C: Number of compressed blocks
    header_size, compressed_size, header_version, decompressed_size, num_blocks = struct.unpack(
        "<IIIII", base_header[0x1C:0x30]
    )

    # Determine subheader size based on version
    if header_version == 0:
        subheader_size = SUBHEADER_V0_SIZE
        expected_header_size = HEADER_V0_TOTAL
    elif header_version == 1:
        subheader_size = SUBHEADER_V1_SIZE
        expected_header_size = HEADER_V1_TOTAL
    else:
        raise InvalidHeaderError(f"Unknown header version: {header_version}")

    # Validate header size
    if header_size != expected_header_size:
        # Some replays may have slightly different header sizes
        # We'll use the reported size but warn-level log would go here
        pass

    # Read subheader
    subheader = stream.read(subheader_size)
    if len(subheader) < subheader_size:
        raise TruncatedDataError("File too small for subheader", BASE_HEADER_SIZE + len(subheader))

    # Parse subheader based on version
    if header_version == 0:
        # Version 0 (Classic, patches <= 1.06)
        # Offset 0x00: unknown (1 word, always 0)
        # Offset 0x02: version number (1 word)
        # Offset 0x04: build number (1 word)
        # Offset 0x06: flags (1 word)
        # Offset 0x08: duration (1 dword)
        # Offset 0x0C: CRC32 (1 dword)
        _, version, build_number, flags, duration_ms, crc32 = struct.unpack(
            "<HHHHI I", subheader
        )
        # Classic replays use 'WAR3' identifier
        game_identifier = "WAR3"
    else:
        # Version 1 (Expansion, patches >= 1.07)
        # Offset 0x00: game identifier (1 dword): 'WAR3' or 'W3XP'
        # Offset 0x04: version number (1 dword)
        # Offset 0x08: build number (1 word)
        # Offset 0x0A: flags (1 word)
        # Offset 0x0C: duration (1 dword)
        # Offset 0x10: CRC32 (1 dword)
        game_id_bytes, version, build_number, flags, duration_ms, crc32 = struct.unpack(
            "<4sIHHII", subheader
        )
        # Decode game identifier (stored as little-endian 4-char string)
        game_identifier = game_id_bytes.decode("ascii", errors="replace")

    return ReplayHeader(
        magic=magic,
        header_size=header_size,
        compressed_size=compressed_size,
        header_version=header_version,
        decompressed_size=decompressed_size,
        num_compressed_blocks=num_blocks,
        game_identifier=game_identifier,
        version=version,
        build_number=build_number,
        flags=flags,
        duration_ms=duration_ms,
        crc32=crc32,
        raw_header=base_header + subheader,
    )


def parse_header_from_bytes(data: bytes) -> ReplayHeader:
    """Parse header from bytes.

    Args:
        data: Raw header bytes

    Returns:
        Parsed ReplayHeader
    """
    import io

    return parse_header(io.BytesIO(data))
