"""Shared helpers for chalkboard explanation template code-generators."""
from __future__ import annotations

import json
import re
from typing import Any

EXPLAIN_ALLOWED_EVENTS = frozenset({
    "place_title", "reveal", "highlight", "hold",
})

_EXPLAIN_HEADER = """\
from manim import *
import numpy as np
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from modules.manim.templates.{scene_module} import {scene_class}


class GeneratedScene({scene_class}):
    def construct(self):
"""

_EXPLAIN_FOOTER = """\
        self.play(FadeOut(*self.mobjects), run_time=0.40)
"""


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def esc_latex(text: str) -> str:
    s = str(text).strip()
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return s


def audio_duration(timeline: dict[str, Any]) -> float:
    return float(timeline.get("audio_duration", 8.0))


def wrap_explain_scene(
    scene_module: str,
    scene_class: str,
    body: str,
) -> str:
    header = _EXPLAIN_HEADER.format(scene_module=scene_module, scene_class=scene_class)
    indented = "\n".join(
        ("        " + line if line.strip() else "") for line in body.splitlines()
    )
    return header + indented + "\n" + _EXPLAIN_FOOTER


def content_dict(plan: dict[str, Any]) -> dict[str, Any]:
    raw = plan.get("content")
    return dict(raw) if isinstance(raw, dict) else {}


def default_content(plan: dict[str, Any], template_id: str) -> dict[str, Any]:
    title = plan.get("title", plan.get("anchor_example", "Concept"))
    goal = plan.get("learning_goal", "")
    anchor = plan.get("anchor_example", "")

    if template_id == "concept_card":
        return {
            "main_title": title,
            "cards": [
                {"title": "Definition", "content": goal or anchor, "color": "#7BA7C2"},
                {"title": "Key idea", "content": anchor or title, "color": "#7AC2A0"},
            ],
        }
    if template_id == "comparison":
        return {
            "left_title": "Without",
            "left_content": anchor or "Baseline case",
            "right_title": "With",
            "right_content": goal or title,
        }
    if template_id == "equation":
        return {
            "title": title,
            "equation": r"F = ma",
            "explanation": goal or anchor,
        }
    if template_id == "timeline":
        return {
            "title": title,
            "events": [anchor or "Step 1", goal or "Step 2", "Summary"],
        }
    if template_id == "diagram":
        return {
            "title": title,
            "nodes": [anchor or "Input", "Process", "Output"],
        }
    return {}


def merge_content(plan: dict[str, Any], template_id: str) -> dict[str, Any]:
    defaults = default_content(plan, template_id)
    user = content_dict(plan)
    merged = {**defaults, **user}
    return merged


def cards_literal(cards: list[dict[str, Any]]) -> str:
    safe = []
    for c in cards[:4]:
        if not isinstance(c, dict):
            continue
        safe.append({
            "title": str(c.get("title", "Part"))[:40],
            "content": str(c.get("content", ""))[:120],
            "color": str(c.get("color", "#7BA7C2")),
        })
    if not safe:
        safe = [
            {"title": "Part 1", "content": "Concept", "color": "#7BA7C2"},
            {"title": "Part 2", "content": "Detail", "color": "#7AC2A0"},
        ]
    return json.dumps(safe, ensure_ascii=False)


def nodes_literal(nodes: list[Any]) -> str:
    labels = []
    for n in nodes:
        if isinstance(n, dict):
            labels.append(str(n.get("label", n.get("name", "?")))[:24])
        else:
            labels.append(str(n)[:24])
    if not labels:
        labels = ["A", "B", "C"]
    return json.dumps(labels[:8], ensure_ascii=False)


def events_literal(events: list[Any]) -> str:
    labels = [str(e)[:36] for e in events if e]
    if not labels:
        labels = ["Step 1", "Step 2", "Step 3"]
    return json.dumps(labels[:6], ensure_ascii=False)
