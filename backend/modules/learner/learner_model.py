import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from .pedagogical_profile import build_pedagogical_profile

@dataclass
class LearnerModel:
    learner_id: str
    grade: int
    theta: Optional[float]
    confidence: Dict[str, int]
    cognitive_profile: Dict[str, Any]
    pedagogical_profile: Dict[str, Any]
    mastery_map: Dict[str, Any]
    metadata: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LearnerModel':
        # Derive grade from academic_level if not present
        academic_level = data.get("academic_level", "class_11")
        grade = data.get("grade")
        if grade is None:
            grade_map = {
                "class_5": 5,
                "class_9": 9,
                "class_10": 10,
                "class_11": 11,
                "class_12": 12,
                "undergraduate": 15,
                "competitive": 12
            }
            grade = grade_map.get(academic_level, 11)

        # Build cognitive profile
        cog = data.get("cognitive_profile") or {
            "learning_style": data.get("learning_style", "visual"),
            "pace_preference": data.get("pace_preference", "balanced")
        }

        # Retrieve theta
        theta = data.get("theta")

        # Build pedagogical profile
        ped = build_pedagogical_profile(theta)

        return cls(
            learner_id=data.get("learner_id", "guest"),
            grade=int(grade),
            theta=theta if theta is not None else None,
            confidence=data.get("confidence_map", {}),
            cognitive_profile=cog,
            pedagogical_profile=ped,
            mastery_map=data.get("mastery_map", {}),
            metadata=data.get("metadata") or {
                "name": data.get("name", "Learner"),
                "academic_level": academic_level,
                "exam_target": data.get("exam_target", []),
                "weak_subjects": data.get("weak_subjects", [])
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Flatten back to compatible profile.json structure for frontend
        d["name"] = self.metadata.get("name", "Learner")
        d["academic_level"] = self.metadata.get("academic_level", f"class_{self.grade}")
        d["exam_target"] = self.metadata.get("exam_target", [])
        d["learning_style"] = self.cognitive_profile.get("learning_style", "visual")
        d["pace_preference"] = self.cognitive_profile.get("pace_preference", "balanced")
        d["weak_subjects"] = self.metadata.get("weak_subjects", [])
        d["confidence_map"] = self.confidence
        return d
