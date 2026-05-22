"""Storyboard planner: generates the conceptual arc for a topic.

Outputs an ordered list of 5 scenes, each with a concept_template and
anchor_example, forming a progressive educational narrative:
  Scene 1: intro (overview + key term)
  Scenes 2-4: core concept templates (mechanics)
  Scene 5: summary
"""
from __future__ import annotations

import json
from typing import Any

from modules.config import NVIDIA_PLANNER_MODEL, PATHS, get_logger
from modules.llm.nvidia_client import NvidiaClient
from modules.templates import VALID_TEMPLATE_IDS

logger = get_logger(__name__)

STORYBOARD_SYSTEM = """You are an expert educational video director.
You design 5-scene progressive lesson arcs for physics topics.
NEVER include run_time, duration, seconds, or timing fields.
Respond ONLY with a valid JSON array. No markdown fences, no commentary."""

STORYBOARD_PROMPT = """Design a 5-scene educational video arc for this topic: {topic}

TEMPLATE OPTIONS (choose the most appropriate for each scene):
{template_list}

REQUIREMENTS:
- Scene 1: always use "intro" template
- Scene 5: always use "summary" template
- Scenes 2-4: use templates that progressively build the concept
- Each scene should have a distinct learning goal
- anchor_example: a concrete real-world object or scenario (e.g. "hockey puck on ice", "sliding box")
- subtitle (scene 1 only): short tagline for the intro
- key_term (scene 1 only): the central physics term to highlight
- summary_points (scene 5 only): list of 3 key takeaways

Return a JSON array of exactly 5 objects:
[
  {{
    "scene_id": 1,
    "concept_template": "intro",
    "title": "Newton's First Law",
    "anchor_example": "objects in motion",
    "learning_goal": "introduce the concept",
    "subtitle": "Why do things keep moving?",
    "key_term": "Inertia"
  }},
  {{
    "scene_id": 2,
    "concept_template": "<one of: {template_ids}>",
    "title": "Object at Rest",
    "anchor_example": "hockey puck on ice",
    "learning_goal": "show an object staying at rest"
  }},
  ... (scenes 3, 4 follow same shape) ...
  {{
    "scene_id": 5,
    "concept_template": "summary",
    "title": "Key Takeaways",
    "anchor_example": "all scenarios",
    "learning_goal": "consolidate learning",
    "summary_points": ["...", "...", "..."]
  }}
]

Return ONLY the JSON array."""


def build_storyboard(topic: str) -> list[dict[str, Any]]:
    """Generate a 5-scene storyboard arc for the given topic."""
    logger.info("Building storyboard for topic: %s", topic)
    client = NvidiaClient()

    template_list = "\n".join(f"  - {t}" for t in VALID_TEMPLATE_IDS)
    template_ids = ", ".join(t for t in VALID_TEMPLATE_IDS if t not in ("intro", "summary"))
    prompt = STORYBOARD_PROMPT.format(
        topic=topic,
        template_list=template_list,
        template_ids=template_ids,
    )
    messages = [
        {"role": "system", "content": STORYBOARD_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    raw = client.chat_json(NVIDIA_PLANNER_MODEL, messages, temperature=0.4, max_tokens=4096)

    if isinstance(raw, dict) and "scenes" in raw:
        raw = raw["scenes"]
    if not isinstance(raw, list):
        raise ValueError(f"Storyboard LLM returned {type(raw)}, expected list")

    validated = [_validate_entry(entry, idx) for idx, entry in enumerate(raw, start=1)]
    # Enforce first/last template
    validated[0]["concept_template"] = "intro"
    validated[-1]["concept_template"] = "summary"

    out = PATHS["json"] / "storyboard.json"
    out.write_text(json.dumps(validated, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Storyboard saved: %s (%d scenes)", out, len(validated))
    return validated


def _validate_entry(entry: dict[str, Any], default_id: int) -> dict[str, Any]:
    """Validate and normalise one storyboard entry."""
    scene_id = int(entry.get("scene_id", default_id))
    template = str(entry.get("concept_template", "intro"))
    if template not in VALID_TEMPLATE_IDS:
        logger.warning(
            "Scene %d has unknown template '%s'; defaulting to 'inertia'", scene_id, template
        )
        template = "inertia"

    result: dict[str, Any] = {
        "scene_id": scene_id,
        "concept_template": template,
        "title": str(entry.get("title", entry.get("anchor_example", f"Scene {scene_id}"))),
        "anchor_example": str(entry.get("anchor_example", "")),
        "learning_goal": str(entry.get("learning_goal", "")),
    }
    # Optional fields
    if "subtitle" in entry:
        result["subtitle"] = str(entry["subtitle"])
    if "key_term" in entry:
        result["key_term"] = str(entry["key_term"])
    if "summary_points" in entry and isinstance(entry["summary_points"], list):
        result["summary_points"] = [str(p) for p in entry["summary_points"][:4]]
    return result
