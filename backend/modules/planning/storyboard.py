"""Storyboard planner: generates the conceptual arc for a topic.

Outputs an ordered list of 5 scenes, each with a concept_template and
anchor_example, forming a progressive educational narrative:
  Scene 1: intro (overview + key term)
  Scenes 2-4: core concept templates (mechanics)
  Scene 5: summary

Scene 2-4 templates and anchor examples MUST all differ — enforced both via
prompt rules and post-validation that rewrites duplicates to "freeform".
"""
from __future__ import annotations

import json
from typing import Any

from modules.config import NVIDIA_PLANNER_MODEL, PATHS, get_logger
from modules.llm.nvidia_client import NvidiaClient
from modules.planning.profile_context import format_learner_context
from modules.templates import VALID_TEMPLATE_IDS

logger = get_logger(__name__)

STORYBOARD_SYSTEM = """You are an expert educational video director.
You design 5-scene progressive lesson arcs that teach a topic through DISTINCT, varied examples.
NEVER include run_time, duration, seconds, or timing fields.
Respond ONLY with a valid JSON array. No markdown fences, no commentary."""

STORYBOARD_PROMPT = """Design a 5-scene educational video arc for this topic: {topic}

{learner_context}

TEMPLATE OPTIONS (choose the most appropriate for each scene):
{template_list}

If NO template above visually fits the topic for a given scene, use "freeform" and the LLM
will author a custom Manim scene from the scene plan.

REQUIREMENTS:
- Scene 1: always use "intro" template
- Scene 5: always use "summary" template
- Scenes 2-4: choose the template that best matches each scene's idea — prefer topic-specific
  templates ({template_ids}) when the topic aligns; otherwise pick "freeform".
- Scenes 2, 3, and 4 MUST have THREE DIFFERENT concept_templates AND THREE DIFFERENT
  anchor_examples. Do NOT reuse the same anchor across scenes. Each scene teaches a
  DIFFERENT facet (definition, mechanism, edge case, real-world application, etc.).
- Each scene's learning_goal must be a unique sentence.
- anchor_example: a concrete real-world object, scenario, or numerical setup, different per scene.
- subtitle (scene 1 only): short tagline for the intro
- key_term (scene 1 only): the central term to highlight
- summary_points (scene 5 only): list of 3 key takeaways

Return a JSON array of exactly 5 objects:
[
  {{
    "scene_id": 1,
    "concept_template": "intro",
    "title": "<topic> — Overview",
    "anchor_example": "<short hook>",
    "learning_goal": "introduce the concept",
    "subtitle": "<one-line tagline>",
    "key_term": "<central term>"
  }},
  {{
    "scene_id": 2,
    "concept_template": "<one of: {template_ids}>",
    "title": "...",
    "anchor_example": "<DISTINCT scenario A>",
    "learning_goal": "<unique goal A>"
  }},
  {{
    "scene_id": 3,
    "concept_template": "<DIFFERENT template>",
    "title": "...",
    "anchor_example": "<DISTINCT scenario B>",
    "learning_goal": "<unique goal B>"
  }},
  {{
    "scene_id": 4,
    "concept_template": "<DIFFERENT template>",
    "title": "...",
    "anchor_example": "<DISTINCT scenario C>",
    "learning_goal": "<unique goal C>"
  }},
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


def build_storyboard(
    topic: str,
    learner_profile: dict[str, Any] | None = None,
    subject: str = "Physics",
) -> list[dict[str, Any]]:
    """Generate a 5-scene storyboard arc for the given topic."""
    logger.info("Building storyboard for topic: %s", topic)
    client = NvidiaClient()

    template_list = "\n".join(f"  - {t}" for t in VALID_TEMPLATE_IDS)
    template_ids = ", ".join(
        t for t in VALID_TEMPLATE_IDS if t not in ("intro", "summary")
    )
    learner_context = format_learner_context(learner_profile, topic, subject)
    prompt = STORYBOARD_PROMPT.format(
        topic=topic,
        learner_context=learner_context,
        template_list=template_list,
        template_ids=template_ids,
    )
    messages = [
        {"role": "system", "content": STORYBOARD_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    raw = client.chat_json(NVIDIA_PLANNER_MODEL, messages, temperature=0.55, max_tokens=4096)

    if isinstance(raw, dict) and "scenes" in raw:
        raw = raw["scenes"]
    if not isinstance(raw, list):
        raise ValueError(f"Storyboard LLM returned {type(raw)}, expected list")

    validated = [_validate_entry(entry, idx) for idx, entry in enumerate(raw, start=1)]
    validated[0]["concept_template"] = "intro"
    validated[-1]["concept_template"] = "summary"
    validated = _enforce_distinct_middle(validated)

    out = PATHS["json"] / "storyboard.json"
    out.write_text(json.dumps(validated, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Storyboard saved: %s (%d scenes)", out, len(validated))
    return validated


def _validate_entry(entry: dict[str, Any], default_id: int) -> dict[str, Any]:
    scene_id = int(entry.get("scene_id", default_id))
    template = str(entry.get("concept_template", "intro"))
    if template not in VALID_TEMPLATE_IDS:
        logger.warning(
            "Scene %d has unknown template '%s'; falling back to 'freeform'",
            scene_id, template,
        )
        template = "freeform"

    result: dict[str, Any] = {
        "scene_id": scene_id,
        "concept_template": template,
        "title": str(entry.get("title", entry.get("anchor_example", f"Scene {scene_id}"))),
        "anchor_example": str(entry.get("anchor_example", "")),
        "learning_goal": str(entry.get("learning_goal", "")),
    }
    if "subtitle" in entry:
        result["subtitle"] = str(entry["subtitle"])
    if "key_term" in entry:
        result["key_term"] = str(entry["key_term"])
    if "summary_points" in entry and isinstance(entry["summary_points"], list):
        result["summary_points"] = [str(p) for p in entry["summary_points"][:4]]
    return result


def _enforce_distinct_middle(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure scenes 2-4 have distinct templates AND distinct anchor examples.

    Duplicates are rewritten to use the freeform template so the LLM generates
    a unique visual for that scene instead of replaying the same animation.
    """
    seen_templates: set[str] = set()
    seen_anchors: set[str] = set()
    for s in scenes[1:-1]:
        tpl = s.get("concept_template", "freeform")
        anchor_key = s.get("anchor_example", "").strip().lower()
        if tpl in seen_templates or tpl in ("intro", "summary"):
            logger.warning(
                "Scene %d duplicated template '%s'; rewriting to 'freeform'",
                s["scene_id"], tpl,
            )
            s["concept_template"] = "freeform"
            tpl = "freeform"
        seen_templates.add(tpl)
        if anchor_key and anchor_key in seen_anchors:
            logger.warning(
                "Scene %d duplicated anchor_example '%s'; rewriting to freeform",
                s["scene_id"], anchor_key,
            )
            s["concept_template"] = "freeform"
            s["anchor_example"] = f"{s['anchor_example']} (alternate framing)"
        seen_anchors.add(s.get("anchor_example", "").strip().lower())
    return scenes
