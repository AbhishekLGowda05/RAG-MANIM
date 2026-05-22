"""Shared helpers for concept template code-generators."""
from __future__ import annotations

from typing import Any

_HEADER = """\
from manim import *
import numpy as np


class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = "#0f1117"
"""

_FOOTER = """\
        self.play(FadeOut(*self.mobjects), run_time=0.40)
"""

BG = "#0f1117"
TITLE_COLOR = "#e0e6f0"
TEXT_COLOR = "#c8d3e6"
ACCENT1 = "#4f8ef7"
ACCENT2 = "#41d4a8"
FORCE_COLOR = "#ff7a59"
GROUND_COLOR = "#909090"
ICE_COLOR = "#a8d8ea"
VEL_COLOR = "#4fc3f7"


def get_event(timeline: dict[str, Any], event_id: str) -> dict[str, Any] | None:
    """Look up a timed event by id from the event timeline."""
    for ev in timeline.get("events", []):
        if ev["id"] == event_id:
            return ev
    return None


def get_event_by_type(
    timeline: dict[str, Any],
    plan_events: list[dict[str, Any]],
    event_type: str,
    fallback_id: str | None = None,
) -> dict[str, Any] | None:
    """Look up a timed event by semantic type using the plan's event list as index.

    Falls back to `fallback_id` lookup if type is not found.
    """
    for plan_ev in plan_events:
        if plan_ev.get("type") == event_type:
            found = get_event(timeline, plan_ev["id"])
            if found is not None:
                return found
    if fallback_id:
        return get_event(timeline, fallback_id)
    return None


def event_rt(timeline: dict[str, Any], event_id: str, default: float = 0.7) -> float:
    ev = get_event(timeline, event_id)
    if ev is None:
        return default
    rt = float(ev["run_time"])
    # Hold events have run_time=0; return default so templates don't get 0-second plays
    return rt if rt >= 0.1 else default


def event_rt_type(
    timeline: dict[str, Any],
    plan_events: list[dict[str, Any]],
    event_type: str,
    fallback_id: str | None = None,
    default: float = 0.7,
) -> float:
    """Get run_time for first event of given type; falls back by id then to default."""
    ev = get_event_by_type(timeline, plan_events, event_type, fallback_id)
    if ev is None:
        return default
    rt = float(ev["run_time"])
    return rt if rt >= 0.1 else default


def event_hold_type(
    timeline: dict[str, Any],
    plan_events: list[dict[str, Any]],
    event_type: str = "hold",
    default: float = 1.2,
) -> float:
    """Get hold_after for first event of given type (typically 'hold')."""
    ev = get_event_by_type(timeline, plan_events, event_type)
    if ev is None:
        return default
    ha = float(ev.get("hold_after", 0.0))
    return ha if ha >= 0.3 else default


def event_start(timeline: dict[str, Any], event_id: str, default: float = 0.0) -> float:
    ev = get_event(timeline, event_id)
    return float(ev["start"]) if ev else default


def event_hold(timeline: dict[str, Any], event_id: str, default: float = 0.0) -> float:
    ev = get_event(timeline, event_id)
    if ev is None:
        return default
    ha = float(ev.get("hold_after", 0.0))
    return ha


def build_sequential(
    blocks: list[tuple[str, float]],
    audio_duration: float,
    outro_time: float = 0.40,
) -> str:
    """Given (animation_code, duration) blocks, emit sequential wait-gapped code.

    `blocks` is ordered by event start time.  Gaps between events are filled
    with self.wait().  A tail wait absorbs any remaining audio time.
    """
    lines: list[str] = []
    elapsed = 0.0
    for code, duration in blocks:
        lines.append(code)
        elapsed += duration

    tail = audio_duration - elapsed - outro_time
    if tail > 0.05:
        lines.append(f"        self.wait({tail:.3f})\n")
    return "".join(lines)


def indent(code: str, spaces: int = 8) -> str:
    """Indent every non-empty line of code by `spaces` spaces."""
    pad = " " * spaces
    result = []
    for line in code.splitlines():
        result.append(pad + line if line.strip() else "")
    return "\n".join(result)


def asset_param(plan: dict[str, Any], role: str, key: str, default: Any = "") -> Any:
    """Extract a param value from the plan's assets list by role."""
    for a in plan.get("assets", []):
        if a["role"] == role:
            return a.get("params", {}).get(key, default)
    return default


def asset_instance(plan: dict[str, Any], role: str) -> str | None:
    """Return the instance_id for an asset role."""
    for a in plan.get("assets", []):
        if a["role"] == role:
            return a.get("instance_id")
    return None
