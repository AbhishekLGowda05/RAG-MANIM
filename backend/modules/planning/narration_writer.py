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
from modules.planning.profile_context import format_learner_context

logger = get_logger(__name__)

NARRATION_SYSTEM = """You are an expert educational video narrator.
Write clear, engaging narration for short animated physics scenes.
CRITICAL: You MUST include every required phrase EXACTLY as given — verbatim, as-is.
Respond with ONLY the narration text. No JSON, no commentary."""

NARRATION_PROMPT = """Write narration for this scene. It will be read aloud over an animation.

{learner_context}

SCENE TITLE: {title}
ANCHOR EXAMPLE: {anchor_example}
LEARNING GOAL: {learning_goal}

REQUIRED PHRASES (include EVERY phrase VERBATIM in this order):
{phrases}

RULES:
- Length: {word_lo}-{word_hi} words (calibrated to the learner's pace).
- Conversational, clear, educational tone matching the learner's level.
- Each required phrase must appear EXACTLY as written above — do not paraphrase.
- The phrases must appear in the order listed.
- Surround each required phrase with natural connective language.
- For low-confidence learners, include one micro-analogy or relatable example inside the scene.

Return ONLY the narration text:"""

NARRATION_REPAIR_PROMPT = """Your previous narration was MISSING these required phrases:
{missing}

SCENE: {title}
REQUIRED (ALL must appear verbatim): {phrases}

Rewrite the narration ({word_lo}-{word_hi} words) making sure EVERY phrase above appears EXACTLY as written.
Return ONLY the narration text:"""


def write_narration(
    plan: dict[str, Any],
    learner_profile: dict[str, Any] | None = None,
    topic: str = "",
    subject: str = "Physics",
) -> str:
    """Generate narration for one scene and validate anchor phrases."""
    scene_id = plan["scene_id"]
    title = plan.get("title", f"Scene {scene_id}")
    anchor_example = plan.get("anchor_example", "")
    learning_goal = plan.get("learning_goal", "")
    events = plan.get("events", [])
    phrases = [ev["anchor_phrase"] for ev in events if ev.get("anchor_phrase", "").strip()]
    seen: set[str] = set()
    unique_phrases: list[str] = []
    for p in phrases:
        if p.lower() not in seen:
            seen.add(p.lower())
            unique_phrases.append(p)

    # Fallback if profile normalization/pacing helpers are absent.
    # Determine TTS speed from provided learner profile (if present).
    tts_speed = 1.0
    if learner_profile and isinstance(learner_profile, dict):
        ped = learner_profile.get("pedagogical_profile") or {}
        try:
            tts_speed = float(ped.get("tts_speed", 1.0))
        except Exception:
            tts_speed = 1.0

    # Base target word counts; faster TTS -> fewer words per scene.
    base_lo, base_hi = 35, 60
    word_lo = max(15, int(base_lo / tts_speed))
    word_hi = max(word_lo + 10, int(base_hi / tts_speed))

    learner_context = plan.get("_learner_context") or format_learner_context(
        learner_profile, topic or title, subject
    )

    if not unique_phrases:
        logger.warning("Scene %d has no anchor phrases; generating free narration", scene_id)
        return _generate_free(
            title, anchor_example, learning_goal, scene_id,
            learner_context=learner_context, word_lo=word_lo, word_hi=word_hi,
        )

    client = NvidiaClient()
    phrases_display = "\n".join(f'  "{p}"' for p in unique_phrases)
    prompt = NARRATION_PROMPT.format(
        learner_context=learner_context,
        title=title,
        anchor_example=anchor_example,
        learning_goal=learning_goal,
        phrases=phrases_display,
        word_lo=word_lo,
        word_hi=word_hi,
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
            word_lo=word_lo,
            word_hi=word_hi,
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


import concurrent.futures

def write_all_narrations(
    plans: list[dict[str, Any]],
    learner_profile: dict[str, Any] | None = None,
    topic: str = "",
    subject: str = "Physics",
) -> list[dict[str, Any]]:
    """Write narrations for all plans and attach them in-place."""
    def process_plan(plan):
        narration = write_narration(
            plan, learner_profile=learner_profile, topic=topic, subject=subject
        )
        plan["narration"] = narration
        logger.info(
            "Narration for scene %d (%d words): %s…",
            plan["scene_id"],
            len(narration.split()),
            narration[:50],
        )
        return plan

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_plan, plan) for plan in plans]
        return [f.result() for f in futures]


def _find_missing(narration: str, phrases: list[str]) -> list[str]:
    """Return any phrases that are NOT verbatim substrings of the narration."""
    lower = narration.lower()
    return [p for p in phrases if p.lower() not in lower]


def _generate_free(
    title: str,
    anchor: str,
    goal: str,
    scene_id: int,
    learner_context: str = "",
    word_lo: int = 40,
    word_hi: int = 60,
) -> str:
    """Fallback: generate narration without phrase constraints."""
    client = NvidiaClient()
    prompt = (
        f"{learner_context}\n\n"
        f"Write a {word_lo}-{word_hi} word educational narration for: {title}. "
        f"Anchor example: {anchor}. Goal: {goal}. "
        "Make it unique to this scene; do not repeat phrasing from other scenes."
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
