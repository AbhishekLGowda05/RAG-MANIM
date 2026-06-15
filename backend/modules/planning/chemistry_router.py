"""Chemistry template router.

Maps a storyboard scene's (topic, scene_role, semantic_tags, visualizable_elements)
to the most appropriate chemistry template ID.

Called from storyboard._validate_entry to override generic explain/freeform
templates when the topic and retrieved section metadata indicate a chemistry domain.
"""
from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Domain keyword sets
# ---------------------------------------------------------------------------

_ATOMIC_KEYWORDS = frozenset({
    "atom", "atomic", "bohr", "rutherford", "thomson", "electron",
    "proton", "neutron", "nucleus", "discharge", "cathode", "canal",
    "plum pudding", "scattering", "shell", "orbit", "subatomic",
    "dalton", "chadwick", "goldstein", "millikan",
})

_ELECTRON_CONFIG_KEYWORDS = frozenset({
    "electron configuration", "electronic configuration", "aufbau",
    "pauli", "hund", "orbital", "subshell", "valence", "configuration",
    "atomic number", "mass number", "isotope", "isobar",
})

_PERIODIC_KEYWORDS = frozenset({
    "periodic", "period", "group", "electronegativity", "ionization",
    "ionisation", "atomic radius", "periodic table", "mendeleev",
    "moseley", "trend", "shielding", "effective nuclear",
})

_BONDING_KEYWORDS = frozenset({
    "ionic", "covalent", "bond", "bonding", "electronegativity",
    "electron pair", "lewis", "dot structure", "octet",
})

_IONIC_KEYWORDS = frozenset({
    "ionic", "ion", "cation", "anion", "lattice", "electrostatic",
    "transfer", "nacl", "sodium chloride",
})

_COVALENT_KEYWORDS = frozenset({
    "covalent", "shared", "sharing", "molecule", "h2o", "co2",
    "water", "carbon dioxide", "double bond", "triple bond",
})

_REDOX_KEYWORDS = frozenset({
    "redox", "oxidation", "reduction", "oxidizing", "reducing",
    "electron transfer", "ox", "red", "half reaction", "oxidation state",
    "oxidation number",
})

_EQUILIBRIUM_KEYWORDS = frozenset({
    "equilibrium", "reversible", "le chatelier", "kc", "kp",
    "dynamic equilibrium",
})

_ACID_BASE_KEYWORDS = frozenset({
    "acid", "base", "ph", "neutralisation", "neutralization",
    "proton donor", "bronsted", "lowry", "arrhenius",
})

_ENERGY_KEYWORDS = frozenset({
    "enthalpy", "exothermic", "endothermic", "activation energy",
    "reaction energy", "hess", "bond energy",
})

_GEOMETRY_KEYWORDS = frozenset({
    "molecular geometry", "vsepr", "shape", "linear", "tetrahedral",
    "bent", "trigonal", "molecular structure",
})

# ---------------------------------------------------------------------------
# Tag-to-template mapping (highest priority — explicit tags)
# ---------------------------------------------------------------------------

_TAG_TO_TEMPLATE: dict[str, str] = {
    "atomic-structure":       "atomic_structure",
    "nuclear-model":          "atomic_structure",
    "electron-configuration": "atomic_structure",
    "periodic-table":         "periodic_trends",
    "ionic-bonding":          "ionic_bonding",    # more specific than chemical-bonding
    "covalent-bonding":       "covalent_bonding", # more specific than chemical-bonding
    "chemical-bonding":       "covalent_bonding", # generic bonding defaults to covalent
    "redox":                  "redox_transfer",
    "acid-base":              "acid_base",
    "chemical-equilibrium":   "chemical_equilibrium",
    "reaction-energy":        "reaction_energy",
    "molecular-geometry":     "molecular_geometry",
}

# Priority ordering for tag matching — more specific tags take precedence.
_TAG_PRIORITY_ORDER = [
    "ionic-bonding", "covalent-bonding", "atomic-structure", "nuclear-model",
    "electron-configuration", "periodic-table", "redox", "acid-base",
    "chemical-equilibrium", "reaction-energy", "molecular-geometry",
    "chemical-bonding",  # least specific bonding tag — checked last
]

