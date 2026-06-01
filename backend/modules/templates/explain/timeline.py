"""Ordered steps timeline chalkboard template."""
from __future__ import annotations

from typing import Any

from modules.templates.explain._base import (
    EXPLAIN_ALLOWED_EVENTS,
    audio_duration,
    esc,
    events_literal,
    merge_content,
    wrap_explain_scene,
)

CONTENT_SCHEMA = """{
  "title": "<scene title>",
  "events": ["<step 1 label>", "<step 2 label>", "<step 3 label>"]
}
Provide 3-5 short event labels in chronological order."""


class TimelineTemplate:
    ALLOWED_EVENTS = EXPLAIN_ALLOWED_EVENTS
    CONTENT_SCHEMA = CONTENT_SCHEMA
    SLOTS = {}

    @staticmethod
    def compile(plan: dict[str, Any], timeline: dict[str, Any]) -> str:
        content = merge_content(plan, "timeline")
        dur = audio_duration(timeline)
        events_json = events_literal(content.get("events", []))

        body = f"""self.build_scene(
            title_text="{esc(str(content.get('title', plan.get('title', 'Timeline'))))}",
            events={events_json},
            audio_duration={dur:.3f},
        )"""
        return wrap_explain_scene("timeline_scene", "TimelineScene", body)
