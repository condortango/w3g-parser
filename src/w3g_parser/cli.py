"""Command-line interface for W3G parser."""

import json
import sys
from pathlib import Path

import click

from w3g_parser.parser import W3GParser


def format_duration(duration) -> str:
    """Format timedelta as HH:MM:SS."""
    total_seconds = int(duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


@click.group()
@click.version_option(version="0.1.0")
def main():
    """W3G Replay Parser - Parse Warcraft 3 replay files."""
    pass


@main.command()
@click.argument("replay", type=click.Path(exists=True))
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.option("--output", "-o", type=click.Path(), help="Output file (default: stdout)")
@click.option("--indent", type=int, default=2, help="JSON indent level")
def parse(replay: str, output_format: str, output: str | None, indent: int):
    """Parse a replay file and display information."""
    try:
        parser = W3GParser()
        result = parser.parse(replay)

        if output_format == "json":
            out = result.to_json(indent=indent)
        else:
            out = format_replay_text(result)

        if output:
            Path(output).write_text(out, encoding="utf-8")
            click.echo(f"Output written to {output}")
        else:
            click.echo(out)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("replay", type=click.Path(exists=True))
def players(replay: str):
    """Show player information."""
    try:
        parser = W3GParser()
        result = parser.parse(replay)

        click.echo(f"Players ({len(result.players)}):")
        click.echo("-" * 60)

        for p in result.players:
            status = []
            if p.is_host:
                status.append("Host")
            if p.is_computer:
                status.append("Computer")
            if p.is_observer:
                status.append("Observer")
            if p.leave_result:
                status.append(p.leave_result.name)

            status_str = f" [{', '.join(status)}]" if status else ""

            click.echo(
                f"  {p.name} - {p.race.name} (Team {p.team}, Color {p.color})"
                f" - APM: {p.apm:.1f}{status_str}"
            )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("replay", type=click.Path(exists=True))
def chat(replay: str):
    """Show chat messages."""
    try:
        parser = W3GParser()
        result = parser.parse(replay)

        if not result.chat_messages:
            click.echo("No chat messages in this replay.")
            return

        click.echo(f"Chat Messages ({len(result.chat_messages)}):")
        click.echo("-" * 60)

        for msg in result.chat_messages:
            ts = format_duration(msg.timestamp)
            mode = f" [{msg.mode_name}]" if msg.mode != 0 else ""
            click.echo(f"[{ts}]{mode} {msg.player_name}: {msg.message}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("replay", type=click.Path(exists=True))
def info(replay: str):
    """Show basic replay information (fast, header only)."""
    try:
        parser = W3GParser()
        header = parser.parse_header_only(replay)

        click.echo("Replay Information:")
        click.echo("-" * 40)
        click.echo(f"  Version: {header.version_string}")
        click.echo(f"  Build: {header.build_number}")
        click.echo(f"  Duration: {format_duration(header.duration)}")
        click.echo(f"  Game ID: {header.game_identifier}")
        click.echo(f"  Multiplayer: {'Yes' if header.is_multiplayer else 'No'}")
        click.echo(f"  Expansion: {'Yes' if header.is_expansion else 'No'}")
        click.echo(f"  Reforged: {'Yes' if header.is_reforged else 'No'}")
        click.echo(f"  Compressed Size: {header.compressed_size:,} bytes")
        click.echo(f"  Decompressed Size: {header.decompressed_size:,} bytes")
        click.echo(f"  Blocks: {header.num_compressed_blocks}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("replays", type=click.Path(exists=True), nargs=-1)
@click.option("--output", "-o", type=click.Path(), required=True, help="Output JSON file")
def batch(replays: tuple[str, ...], output: str):
    """Parse multiple replays to a JSON array."""
    if not replays:
        click.echo("No replay files specified.", err=True)
        sys.exit(1)

    parser = W3GParser(strict=False)
    results = []
    errors = 0

    with click.progressbar(replays, label="Parsing replays") as bar:
        for replay_path in bar:
            try:
                result = parser.parse(replay_path)
                data = result.to_dict()
                data["_source_file"] = str(replay_path)
                results.append(data)
            except Exception as e:
                click.echo(f"\nError parsing {replay_path}: {e}", err=True)
                errors += 1

    Path(output).write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    click.echo(f"Parsed {len(results)} replays to {output} ({errors} errors)")


@main.command()
@click.argument("replay", type=click.Path(exists=True))
@click.option("--limit", "-n", type=int, default=50, help="Maximum actions to show")
@click.option("--detail", "-d", is_flag=True, help="Show detailed action information")
@click.option(
    "--filter",
    "-f",
    "action_filter",
    type=str,
    help="Filter by action type (e.g., ability_position, select_units)",
)
def actions(replay: str, limit: int, detail: bool, action_filter: str | None):
    """Show game actions."""
    from w3g_parser.actions import decode_item_id

    try:
        parser = W3GParser()
        result = parser.parse(replay)

        # Filter actions if requested
        filtered_actions = result.actions
        if action_filter:
            filtered_actions = [
                a for a in result.actions if action_filter.lower() in a.action_name.lower()
            ]

        total = len(filtered_actions)
        shown = min(limit, total)

        filter_note = f" matching '{action_filter}'" if action_filter else ""
        click.echo(f"Game Actions (showing {shown} of {total}{filter_note}):")
        click.echo("-" * 70)

        for action in filtered_actions[:limit]:
            ts = format_duration(action.timestamp)
            player = result.get_player(action.player_id)
            player_name = player.name if player else f"Player {action.player_id}"

            if detail:
                # Show detailed action info
                detail_parts = []

                # Decode item/ability ID
                if "item_id" in action.data:
                    item_bytes = action.data["item_id"]
                    if isinstance(item_bytes, bytes):
                        decoded = decode_item_id(item_bytes)
                        detail_parts.append(decoded)

                # Add coordinates
                if "target_x" in action.data and "target_y" in action.data:
                    x, y = action.data["target_x"], action.data["target_y"]
                    if x == x and y == y:  # Check for NaN
                        detail_parts.append(f"at ({x:.0f}, {y:.0f})")

                # Add unit count with select mode and object IDs
                if "unit_count" in action.data:
                    count = action.data["unit_count"]
                    mode = action.data.get("select_mode", 0)
                    mode_str = "+" if mode == 1 else "-" if mode == 2 else ""
                    obj_ids = action.data.get("object_ids", [])
                    if obj_ids:
                        # Show object IDs in hex (shorter format)
                        ids_str = ",".join(f"{oid:x}" for oid in obj_ids[:5])
                        if len(obj_ids) > 5:
                            ids_str += f"...+{len(obj_ids)-5}"
                        detail_parts.append(f"{mode_str}{count} unit(s) [{ids_str}]")
                    else:
                        detail_parts.append(f"{mode_str}{count} unit(s)")

                # Add group number
                if "group" in action.data:
                    detail_parts.append(f"group {action.data['group']}")

                # Add resource transfer info
                if "gold" in action.data or "lumber" in action.data:
                    gold = action.data.get("gold", 0)
                    lumber = action.data.get("lumber", 0)
                    detail_parts.append(f"gold={gold}, lumber={lumber}")

                detail_str = " - " + " ".join(detail_parts) if detail_parts else ""
                click.echo(f"[{ts}] {player_name}: {action.action_name}{detail_str}")
            else:
                click.echo(f"[{ts}] {player_name}: {action.action_name}")

        if total > limit:
            click.echo(f"\n... and {total - limit} more actions")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def format_replay_text(replay) -> str:
    """Format replay as human-readable text."""
    lines = []

    lines.append("=" * 60)
    lines.append("WARCRAFT III REPLAY")
    lines.append("=" * 60)
    lines.append("")

    # Header info
    lines.append("GAME INFO")
    lines.append("-" * 40)
    lines.append(f"  Game Name: {replay.game_name}")
    lines.append(f"  Map: {replay.map_name}")
    lines.append(f"  Map Path: {replay.map_path}")
    lines.append(f"  Host: {replay.host_name}")
    lines.append(f"  Duration: {format_duration(replay.header.duration)}")
    lines.append(f"  Version: {replay.header.version_string}")
    lines.append(f"  Build: {replay.header.build_number}")
    lines.append("")

    # Settings
    lines.append("SETTINGS")
    lines.append("-" * 40)
    lines.append(f"  Speed: {replay.settings.speed_name}")
    lines.append(f"  Lock Teams: {'Yes' if replay.settings.lock_teams else 'No'}")
    lines.append(f"  Random Races: {'Yes' if replay.settings.random_races else 'No'}")
    lines.append(f"  Random Hero: {'Yes' if replay.settings.random_hero else 'No'}")
    lines.append("")

    # Players
    lines.append("PLAYERS")
    lines.append("-" * 40)
    for p in replay.players:
        status = []
        if p.is_host:
            status.append("Host")
        if p.is_computer:
            status.append("AI")
        if p.is_observer:
            status.append("Obs")
        if p.leave_result:
            status.append(p.leave_result.name)
        status_str = f" ({', '.join(status)})" if status else ""

        lines.append(
            f"  {p.name}{status_str}"
        )
        lines.append(
            f"    Race: {p.race.name}, Team: {p.team}, "
            f"Color: {p.color}, APM: {p.apm:.1f}"
        )
    lines.append("")

    # Winner
    winner = replay.winner
    if winner:
        lines.append("RESULT")
        lines.append("-" * 40)
        lines.append(f"  Winner: {winner.name}")
        lines.append("")

    # Chat summary
    if replay.chat_messages:
        lines.append("CHAT")
        lines.append("-" * 40)
        for msg in replay.chat_messages[:10]:
            ts = format_duration(msg.timestamp)
            lines.append(f"  [{ts}] {msg.player_name}: {msg.message}")
        if len(replay.chat_messages) > 10:
            lines.append(f"  ... and {len(replay.chat_messages) - 10} more messages")
        lines.append("")

    # Action summary
    lines.append("ACTIONS")
    lines.append("-" * 40)
    lines.append(f"  Total Actions: {len(replay.actions)}")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
