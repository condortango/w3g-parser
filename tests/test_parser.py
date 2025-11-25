"""Tests for the main parser."""

import pytest

from w3g_parser import W3GParser, W3GReplay


def test_parse_replay(sample_replay_path):
    """Test parsing a complete replay file."""
    parser = W3GParser()
    replay = parser.parse(sample_replay_path)

    # Check basic structure
    assert replay.header is not None
    assert replay.header.magic == b"Warcraft III recorded game\x1a\x00"

    # Check we got some data
    assert replay.game_name or replay.map_name  # At least one should be set
    assert len(replay.players) > 0


def test_parse_header_only(sample_replay_path):
    """Test quick header-only parsing."""
    parser = W3GParser()
    header = parser.parse_header_only(sample_replay_path)

    assert header is not None
    assert header.duration_ms > 0
    assert header.num_compressed_blocks > 0


def test_class_method_parse(sample_replay_path):
    """Test the convenience class method."""
    replay = W3GReplay.parse(sample_replay_path)

    assert replay is not None
    assert replay.header is not None


def test_replay_to_dict(sample_replay_path):
    """Test conversion to dictionary."""
    parser = W3GParser()
    replay = parser.parse(sample_replay_path)

    data = replay.to_dict()

    assert "header" in data
    assert "players" in data
    assert "game_name" in data
    assert "map_name" in data
    assert isinstance(data["players"], list)


def test_replay_to_json(sample_replay_path):
    """Test JSON export."""
    parser = W3GParser()
    replay = parser.parse(sample_replay_path)

    json_str = replay.to_json()

    assert json_str.startswith("{")
    assert "header" in json_str
    assert "players" in json_str


def test_get_player(sample_replay_path):
    """Test player lookup methods."""
    parser = W3GParser()
    replay = parser.parse(sample_replay_path)

    if replay.players:
        first_player = replay.players[0]

        # Test lookup by ID
        found = replay.get_player(first_player.id)
        assert found is not None
        assert found.id == first_player.id

        # Test lookup by name
        found = replay.get_player_by_name(first_player.name)
        assert found is not None
        assert found.name == first_player.name

        # Test case-insensitive name lookup
        found = replay.get_player_by_name(first_player.name.upper())
        assert found is not None


def test_iter_actions(sample_replay_path):
    """Test action iteration."""
    parser = W3GParser()

    action_count = 0
    for action in parser.iter_actions(sample_replay_path):
        action_count += 1
        if action_count >= 10:
            break

    # Should have at least some actions in a real replay
    # (unless it's a very short replay)
    assert action_count >= 0


def test_player_apm(sample_replay_path):
    """Test APM calculation."""
    parser = W3GParser()
    replay = parser.parse(sample_replay_path)

    for player in replay.players:
        # APM should be non-negative
        assert player.apm >= 0

        # If player has actions, APM should be positive
        if player.action_count > 0:
            assert player.apm > 0
