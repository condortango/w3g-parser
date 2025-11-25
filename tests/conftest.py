"""Pytest fixtures for W3G parser tests."""

import pytest
from pathlib import Path


@pytest.fixture
def sample_replay_path():
    """Path to sample replay for testing."""
    path = Path(__file__).parent.parent / "replay.w3g"
    if not path.exists():
        pytest.skip("No sample replay available")
    return path


@pytest.fixture
def mock_classic_header():
    """Minimal valid classic header bytes (v0) for unit testing."""
    # Magic string (28 bytes)
    header = bytearray(b"Warcraft III recorded game\x1a\x00")

    # Header size (4 bytes) - 0x40 for v0
    header.extend(b"\x40\x00\x00\x00")

    # Compressed size (4 bytes)
    header.extend(b"\x00\x10\x00\x00")

    # Header version (4 bytes) - 0 for v0
    header.extend(b"\x00\x00\x00\x00")

    # Decompressed size (4 bytes)
    header.extend(b"\x00\x20\x00\x00")

    # Number of blocks (4 bytes)
    header.extend(b"\x01\x00\x00\x00")

    # SubHeader v0 (16 bytes)
    # Unknown (2 bytes)
    header.extend(b"\x00\x00")
    # Version (2 bytes) - 1.06
    header.extend(b"\x06\x01")
    # Build (2 bytes)
    header.extend(b"\x00\x10")
    # Flags (2 bytes) - multiplayer
    header.extend(b"\x00\x80")
    # Duration (4 bytes) - 300000ms = 5 minutes
    header.extend(b"\xa0\x93\x04\x00")
    # CRC32 (4 bytes)
    header.extend(b"\x00\x00\x00\x00")

    return bytes(header)


@pytest.fixture
def mock_expansion_header():
    """Minimal valid expansion header bytes (v1) for unit testing."""
    # Magic string (28 bytes)
    header = bytearray(b"Warcraft III recorded game\x1a\x00")

    # Header size (4 bytes) - 0x44 for v1
    header.extend(b"\x44\x00\x00\x00")

    # Compressed size (4 bytes)
    header.extend(b"\x00\x10\x00\x00")

    # Header version (4 bytes) - 1 for v1
    header.extend(b"\x01\x00\x00\x00")

    # Decompressed size (4 bytes)
    header.extend(b"\x00\x20\x00\x00")

    # Number of blocks (4 bytes)
    header.extend(b"\x01\x00\x00\x00")

    # SubHeader v1 (20 bytes)
    # Game ID (4 bytes) - 'W3XP' for TFT
    header.extend(b"W3XP")
    # Version (4 bytes) - version 26
    header.extend(b"\x1a\x00\x00\x00")
    # Build (2 bytes)
    header.extend(b"\x00\x10")
    # Flags (2 bytes) - multiplayer
    header.extend(b"\x00\x80")
    # Duration (4 bytes) - 600000ms = 10 minutes
    header.extend(b"\xc0\x27\x09\x00")
    # CRC32 (4 bytes)
    header.extend(b"\x00\x00\x00\x00")

    return bytes(header)
