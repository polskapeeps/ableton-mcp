from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp.server.fastmcp import Context, FastMCP

from .connection import get_ableton_connection
from .protocol import error_response, normalize_response


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("AbletonMCPServer")


def invoke_ableton(command_type: str, **params: Any) -> dict[str, Any]:
    try:
        connection = get_ableton_connection()
        response = connection.send_command(command_type, params)
        return normalize_response(response)
    except Exception as exc:
        logger.error("Error running Ableton command %s: %s", command_type, exc)
        return error_response("live_not_connected", str(exc))


@asynccontextmanager
async def server_lifespan(_: FastMCP) -> AsyncIterator[dict[str, Any]]:
    logger.info("AbletonMCP server starting")
    yield {}
    try:
        get_ableton_connection().disconnect()
    except Exception:
        logger.debug("Ignoring disconnect error during shutdown", exc_info=True)
    logger.info("AbletonMCP server stopped")


mcp = FastMCP("AbletonMCP", lifespan=server_lifespan)


@mcp.tool()
def live_status(ctx: Context) -> dict[str, Any]:
    """Return transport, selection, and session-level Ableton state."""

    return invoke_ableton("live_status")


@mcp.tool()
def list_tracks(ctx: Context) -> dict[str, Any]:
    """Return all session tracks with mixer and playback summary fields."""

    return invoke_ableton("list_tracks")


@mcp.tool()
def list_scenes(ctx: Context) -> dict[str, Any]:
    """Return all scenes with launch and naming metadata."""

    return invoke_ableton("list_scenes")


@mcp.tool()
def list_clip_slots(ctx: Context, track_index: int) -> dict[str, Any]:
    """Return every clip slot for a track, including clip summaries when present."""

    return invoke_ableton("list_clip_slots", track_index=track_index)


@mcp.tool()
def list_devices(ctx: Context, track_index: int) -> dict[str, Any]:
    """Return the devices for a track."""

    return invoke_ableton("list_devices", track_index=track_index)


@mcp.tool()
def list_parameters(ctx: Context, track_index: int, device_index: int) -> dict[str, Any]:
    """Return all automatable parameters for a track device."""

    return invoke_ableton(
        "list_parameters",
        track_index=track_index,
        device_index=device_index,
    )


@mcp.tool()
def transport_play(ctx: Context) -> dict[str, Any]:
    """Start transport playback from the current start point."""

    return invoke_ableton("transport_play")


@mcp.tool()
def transport_continue(ctx: Context) -> dict[str, Any]:
    """Continue playback from the current transport position."""

    return invoke_ableton("transport_continue")


@mcp.tool()
def transport_stop(ctx: Context) -> dict[str, Any]:
    """Stop Ableton transport playback."""

    return invoke_ableton("transport_stop")


@mcp.tool()
def transport_set_tempo(ctx: Context, tempo: float) -> dict[str, Any]:
    """Set the song tempo in BPM."""

    return invoke_ableton("transport_set_tempo", tempo=tempo)


@mcp.tool()
def transport_set_metronome(ctx: Context, enabled: bool) -> dict[str, Any]:
    """Enable or disable the metronome."""

    return invoke_ableton("transport_set_metronome", enabled=enabled)


@mcp.tool()
def track_create_midi(ctx: Context, index: int = -1) -> dict[str, Any]:
    """Create a MIDI track at the given index or at the end when index is -1."""

    return invoke_ableton("track_create_midi", index=index)


@mcp.tool()
def track_create_audio(ctx: Context, index: int = -1) -> dict[str, Any]:
    """Create an audio track at the given index or at the end when index is -1."""

    return invoke_ableton("track_create_audio", index=index)


@mcp.tool()
def track_rename(ctx: Context, track_index: int, name: str) -> dict[str, Any]:
    """Rename a track."""

    return invoke_ableton("track_rename", track_index=track_index, name=name)


@mcp.tool()
def track_set_color(ctx: Context, track_index: int, color: int) -> dict[str, Any]:
    """Set a track color using Ableton's integer RGB color value."""

    return invoke_ableton("track_set_color", track_index=track_index, color=color)


