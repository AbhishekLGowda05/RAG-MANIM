"""Concept template registry for educational Manim scene generation."""
from __future__ import annotations

from modules.templates.mechanics.intro import IntroTemplate
from modules.templates.mechanics.inertia import InertiaTemplate
from modules.templates.mechanics.force import ForceTemplate
from modules.templates.mechanics.acceleration import AccelerationTemplate
from modules.templates.mechanics.friction import FrictionTemplate
from modules.templates.mechanics.projectile import ProjectileTemplate
from modules.templates.mechanics.inclined_plane import InclinedPlaneTemplate
from modules.templates.mechanics.summary import SummaryTemplate

TEMPLATES: dict[str, type] = {
    "intro": IntroTemplate,
    "inertia": InertiaTemplate,
    "force": ForceTemplate,
    "acceleration": AccelerationTemplate,
    "friction": FrictionTemplate,
    "projectile": ProjectileTemplate,
    "inclined_plane": InclinedPlaneTemplate,
    "summary": SummaryTemplate,
}

VALID_TEMPLATE_IDS: list[str] = sorted(TEMPLATES)

__all__ = ["TEMPLATES", "VALID_TEMPLATE_IDS"]
