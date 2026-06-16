"""Storyboard planner: generates the conceptual arc for a topic.

Outputs an ordered list of scenes, each with a concept_template and
anchor_example, forming a progressive educational narrative personalized to student.
"""
from __future__ import annotations

import json
from typing import Any

from modules.config import NVIDIA_PLANNER_MODEL, PATHS, get_logger
from modules.llm.nvidia_client import NvidiaClient
from modules.planning.profile_context import format_learner_context
from modules.learner.learner_model import LearnerModel
from modules.templates import (
    EXPLAIN_TEMPLATE_IDS,
    MECHANICS_TEMPLATE_IDS,
    VALID_TEMPLATE_IDS,
)

logger = get_logger(__name__)

STORYBOARD_SYSTEM = """You are an expert educational video director.
You design progressive lesson arcs that teach a topic through DISTINCT, varied examples.
NEVER include run_time, duration, seconds, or timing fields.
Respond ONLY with a valid JSON array. No markdown fences, no commentary."""

STORYBOARD_PROMPT = """Design a {scene_count}-scene educational video arc for this topic: {topic}

CURRICULUM CONTEXT:
{curriculum_context}

{pedagogical_context}
{higher_grade_directive}

IMPORTANT:
- Use the curriculum context as the PRIMARY source of truth.
- Base scene titles, examples, explanations, formulas, and learning goals on the curriculum context.
- Do not invent concepts that are not supported by the curriculum context.
- If the curriculum context is empty, fall back to general educational knowledge.
{learner_context}

SCENE SEQUENCE & ROLES (Design exactly {scene_count} scenes in this order):
{scene_sequence_instructions}

TEMPLATE FAMILIES — pick the best family per scene:

A) PHYSICS SIMULATION (animated motion on chalkboard) — use when the scene shows a physical
   process, forces, or motion:
   {mechanics_list}

B) CHALKBOARD EXPLANATION (conceptual layouts, no physics assets) — allowed templates:
{allowed_chalkboard_templates}

C) FALLBACK: freeform — only if neither family fits.

Also available: intro (first scene only), summary (last scene only).

REQUIREMENTS:
- First scene: always use "intro" template.
- Last scene: always use "summary" template.
- Middle scenes: choose the template that best matches each scene's role.
- Middle scenes MUST have DIFFERENT concept_templates AND DIFFERENT anchor_examples.
- Each scene's learning_goal must be a unique sentence.
- anchor_example: a concrete real-world object, scenario, or numerical setup.
- subtitle (scene 1 only): short tagline for the intro
- key_term (scene 1 only): the central term to highlight
- summary_points (scene {scene_count} only): list of 3 key takeaways

Return a JSON array of exactly {scene_count} objects matching this structure:
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
    "concept_template": "<one of the allowed templates>",
    "title": "...",
    "anchor_example": "<DISTINCT scenario A>",
    "learning_goal": "<unique goal A>"
  }},
  ...
  {{
    "scene_id": {scene_count},
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
    curriculum_context: str = "",
    learner_profile: dict[str, Any] | None = None,
    subject: str = "Physics",
    scene_count: int = 5,
    pedagogical_context: str = "",
) -> list[dict[str, Any]]:
    """Generate a storyboard arc for the given topic."""
    logger.info("Building storyboard for topic: %s with %d scenes", topic, scene_count)
    client = NvidiaClient()
    
    model = LearnerModel.from_dict(learner_profile or {})
    theta = model.theta if model.theta is not None else 0.0
    grade = model.grade

    # Stage 7: Template Selection Adaptation based on Grade/Standard
    if grade <= 5:
        allowed_chalkboard_templates = (
            "   - concept_card: break a concept into 2-4 labeled parts/cards\n"
            "   - diagram: relationships between parts (nodes in a flow or system)\n"
            "   - timeline: ordered steps, history, or procedure (3-5 labels)\n"
            "   (AVOID using 'equation' or 'comparison' templates for this grade)"
        )
    else:
        allowed_chalkboard_templates = (
            "   - concept_card: break a concept into 2-4 labeled parts/cards\n"
            "   - comparison: contrast two ideas side-by-side (e.g. scalar vs vector)\n"
            "   - equation: present or derive a key formula with a short explanation\n"
            "   - diagram: relationships between parts (nodes in a flow or system)\n"
            "   (AVOID using 'timeline' templates unless representing historical order)"
        )

    # Stage 3: Storyboard Adaptation based on Theta Range and Grade
    if grade >= 7:
        # Higher-grade students: emphasize connections, prerequisites, and forward concepts!
        if theta < -1.0:
            scene_count = 6
            scene_sequence_instructions = (
                "1. Hook & Overview (introduce main topic & key term)\n"
                "2. Prerequisite Concept A (simplify foundational prerequisite concept A)\n"
                "3. Prerequisite Concept B (simplify foundational prerequisite concept B)\n"
                "4. Main Topic Connection (explain how the prerequisites combine into the main topic)\n"
                "5. Forward Concept Preview (introduce a simple forward concept to motivate future learning)\n"
                "6. Summary (recap connections between prerequisites, topic, and future concepts)"
            )
        elif theta > 1.0:
            scene_count = 4
            scene_sequence_instructions = (
                "1. Advanced Hook & Prerequisite Bridge (briefly bridge from prerequisite concepts directly to the formal definition)\n"
                "2. Core Derivation & Mathematical Formalism (isolate equations & variables of the main topic)\n"
                "3. Forward Concepts Projection (explore advanced extensions and next-level forward concepts where this is applied)\n"
                "4. Summary & Concept Synthesis (consolidate prerequisites, main topic, and forward concepts)"
            )
        else:
            scene_count = 5
            scene_sequence_instructions = (
                "1. Hook & Syllabus Connection (connect key term to the course curriculum)\n"
                "2. Prerequisite Concepts Grounding (explain foundational prerequisites and their relation to the topic)\n"
                "3. Main Topic Definition & Formulas (define the core topic in relation to prerequisites)\n"
                "4. Forward Concept Applications (introduce next-level concepts that build upon this topic)\n"
                "5. Summary (recap connections between prerequisites, topic, and future concepts)"
            )
    else:
        # Lower-grade students (Grade < 7)
        if theta < -1.0:
            # High scaffolding sequence (e.g. 7 scenes)
            scene_count = 7
            scene_sequence_instructions = (
                "1. Hook / Intro (introduce key term & hook example)\n"
                "2. Analogy (connect to a common everyday experience)\n"
                "3. Definition (define the core concept simply)\n"
                "4. Example (concrete worked example with real-world objects)\n"
                "5. Activity (interactive conceptual setup/timeline)\n"
                "6. Recap (review main takeaways so far)\n"
                "7. Summary (final summary points)"
            )
        elif theta > 1.0:
            # Low scaffolding / advanced sequence (4 scenes)
            scene_count = 4
            scene_sequence_instructions = (
                "1. Definition (rigorous academic definition and formula)\n"
                "2. Equation / Formal derivation (breakdown of each mathematical term)\n"
                "3. Advanced Example (complex, quantitative or technical application)\n"
                "4. Summary (quick recap of key takeaways)"
            )
        else:
            # Moderate scaffolding / standard sequence (5 scenes)
            scene_count = 5
            scene_sequence_instructions = (
                "1. Hook / Intro (introduce key term & tagline)\n"
                "2. Definition (standard definition & key cards)\n"
                "3. Example (everyday scenario/comparison demonstrating the concept)\n"
                "4. Quantitative Worked Example (simple formula application or equation)\n"
                "5. Summary (final summary points)"
            )

    higher_grade_directive = ""
    if grade >= 7:
        higher_grade_directive = (
            "\nPEDAGOGICAL DIRECTIVE FOR HIGHER GRADE STUDENTS:\n"
            "- Stresses more on how the main topic connects to its PREREQUISITES and FORWARD CONCEPTS instead of just explaining the actual topic in isolation.\n"
            "- Explain concepts by grounding them deeply in prerequisite concepts and showing forward concepts where these are applied."
        )

    mechanics_middle = [
        t for t in MECHANICS_TEMPLATE_IDS if t not in ("intro", "summary")
    ]
    mechanics_list = "\n".join(f"   - {t}" for t in mechanics_middle)
    template_ids = ", ".join(
        mechanics_middle + EXPLAIN_TEMPLATE_IDS + ["freeform"]
    )
    learner_context = format_learner_context(learner_profile, topic, subject)
    
    prompt = STORYBOARD_PROMPT.format(
        topic=topic,
        scene_count=scene_count,
        curriculum_context=curriculum_context,
        pedagogical_context=pedagogical_context,
        higher_grade_directive=higher_grade_directive,
        learner_context=learner_context,
        scene_sequence_instructions=scene_sequence_instructions,
        allowed_chalkboard_templates=allowed_chalkboard_templates,
        mechanics_list=mechanics_list,
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
    """Ensure middle scenes have distinct templates AND distinct anchor examples.

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