# ---------------------------------------------------------------------------
# scene_role → template preference lists (used as tie-breakers)
# ---------------------------------------------------------------------------

_ROLE_PREFERENCE: dict[str, list[str]] = {
    "hook":            ["atomic_structure", "rutherford_gold_foil", "periodic_trends"],
    "visual_intuition":["atomic_structure", "ionic_bonding", "covalent_bonding", "periodic_trends"],
    "formal_concept":  ["atomic_structure", "periodic_trends", "ionic_bonding", "covalent_bonding"],
    "worked_example":  ["redox_transfer", "acid_base", "chemical_equilibrium", "reaction_energy"],
    "summary":         ["atomic_structure"],
}

# All valid chemistry template IDs (must match templates/__init__.py keys)
CHEMISTRY_TEMPLATE_IDS = [
    "atomic_structure",
    "periodic_trends",
    "ionic_bonding",
    "covalent_bonding",
    "molecular_geometry",
    "chemical_equilibrium",
    "acid_base",
    "reaction_energy",
]


def route_chemistry_template(
    topic: str,
    scene_role: str,
    semantic_tags: list[str],
    visualizable_elements: list[str],
) -> Optional[str]:
    """Return the best chemistry template ID, or None if topic is not chemistry.

    Priority:
      1. Explicit semantic_tag match (strongest signal from indexer)
      2. visualizable_elements keyword match
      3. Topic keyword domain detection
      4. scene_role preference within the matched domain
    """
    topic_lower = topic.lower()
    tags_lower = [t.lower() for t in semantic_tags]
    vis_lower = [v.lower() for v in visualizable_elements]
    combined = topic_lower + " " + " ".join(tags_lower) + " " + " ".join(vis_lower)

    # 1. Explicit tag override — use priority order (specific before generic)
    for priority_tag in _TAG_PRIORITY_ORDER:
        if priority_tag in tags_lower:
            return _TAG_TO_TEMPLATE[priority_tag]

    # 2. Visualizable elements signal atomic structure
    atomic_vis = {"discharge tube", "plum pudding model", "gold foil experiment",
                  "bohr atom orbits", "bohr model", "rutherford"}
    if any(any(av in ve for av in atomic_vis) for ve in vis_lower):
        return "atomic_structure"

    def _kw_match(keyword_set: frozenset, text: str) -> bool:
        """Word-boundary match any keyword from a set against text."""
        for kw in keyword_set:
            if re.search(r"\b" + re.escape(kw) + r"\b", text):
                return True
        return False

    # 3. Keyword domain detection with scene_role preference
    if _kw_match(_ELECTRON_CONFIG_KEYWORDS, combined):
        return "atomic_structure"

    if _kw_match(_ATOMIC_KEYWORDS, combined):
        prefs = _ROLE_PREFERENCE.get(scene_role, [])
        for p in prefs:
            if p == "atomic_structure":
                return p
        return "atomic_structure"

    if _kw_match(_REDOX_KEYWORDS, combined):
        return "redox_transfer"

    if _kw_match(_IONIC_KEYWORDS, combined):
        return "ionic_bonding"

    if _kw_match(_COVALENT_KEYWORDS, combined):
        return "covalent_bonding"

    if _kw_match(_BONDING_KEYWORDS, combined):
        if scene_role in ("visual_intuition", "hook"):
            return "ionic_bonding"
        return "covalent_bonding"

    if _kw_match(_PERIODIC_KEYWORDS, combined):
        return "periodic_trends"

    if _kw_match(_ACID_BASE_KEYWORDS, combined):
        return "acid_base"

    if _kw_match(_EQUILIBRIUM_KEYWORDS, combined):
        return "chemical_equilibrium"

    if _kw_match(_ENERGY_KEYWORDS, combined):
        return "reaction_energy"

    if _kw_match(_GEOMETRY_KEYWORDS, combined):
        return "molecular_geometry"

    return None


def is_chemistry_topic(
    topic: str,
    semantic_tags: list[str],
    visualizable_elements: list[str],
) -> bool:
    """Return True if the topic and retrieved metadata indicate a chemistry domain."""
    return route_chemistry_template(topic, "formal_concept", semantic_tags, visualizable_elements) is not None
