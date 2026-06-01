"""Relationship diagram chalkboard template."""
from __future__ import annotations

from typing import Any

from modules.templates.explain._base import (
    EXPLAIN_ALLOWED_EVENTS,
    audio_duration,
    esc,
    merge_content,
    nodes_literal,
    wrap_explain_scene,
)

CONTENT_SCHEMA = """{
  "title": "<scene title>",
  "nodes": ["<node A>", "<node B>", "<node C>"]
}
Provide 3-6 node labels showing structure or flow (cause → effect, parts of a system, etc.)."""


class DiagramTemplate:
    ALLOWED_EVENTS = EXPLAIN_ALLOWED_EVENTS
    CONTENT_SCHEMA = CONTENT_SCHEMA
    SLOTS = {}

    @staticmethod
    def compile(plan: dict[str, Any], timeline: dict[str, Any]) -> str:
        content = merge_content(plan, "diagram")
        dur = audio_duration(timeline)
        nodes_json = nodes_literal(content.get("nodes", []))

        body = f"""self.build_scene(
            title_text="{esc(str(content.get('title', plan.get('title', 'Diagram'))))}",
            nodes={nodes_json},
            audio_duration={dur:.3f},
        )"""
        return wrap_explain_scene("diagram_scene", "DiagramScene", body)
