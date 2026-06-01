"""Concept template registry for educational Manim scene generation."""
from __future__ import annotations

from modules.templates.mechanics.intro import IntroTemplate
from modules.templates.mechanics.inertia import InertiaTemplate
from modules.templates.mechanics.force import ForceTemplate
from modules.templates.mechanics.acceleration import AccelerationTemplate
from modules.templates.mechanics.friction import FrictionTemplate
from modules.templates.mechanics.projectile import ProjectileTemplate
from modules.templates.mechanics.inclined_plane import InclinedPlaneTemplate
from modules.templates.mechanics.magnetism import MagnetismTemplate
from modules.templates.mechanics.circular_motion import CircularMotionTemplate
from modules.templates.mechanics.gravitation import GravitationTemplate
from modules.templates.mechanics.momentum import MomentumTemplate
from modules.templates.mechanics.free_fall import FreeFallTemplate
from modules.templates.mechanics.shm import SimpleHarmonicMotionTemplate
from modules.templates.mechanics.torque import TorqueTemplate
from modules.templates.mechanics.work_energy import WorkEnergyTemplate
from modules.templates.mechanics.summary import SummaryTemplate
from modules.templates.freeform import FreeformTemplate

TEMPLATES: dict[str, type] = {
    "intro": IntroTemplate,
    "inertia": InertiaTemplate,
    "force": ForceTemplate,
    "acceleration": AccelerationTemplate,
    "friction": FrictionTemplate,
    "projectile": ProjectileTemplate,
    "inclined_plane": InclinedPlaneTemplate,
    "magnetism": MagnetismTemplate,
    "circular_motion": CircularMotionTemplate,
    "gravitation": GravitationTemplate,
    "momentum": MomentumTemplate,
    "free_fall": FreeFallTemplate,
    "shm": SimpleHarmonicMotionTemplate,
    "torque": TorqueTemplate,
    "work_energy": WorkEnergyTemplate,
    "freeform": FreeformTemplate,
    "summary": SummaryTemplate,
}

VALID_TEMPLATE_IDS: list[str] = sorted(TEMPLATES)

__all__ = ["TEMPLATES", "VALID_TEMPLATE_IDS"]