@mcp.tool()
def track_set_arm(ctx: Context, track_index: int, armed: bool) -> dict[str, Any]:
    """Arm or disarm a track."""

    return invoke_ableton("track_set_arm", track_index=track_index, armed=armed)


@mcp.tool()
def track_set_mute(ctx: Context, track_index: int, muted: bool) -> dict[str, Any]:
    """Mute or unmute a track."""

    return invoke_ableton("track_set_mute", track_index=track_index, muted=muted)


@mcp.tool()
def track_set_solo(ctx: Context, track_index: int, soloed: bool) -> dict[str, Any]:
    """Solo or unsolo a track."""

    return invoke_ableton("track_set_solo", track_index=track_index, soloed=soloed)


@mcp.tool()
def track_set_volume(ctx: Context, track_index: int, value: float) -> dict[str, Any]:
    """Set a track's volume parameter."""

    return invoke_ableton("track_set_volume", track_index=track_index, value=value)


@mcp.tool()
def track_set_pan(ctx: Context, track_index: int, value: float) -> dict[str, Any]:
    """Set a track's pan parameter."""

    return invoke_ableton("track_set_pan", track_index=track_index, value=value)


@mcp.tool()
def track_set_send(
    ctx: Context,
    track_index: int,
    send_index: int,
    value: float,
) -> dict[str, Any]:
    """Set one of a track's send parameters."""

    return invoke_ableton(
        "track_set_send",
        track_index=track_index,
        send_index=send_index,
        value=value,
    )


@mcp.tool()
def track_stop_all_clips(ctx: Context, track_index: int) -> dict[str, Any]:
    """Stop all session clips on a track."""

    return invoke_ableton("track_stop_all_clips", track_index=track_index)


@mcp.tool()
def track_duplicate(
    ctx: Context,
    track_index: int,
    confirm_destructive: bool,
) -> dict[str, Any]:
    """Duplicate a track. Explicit confirmation is required because it changes project structure."""

    return invoke_ableton(
        "track_duplicate",
        track_index=track_index,
        confirm_destructive=confirm_destructive,
    )


@mcp.tool()
def track_delete(
    ctx: Context,
    track_index: int,
    confirm_destructive: bool,
) -> dict[str, Any]:
    """Delete a track. Explicit confirmation is required."""

    return invoke_ableton(
        "track_delete",
        track_index=track_index,
        confirm_destructive=confirm_destructive,
    )


@mcp.tool()
def scene_create(ctx: Context, index: int = -1) -> dict[str, Any]:
    """Create a scene."""

    return invoke_ableton("scene_create", index=index)


@mcp.tool()
def scene_launch(ctx: Context, scene_index: int) -> dict[str, Any]:
    """Launch a scene."""

    return invoke_ableton("scene_launch", scene_index=scene_index)


@mcp.tool()
def scene_rename(ctx: Context, scene_index: int, name: str) -> dict[str, Any]:
    """Rename a scene."""

    return invoke_ableton("scene_rename", scene_index=scene_index, name=name)


@mcp.tool()
def scene_set_color(ctx: Context, scene_index: int, color: int) -> dict[str, Any]:
    """Set a scene color using Ableton's integer RGB color value."""

    return invoke_ableton("scene_set_color", scene_index=scene_index, color=color)


@mcp.tool()
def scene_duplicate(
    ctx: Context,
    scene_index: int,
    confirm_destructive: bool,
) -> dict[str, Any]:
    """Duplicate a scene. Explicit confirmation is required because it changes project structure."""

    return invoke_ableton(
        "scene_duplicate",
        scene_index=scene_index,
        confirm_destructive=confirm_destructive,
    )


@mcp.tool()
def scene_delete(
    ctx: Context,
    scene_index: int,
    confirm_destructive: bool,
) -> dict[str, Any]:
    """Delete a scene. Explicit confirmation is required."""

    return invoke_ableton(
        "scene_delete",
        scene_index=scene_index,
        confirm_destructive=confirm_destructive,
    )


