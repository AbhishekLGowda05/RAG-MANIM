"""Chemistry template registry.

All templates in this package generate Manim scenes appropriate for
SCERT Kerala Class 10 Chemistry topics (atomic structure, periodic table,
chemical bonding, redox reactions, acid-base, equilibrium, reaction energy).

Visual rules enforced by every template in this package:
  - Subatomic particles are ALWAYS rendered as Dot (never Rectangle or Square).
  - Electron shells are ALWAYS concentric Circle objects.
  - Electron transfer uses MoveAlongPath or ArcBetweenPoints.
  - event.start values from the sync engine are consumed to synchronize
    visual beats with narration anchor phrases.
"""
from __future__ import annotations

from modules.templates.chemistry.atomic_structure import AtomicStructureTemplate
from modules.templates.chemistry.periodic_trends import PeriodicTrendsTemplate
from modules.templates.chemistry.ionic_bonding import IonicBondingTemplate
from modules.templates.chemistry.covalent_bonding import CovalentBondingTemplate
from modules.templates.chemistry.molecular_geometry import MolecularGeometryTemplate
from modules.templates.chemistry.chemical_equilibrium import ChemicalEquilibriumTemplate
from modules.templates.chemistry.acid_base import AcidBaseTemplate
from modules.templates.chemistry.reaction_energy import ReactionEnergyTemplate

CHEMISTRY_TEMPLATE_IDS: list[str] = [
    "atomic_structure",
    "periodic_trends",
    "ionic_bonding",
    "covalent_bonding",
    "molecular_geometry",
    "chemical_equilibrium",
    "acid_base",
    "reaction_energy",
]

CHEMISTRY_TEMPLATES: dict[str, type] = {
    "atomic_structure":    AtomicStructureTemplate,
    "periodic_trends":     PeriodicTrendsTemplate,
    "ionic_bonding":       IonicBondingTemplate,
    "covalent_bonding":    CovalentBondingTemplate,
    "molecular_geometry":  MolecularGeometryTemplate,
    "chemical_equilibrium": ChemicalEquilibriumTemplate,
    "acid_base":           AcidBaseTemplate,
    "reaction_energy":     ReactionEnergyTemplate,
}

__all__ = [
    "CHEMISTRY_TEMPLATE_IDS",
    "CHEMISTRY_TEMPLATES",
    "AtomicStructureTemplate",
    "PeriodicTrendsTemplate",
    "IonicBondingTemplate",
    "CovalentBondingTemplate",
    "MolecularGeometryTemplate",
    "ChemicalEquilibriumTemplate",
    "AcidBaseTemplate",
    "ReactionEnergyTemplate",
]
