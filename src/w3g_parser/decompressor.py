"""Block decompression for W3G replay files."""

import struct
import zlib
from typing import BinaryIO

from w3g_parser.exceptions import DecompressionError, TruncatedDataError
from w3g_parser.models import ReplayHeader


def decompress_blocks(stream: BinaryIO, header: ReplayHeader) -> bytes:
    """Decompress all data blocks from stream.

    Block format varies by version:

    Classic (pre-Reforged) - 8 byte header:
    - Offset 0x00: Compressed size (1 word)
    - Offset 0x02: Decompressed size (1 word)
    - Offset 0x04: Checksum/unknown (1 dword)
    - Offset 0x08: Compressed data (compressed_size bytes, raw deflate)

    Reforged - 12 byte header:
    - Offset 0x00: Compressed size (1 word) - doesn't include header
    - Offset 0x02: Unknown (1 word)
    - Offset 0x04: Decompressed size (1 dword)
    - Offset 0x08: Checksum (1 dword)
    - Offset 0x0C: Compressed data (zlib format with header)

    Args:
        stream: Binary stream positioned after header
        header: Parsed replay header

    Returns:
        Concatenated decompressed data

    Raises:
        DecompressionError: If decompression fails
        TruncatedDataError: If not enough data
    """
    decompressed_parts: list[bytes] = []

    # Determine if this is Reforged format
    # Reforged uses 12-byte block headers and zlib with headers
    is_reforged = header.is_reforged

    for block_num in range(header.num_compressed_blocks):
        if is_reforged:
            # Reforged: 12-byte header
            block_header = stream.read(12)
            if len(block_header) < 12:
                raise TruncatedDataError(
                    f"Block {block_num} header truncated",
                    stream.tell()
                )

            # Parse Reforged header
            # compressed_size is the size of zlib data only
            compressed_size = struct.unpack_from("<H", block_header, 0)[0]
            decompressed_size = struct.unpack_from("<I", block_header, 4)[0]

            # Read compressed data
            compressed_data = stream.read(compressed_size)
            if len(compressed_data) < compressed_size:
                raise TruncatedDataError(
                    f"Block {block_num} data truncated: expected {compressed_size}, "
                    f"got {len(compressed_data)}",
                    stream.tell()
                )

            # Decompress using zlib (with header)
            try:
                decompressor = zlib.decompressobj()
                decompressed = decompressor.decompress(compressed_data)
                decompressed += decompressor.flush()
            except zlib.error as e:
                raise DecompressionError(
                    f"Block {block_num} decompression failed: {e}",
                    stream.tell() - compressed_size
                ) from e

        else:
            # Classic: 8-byte header
            block_header = stream.read(8)
            if len(block_header) < 8:
                raise TruncatedDataError(
                    f"Block {block_num} header truncated",
                    stream.tell()
                )

            compressed_size, decompressed_size, _ = struct.unpack("<HHI", block_header)

            # Read compressed data
            compressed_data = stream.read(compressed_size)
            if len(compressed_data) < compressed_size:
                raise TruncatedDataError(
                    f"Block {block_num} data truncated: expected {compressed_size}, "
                    f"got {len(compressed_data)}",
                    stream.tell()
                )

            # Decompress using raw deflate (no header)
            try:
                decompressor = zlib.decompressobj(wbits=-15)
                decompressed = decompressor.decompress(compressed_data)
                decompressed += decompressor.flush()
            except zlib.error:
                # Fall back to zlib with header
                try:
                    decompressor = zlib.decompressobj()
                    decompressed = decompressor.decompress(compressed_data)
                    decompressed += decompressor.flush()
                except zlib.error as e:
                    raise DecompressionError(
                        f"Block {block_num} decompression failed: {e}",
                        stream.tell() - compressed_size
                    ) from e

        decompressed_parts.append(decompressed)

    return b"".join(decompressed_parts)


def decompress_single_block(data: bytes, use_zlib_header: bool = False) -> bytes:
    """Decompress a single block of data.

    Args:
        data: Raw block data (without header)
        use_zlib_header: If True, use zlib format; otherwise raw deflate

    Returns:
        Decompressed data
    """
    if use_zlib_header:
        decompressor = zlib.decompressobj()
    else:
        decompressor = zlib.decompressobj(wbits=-15)

    try:
        result = decompressor.decompress(data)
        result += decompressor.flush()
        return result
    except zlib.error:
        # Try the other format
        if use_zlib_header:
            decompressor = zlib.decompressobj(wbits=-15)
        else:
            decompressor = zlib.decompressobj()
        result = decompressor.decompress(data)
        result += decompressor.flush()
        return result
