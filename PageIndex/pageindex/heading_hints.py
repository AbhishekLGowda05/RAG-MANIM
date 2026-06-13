"""Tunable heading-detection hints for subsection extraction."""

from __future__ import annotations

# Recall boost: candidate containing any of these (case-insensitive) is heading-likely.
SCIENCE_HEADING_HINTS = frozenset({
    "model", "law", "experiment", "experiments", "rays", "reaction", "reactions",
    "bonding", "number", "configuration", "isotope", "isotopes", "isobars", "isotones",
    "valency", "oxidation", "reduction", "redox", "periodic", "atom", "electron",
    "proton", "neutron", "nucleus", "orbit", "shell", "radioactivity", "discovery",
    "discharge", "cathode", "anode", "molecule", "compound", "element",
})

# Reject list: lines starting with these are body/questions/captions, not headings.
JUNK_STARTERS = frozenset({
    "fig", "figure", "table", "let", "note", "activity", "analyse", "analyze",
    "complete", "write", "find", "what", "how", "why", "which", "draw", "select",
    "match", "prepare", "list", "observe", "calculate", "the", "a", "an", "in", "on",
    "see", "you", "hey", "yes", "then", "when", "if", "can", "are", "is", "was",
    "element", "compound", "cation", "anion",
})

CONTINUATION_WORDS = frozenset({"of", "and", "in", "the", "for", "with", "to", "from", "on"})

# Single-word headings allowed when in this set (e.g. Isotopes, Isobars).
SINGLE_WORD_HEADINGS = frozenset({
    "isotopes", "isobars", "isotones", "radioactivity",
})
