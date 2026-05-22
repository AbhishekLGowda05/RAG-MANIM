"""Narration writer: generates and validates narration for each scene.

Given a semantic plan with events that have anchor_phrases, this module
generates a narration script that:
  1. Contains every anchor_phrase verbatim (as a contiguous substring)
  2. Preserves the anchor phrases in order
  3. Sounds natural and educational (35-60 words per scene)

Validation: verifies each anchor_phrase is a case-insensitive substring
of the final narration. Retries up to 3 times with stricter prompts.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from modules.config import NVIDIA_PLANNER_MODEL, PATHS, get_logger
from modules.llm.nvidia_client import NvidiaClient

logger = get_logger(__name__)

NARRATION_SYSTEM = """You are an expert educational video narrator.
Write clear, engaging narration for short animated physics scenes.
CRITICAL: You MUST include every required phrase EXACTLY as given — verbatim, as-is.
Respond with ONLY the narration text. No JSON, no commentary."""

NARRATION_PROMPT = """Write narration for this scene. It will be read aloud over an animation.

SCENE TITLE: {title}
ANCHOR EXAMPLE: {anchor_example}
LEARNING GOAL: {learning_goal}

REQUIRED PHRASES (include EVERY phrase VERBATIM in this order):
{phrases}

RULES:
- Length: 40-65 words
- Conversational, clear, educational tone
- Each required phrase must appear EXACTLY as written above — do not paraphrase
- The phrases must appear in the order listed
- Surround each required phrase with natural connective language

Return ONLY the narration text:"""

NARRATION_REPAIR_PROMPT = """Your previous narration was MISSING these required phrases:
{missing}

SCENE: {title}
REQUIRED (ALL must appear verbatim): {phrases}

Rewrite the narration (40-65 words) making sure EVERY phrase above appears EXACTLY as written.
Return ONLY the narration text:"""


def write_narration(plan: dict[str, Any]) -> str:
    """Generate narration for one scene and validate anchor phrases."""
    scene_id = plan["scene_id"]
    title = plan.get("title", f"Scene {scene_id}")
    anchor_example = plan.get("anchor_example", "")
    learning_goal = plan.get("learning_goal", "")
    events = plan.get("events", [])
    phrases = [ev["anchor_phrase"] for ev in events if ev.get("anchor_phrase", "").strip()]
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_phrases: list[str] = []
    for p in phrases:
        if p.lower() not in seen:
            seen.add(p.lower())
            unique_phrases.append(p)

    if not unique_phrases:
        # No anchor phrases — generate free narration
        logger.warning("Scene %d has no anchor phrases; generating free narration", scene_id)
        return _generate_free(title, anchor_example, learning_goal, scene_id)

    client = NvidiaClient()
    phrases_display = "\n".join(f'  "{p}"' for p in unique_phrases)
    prompt = NARRATION_PROMPT.format(
        title=title,
        anchor_example=anchor_example,
        learning_goal=learning_goal,
        phrases=phrases_display,
    )
    messages = [
        {"role": "system", "content": NARRATION_SYSTEM},
        {"role": "user", "content": prompt},
    ]

    narration = ""
    for attempt in range(3):
        text = client.chat(NVIDIA_PLANNER_MODEL, messages, temperature=0.35, max_tokens=512)
        text = text.strip()
        missing = _find_missing(text, unique_phrases)
        if not missing:
            narration = text
            break
        logger.warning(
            "Scene %d narration attempt %d missing phrases: %s", scene_id, attempt + 1, missing
        )
        repair_prompt = NARRATION_REPAIR_PROMPT.format(
            missing="\n".join(f'  "{p}"' for p in missing),
            title=title,
            phrases=phrases_display,
        )
        messages = [
            {"role": "system", "content": NARRATION_SYSTEM},
            {"role": "user", "content": repair_prompt},
        ]

    if not narration:
        # Use last attempt even if imperfect
        narration = text
        logger.warning(
            "Scene %d: narration validation failed after 3 attempts; using best attempt", scene_id
        )

    _save_narration(scene_id, narration)
    return narration


def write_all_narrations(plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Write narrations for all plans and attach them in-place."""
    for plan in plans:
        narration = write_narration(plan)
        plan["narration"] = narration
        logger.info(
            "Narration for scene %d (%d words): %s…",
            plan["scene_id"],
            len(narration.split()),
            narration[:60],
        )
    return plans


def _find_missing(narration: str, phrases: list[str]) -> list[str]:
    """Return any phrases that are NOT verbatim substrings of the narration."""
    lower = narration.lower()
    return [p for p in phrases if p.lower() not in lower]


def _generate_free(title: str, anchor: str, goal: str, scene_id: int) -> str:
    """Fallback: generate narration without phrase constraints."""
    client = NvidiaClient()
    prompt = (
        f"Write a 40-60 word educational narration for: {title}. "
        f"Anchor example: {anchor}. Goal: {goal}."
    )
    text = client.chat(
        NVIDIA_PLANNER_MODEL,
        [{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=256,
    )
    narration = text.strip()
    _save_narration(scene_id, narration)
    return narration


def _save_narration(scene_id: int, narration: str) -> None:
    txt_path = PATHS["audio"] / f"scene_{scene_id}.txt"
    txt_path.write_text(narration, encoding="utf-8")
    logger.debug("Narration saved to %s", txt_path)
