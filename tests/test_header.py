"""Tests for header parsing."""

import io
import pytest

from w3g_parser.header import parse_header, parse_header_from_bytes
from w3g_parser.exceptions import InvalidHeaderError, TruncatedDataError


def test_parse_classic_header(mock_classic_header):
    """Test parsing a classic (v0) header."""
    header = parse_header_from_bytes(mock_classic_header)

    assert header.magic == b"Warcraft III recorded game\x1a\x00"
    assert header.header_size == 0x40
    assert header.header_version == 0
    assert header.game_identifier == "WAR3"
    assert header.version == 0x0106  # 1.06 in hex representation
    assert header.is_multiplayer is True


def test_parse_expansion_header(mock_expansion_header):
    """Test parsing an expansion (v1) header."""
    header = parse_header_from_bytes(mock_expansion_header)

    assert header.magic == b"Warcraft III recorded game\x1a\x00"
    assert header.header_size == 0x44
    assert header.header_version == 1
    assert header.game_identifier == "W3XP"
    assert header.version == 26
    assert header.is_expansion is True
    assert header.is_multiplayer is True
    assert header.duration_ms == 600000


def test_invalid_magic_string():
    """Test that invalid magic string raises error."""
    bad_header = b"Invalid header data" + b"\x00" * 100

    with pytest.raises(InvalidHeaderError, match="Invalid magic string"):
        parse_header_from_bytes(bad_header)


def test_truncated_header():
    """Test that truncated data raises error."""
    truncated = b"Warcraft III recorded game\x1a\x00"  # Only magic, no more data

    with pytest.raises(TruncatedDataError):
        parse_header_from_bytes(truncated)


def test_header_version_string(mock_expansion_header):
    """Test version string formatting."""
    header = parse_header_from_bytes(mock_expansion_header)

    # Version 26 should format as "1.26"
    assert header.version_string == "1.26"


def test_parse_real_replay(sample_replay_path):
    """Test parsing header from real replay file."""
    with open(sample_replay_path, "rb") as f:
        header = parse_header(f)

    # Basic sanity checks
    assert header.magic == b"Warcraft III recorded game\x1a\x00"
    assert header.header_size in (0x40, 0x44)
    assert header.header_version in (0, 1)
    assert header.num_compressed_blocks > 0
    assert header.duration_ms > 0
