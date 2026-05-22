"""Semantic plan generator.

For each storyboard entry, the LLM fills the template's slot schema:
  - which assets to use (from ASSET_REGISTRY)
  - which event types (from the template's ALLOWED_EVENTS)
  - anchor_phrases that MUST later appear verbatim in the narration

Strict validation:
  - asset_ids must be in ASSET_REGISTRY
  - event types must be in the template's ALLOWED_EVENTS
  - anchor_phrases are recorded (the narration writer will embed them)
"""
from __future__ import annotations

import json
from typing import Any

from modules.assets import ASSET_REGISTRY
from modules.config import NVIDIA_PLANNER_MODEL, PATHS, get_logger
from modules.llm.nvidia_client import NvidiaClient
from modules.planning.asset_registry import get_registry
from modules.templates import TEMPLATES

logger = get_logger(__name__)

SEMANTIC_PLAN_SYSTEM = """You are an educational animation director.
You assign physics assets and event sequences to scenes.
NEVER include run_time, duration, seconds, or timing fields.
Respond ONLY with valid JSON. No markdown fences."""

SEMANTIC_PLAN_PROMPT = """Fill the semantic plan for this scene.

STORYBOARD ENTRY:
{storyboard_entry}

TEMPLATE: {template_id}
TEMPLATE ALLOWED EVENTS: {allowed_events}

AVAILABLE ASSET IDs: {asset_ids}

RULES:
1. Fill the "assets" array using only asset_ids from the AVAILABLE list.
2. Each event "type" must be from ALLOWED EVENTS.
3. Each event "anchor_phrase" must be 3-7 words that will appear VERBATIM
   in the narration script later. Choose clear, descriptive phrases.
4. "phase" must be "before", "on", or "after" (when relative to the phrase).
5. "importance" is 1-5 (5 = most critical, gets longest animation time).
6. instance_id must be unique snake_case (e.g. "puck_a", "ice_surface").
7. Do NOT invent asset_ids — only use those listed.

Return ONLY this JSON shape:
{{
  "scene_id": {scene_id},
  "concept_template": "{template_id}",
  "title": "<short scene title>",
  "anchor_example": "{anchor_example}",
  "assets": [
    {{
      "role": "<slot role matching template>",
      "asset_id": "<from AVAILABLE list>",
      "instance_id": "<unique snake_case>",
      "params": {{<asset-specific params like label, color, direction>}}
    }}
  ],
  "events": [
    {{
      "id": "e0",
      "type": "<from ALLOWED EVENTS>",
      "targets": ["<instance_id>"],
      "anchor_phrase": "<3-7 verbatim words for narration>",
      "phase": "on",
      "importance": 3
    }}
  ]
}}"""


def build_semantic_plan(storyboard_entry: dict[str, Any]) -> dict[str, Any]:
    """Generate and validate a semantic plan for one storyboard entry."""
    scene_id = storyboard_entry["scene_id"]
    template_id = storyboard_entry["concept_template"]
    logger.info("Building semantic plan for scene %d (template=%s)", scene_id, template_id)

    template_cls = TEMPLATES.get(template_id)
    if template_cls is None:
        raise ValueError(f"Unknown template '{template_id}'")

    allowed_events = sorted(getattr(template_cls, "ALLOWED_EVENTS", set()))
    asset_ids = sorted(ASSET_REGISTRY.keys())
    anchor_example = storyboard_entry.get("anchor_example", "")

    client = NvidiaClient()
    prompt = SEMANTIC_PLAN_PROMPT.format(
        storyboard_entry=json.dumps(storyboard_entry, indent=2),
        template_id=template_id,
        allowed_events=", ".join(allowed_events),
        asset_ids=", ".join(asset_ids),
        scene_id=scene_id,
        anchor_example=anchor_example,
    )
    messages = [
        {"role": "system", "content": SEMANTIC_PLAN_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    raw = client.chat_json(NVIDIA_PLANNER_MODEL, messages, temperature=0.3, max_tokens=4096)
    plan = _validate_plan(raw, scene_id, template_id, allowed_events)

    # Carry over optional storyboard fields into plan
    for field in ("subtitle", "key_term", "summary_points", "learning_goal"):
        if field in storyboard_entry and field not in plan:
            plan[field] = storyboard_entry[field]

    # Register all assets in the global registry
    registry = get_registry()
    for asset in plan.get("assets", []):
        registry.register(
            instance_id=asset["instance_id"],
            asset_id=asset["asset_id"],
            params=asset.get("params", {}),
            scene_id=scene_id,
        )

    out = PATHS["json"] / f"semantic_plan_{scene_id}.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(
        "Semantic plan saved: %s (%d assets, %d events)",
        out, len(plan.get("assets", [])), len(plan.get("events", []))
    )
    return plan


def build_all_semantic_plans(storyboard: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [build_semantic_plan(entry) for entry in storyboard]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_plan(
    raw: Any,
    scene_id: int,
    template_id: str,
    allowed_events: list[str],
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"Semantic plan must be a dict, got {type(raw)}")

    # Normalise scene_id
    plan = dict(raw)
    plan["scene_id"] = scene_id
    plan["concept_template"] = template_id

    # Validate assets
    assets = plan.get("assets", [])
    if not isinstance(assets, list):
        plan["assets"] = []
        assets = []

    seen_instances: set[str] = set()
    valid_assets = []
    for asset in assets:
        asset_id = asset.get("asset_id", "")
        if asset_id not in ASSET_REGISTRY:
            logger.warning("Dropping asset with unknown asset_id '%s'", asset_id)
            continue
        iid = str(asset.get("instance_id", f"{asset_id}_{scene_id}"))
        if iid in seen_instances:
            iid = f"{iid}_{len(seen_instances)}"
        seen_instances.add(iid)
        valid_assets.append({
            "role": str(asset.get("role", asset_id)),
            "asset_id": asset_id,
            "instance_id": iid,
            "params": dict(asset.get("params", {})),
        })
    plan["assets"] = valid_assets

    # Validate events
    events = plan.get("events", [])
    if not isinstance(events, list):
        plan["events"] = []
        events = []

    valid_events = []
    for i, ev in enumerate(events):
        etype = str(ev.get("type", ""))
        if allowed_events and etype not in allowed_events:
            logger.warning(
                "Scene %d event '%s' has invalid type '%s' (allowed: %s); dropping",
                scene_id, ev.get("id", i), etype, allowed_events
            )
            continue
        valid_events.append({
            "id": str(ev.get("id", f"e{i}")),
            "type": etype,
            "targets": list(ev.get("targets", [])),
            "anchor_phrase": str(ev.get("anchor_phrase", "")),
            "phase": str(ev.get("phase", "on")),
            "importance": max(1, min(5, int(ev.get("importance", 3)))),
        })
    plan["events"] = valid_events

    # Ensure title
    if "title" not in plan or not plan["title"]:
        plan["title"] = str(raw.get("anchor_example", f"Scene {scene_id}"))

    return plan
