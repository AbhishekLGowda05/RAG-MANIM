"""Learner profile -> prompt-context formatter.

Uses the unified LearnerModel and pedagogical_profile to emit a markdown block
injected into every planning/narration/code LLM call so generation is personalized.
"""
from __future__ import annotations
from typing import Any
from modules.learner.learner_model import LearnerModel

def format_learner_context(
    profile: dict[str, Any] | None,
    topic: str,
    subject: str = "Physics",
) -> str:
    """Return the prompt-injected LEARNER CONTEXT block."""
    if not profile:
        profile = {}
        
    model = LearnerModel.from_dict(profile)
    ped = model.pedagogical_profile
    
    # Vocabulary & Reading Level rules
    if ped["vocabulary"] == "simple":
        vocab_rules = (
            f"- Vocabulary level: simple (appropriate for Grade {model.grade}).\n"
            "- AVOID technical jargon or complex derivations.\n"
            "- Use short sentences and explain terms with simple words.\n"
            "- Use daily-life analogies and real-world objects."
        )
    elif ped["vocabulary"] == "advanced":
        vocab_rules = (
            f"- Vocabulary level: advanced (appropriate for Grade {model.grade}).\n"
            "- Introduce formal scientific/mathematical terminology.\n"
            "- Use textbook definitions and equations where appropriate.\n"
            "- Focus on quantitative explanation."
        )
    else:
        vocab_rules = (
            f"- Vocabulary level: standard (appropriate for Grade {model.grade}).\n"
            "- Explain concepts using balanced, clear textbook terminology.\n"
            "- Introduce key equations alongside intuition."
        )
        
    # Visual Complexity/Density rules (Stage 8)
    if ped["visual_density"] == "simple":
        visual_rules = (
            "- Visual Density: SIMPLE.\n"
            "- Use max 2 objects on screen at a time.\n"
            "- Use bright, high-contrast colors.\n"
            "- Use large labels and slow transitions."
        )
    elif ped["visual_density"] == "complex":
        visual_rules = (
            "- Visual Density: COMPLEX.\n"
            "- Use up to 8 objects/components to show details.\n"
            "- Use neutral, academic colors.\n"
            "- Use compact labels and faster transitions."
        )
    else:
        visual_rules = (
            "- Visual Density: MODERATE.\n"
            "- Use 4-5 objects on screen.\n"
            "- Balanced layout and colors."
        )

    # Cross-subject weakness check
    cm = model.confidence
    weakest_line = ""
    if cm:
        try:
            weakest_subj = min(cm.keys(), key=lambda k: cm.get(k, 50))
            if cm.get(weakest_subj, 50) < 50 and weakest_subj != subject:
                weakest_line = f"\n- Note: Student is weakest in {weakest_subj} ({cm[weakest_subj]}%). Bridge concepts gently if they overlap."
        except Exception:
            pass

    return f"""
LEARNER STATE & PEDAGOGICAL PROFILE:
- Learner Name: {model.metadata.get('name', 'Learner')}
- Target Grade: {model.grade}
- Ability Estimate (Theta): {model.theta if model.theta is not None else 'Default (0.0)'}
- Scaffolding Strategy: {ped['scaffolding'].upper()}
- Narration Pace: {ped['tts_speed']}x speed multiplier
- Analogy First: {ped['analogy_first']}
- Example Type: {ped['example_type']}

VOCABULARY AND STYLE RULES:
{vocab_rules}

VISUAL DESIGN RULES:
{visual_rules}
- Equations allowed: {ped['equations']}{weakest_line}
- NEVER repeat the same anchor example across two scenes. Each scene must teach a DISTINCT facet.
"""