@mcp.tool()
def clip_create_midi(
    ctx: Context,
    track_index: int,
    clip_slot_index: int,
    length: float = 4.0,
) -> dict[str, Any]:
    """Create an empty MIDI clip in a session clip slot."""

    return invoke_ableton(
        "clip_create_midi",
        track_index=track_index,
        clip_slot_index=clip_slot_index,
        length=length,
    )


@mcp.tool()
def clip_fire(ctx: Context, track_index: int, clip_slot_index: int) -> dict[str, Any]:
    """Launch a clip slot."""

    return invoke_ableton(
        "clip_fire",
        track_index=track_index,
        clip_slot_index=clip_slot_index,
    )


@mcp.tool()
def clip_stop(ctx: Context, track_index: int, clip_slot_index: int) -> dict[str, Any]:
    """Stop the clip slot's track playback."""

    return invoke_ableton(
        "clip_stop",
        track_index=track_index,
        clip_slot_index=clip_slot_index,
    )


@mcp.tool()
def clip_rename(
    ctx: Context,
    track_index: int,
    clip_slot_index: int,
    name: str,
) -> dict[str, Any]:
    """Rename a clip."""

    return invoke_ableton(
        "clip_rename",
        track_index=track_index,
        clip_slot_index=clip_slot_index,
        name=name,
    )


@mcp.tool()
def clip_set_color(
    ctx: Context,
    track_index: int,
    clip_slot_index: int,
    color: int,
) -> dict[str, Any]:
    """Set a clip color using Ableton's integer RGB color value."""

    return invoke_ableton(
        "clip_set_color",
        track_index=track_index,
        clip_slot_index=clip_slot_index,
        color=color,
    )


@mcp.tool()
def clip_set_loop(
    ctx: Context,
    track_index: int,
    clip_slot_index: int,
    loop_start: float,
    loop_end: float,
    looping: bool = True,
) -> dict[str, Any]:
    """Set clip loop boundaries and loop enabled state."""

    return invoke_ableton(
        "clip_set_loop",
        track_index=track_index,
        clip_slot_index=clip_slot_index,
        loop_start=loop_start,
        loop_end=loop_end,
        looping=looping,
    )


@mcp.tool()
def clip_add_notes(
    ctx: Context,
    track_index: int,
    clip_slot_index: int,
    notes: list[dict[str, Any]],
) -> dict[str, Any]:
    """Add MIDI notes to a clip. Each note uses pitch, start_time, duration, velocity, and mute."""

    return invoke_ableton(
        "clip_add_notes",
        track_index=track_index,
        clip_slot_index=clip_slot_index,
        notes=notes,
    )


@mcp.tool()
def clip_duplicate(
    ctx: Context,
    track_index: int,
    clip_slot_index: int,
    confirm_destructive: bool,
) -> dict[str, Any]:
    """Duplicate a clip slot. Explicit confirmation is required because it changes project structure."""

    return invoke_ableton(
        "clip_duplicate",
        track_index=track_index,
        clip_slot_index=clip_slot_index,
        confirm_destructive=confirm_destructive,
    )


@mcp.tool()
def clip_delete(
    ctx: Context,
    track_index: int,
    clip_slot_index: int,
    confirm_destructive: bool,
) -> dict[str, Any]:
    """Delete a clip from a slot. Explicit confirmation is required."""

    return invoke_ableton(
        "clip_delete",
        track_index=track_index,
        clip_slot_index=clip_slot_index,
        confirm_destructive=confirm_destructive,
    )


@mcp.tool()
def device_set_parameter(
    ctx: Context,
    track_index: int,
    device_index: int,
    parameter_index: int,
    value: float,
) -> dict[str, Any]:
    """Set a specific device parameter."""

    return invoke_ableton(
        "device_set_parameter",
        track_index=track_index,
        device_index=device_index,
        parameter_index=parameter_index,
        value=value,
    )


@mcp.tool()
def device_delete(
    ctx: Context,
    track_index: int,
    device_index: int,
    confirm_destructive: bool,
) -> dict[str, Any]:
    """Delete a device from a track. Explicit confirmation is required."""

    return invoke_ableton(
        "device_delete",
        track_index=track_index,
        device_index=device_index,
        confirm_destructive=confirm_destructive,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
