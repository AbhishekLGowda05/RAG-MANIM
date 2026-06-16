from typing import Any, Dict, Optional

def build_pedagogical_profile(theta: Optional[float]) -> Dict[str, Any]:
    """
    Map ability estimate theta to derived pedagogical constraints.
    personalization = Ability (theta) NOT Grade.
    """
    if theta is None:
        theta = 0.0 # Default starting ability

    if theta < -1.0:
        return {
            "vocabulary": "simple",
            "scene_count": 7,
            "scaffolding": "high",
            "tts_speed": 0.85,
            "equations": False,
            "analogy_first": True,
            "example_type": "daily_life",
            "visual_density": "simple" # simple: 2 objects, bright colors, large labels, slow transitions
        }
    elif theta > 1.0:
        return {
            "vocabulary": "advanced",
            "scene_count": 4,
            "scaffolding": "minimal",
            "tts_speed": 1.15,
            "equations": True,
            "analogy_first": False,
            "example_type": "technical",
            "visual_density": "complex" # complex: 8 objects, neutral colors, compact labels, faster transitions
        }
    else:
        # -1.0 <= theta <= 1.0
        return {
            "vocabulary": "standard",
            "scene_count": 5,
            "scaffolding": "moderate",
            "tts_speed": 1.0,
            "equations": True,
            "analogy_first": True,
            "example_type": "standard",
            "visual_density": "moderate" # moderate: 4-5 objects, balanced colors
        }
