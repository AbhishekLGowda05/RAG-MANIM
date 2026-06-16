from typing import List, Dict, Any

# A small pre-seeded item bank with 2PL IRT parameters
# a: discrimination, b: difficulty
ITEM_BANK: List[Dict[str, Any]] = [
    # Physics
    {"item_id": "PHY9_001", "concept": "Motion", "a": 1.23, "b": -1.42, "type": "Recall",
     "question": "What is the physical quantity that indicates the rate of change of displacement?",
     "options": ["Speed", "Velocity", "Acceleration", "Distance"], "answer": "Velocity"},
    {"item_id": "PHY9_002", "concept": "Velocity", "a": 1.41, "b": -0.87, "type": "Comprehension",
     "question": "If an object moves in a circular path with constant speed, its velocity is:",
     "options": ["Constant", "Zero", "Changing", "Infinite"], "answer": "Changing"},
    {"item_id": "PHY9_003", "concept": "Acceleration", "a": 1.38, "b": -0.31, "type": "Application",
     "question": "A car accelerates from rest to 20 m/s in 5 seconds. What is its acceleration?",
     "options": ["2 m/s²", "4 m/s²", "10 m/s²", "100 m/s²"], "answer": "4 m/s²"},
    {"item_id": "PHY9_042", "concept": "Oscillation", "a": 1.29, "b": 0.54, "type": "Comprehension",
     "question": "The restoring force in a simple pendulum is provided by:",
     "options": ["Tension in string", "Component of gravity", "Air resistance", "Mass of the bob"], "answer": "Component of gravity"},
    {"item_id": "PHY9_043", "concept": "Periodic Motion", "a": 1.44, "b": 0.71, "type": "Application",
     "question": "Which of the following is an example of periodic motion but not simple harmonic motion?",
     "options": ["A playground swing", "A bouncing ball", "A bouncing spring", "Motion of planets around the sun"], "answer": "Motion of planets around the sun"},
    {"item_id": "PHY9_067", "concept": "Simple Harmonic Motion", "a": 1.51, "b": 1.23, "type": "Application",
     "question": "In SHM, the acceleration is proportional to and opposite in direction to the:",
     "options": ["Velocity", "Displacement", "Mass", "Force"], "answer": "Displacement"},
    {"item_id": "PHY9_072", "concept": "Resonance", "a": 1.19, "b": 1.67, "type": "Comprehension",
     "question": "When the frequency of an external periodic force matches the natural frequency of a system, it causes:",
     "options": ["Damping", "Resonance", "Diffraction", "Refraction"], "answer": "Resonance"},
    {"item_id": "PHY9_080", "concept": "Newton's First Law", "a": 1.30, "b": -1.10, "type": "Recall",
     "question": "The property of a body to resist a change in its state of rest or uniform motion is called:",
     "options": ["Force", "Momentum", "Inertia", "Energy"], "answer": "Inertia"},
    {"item_id": "PHY9_085", "concept": "Newton's Second Law", "a": 1.45, "b": 0.10, "type": "Application",
     "question": "A force of 10 N acts on a mass of 2 kg. What is the acceleration produced?",
     "options": ["20 m/s²", "5 m/s²", "12 m/s²", "0.2 m/s²"], "answer": "5 m/s²"},
    {"item_id": "PHY9_090", "concept": "Newton's Third Law", "a": 1.10, "b": -0.50, "type": "Comprehension",
     "question": "Action and reaction forces act on:",
     "options": ["The same body", "Different bodies", "The ground", "Nothing"], "answer": "Different bodies"},

    # Chemistry
    {"item_id": "CHM9_001", "concept": "Matter", "a": 1.05, "b": -1.50, "type": "Recall",
     "question": "Which state of matter has a definite volume but no definite shape?",
     "options": ["Solid", "Liquid", "Gas", "Plasma"], "answer": "Liquid"},
    {"item_id": "CHM9_010", "concept": "Atomic Structure", "a": 1.20, "b": -0.20, "type": "Recall",
     "question": "The nucleus of an atom consists of:",
     "options": ["Electrons and Protons", "Protons and Neutrons", "Electrons and Neutrons", "Only Protons"], "answer": "Protons and Neutrons"},
    {"item_id": "CHM9_020", "concept": "Isotopes", "a": 1.35, "b": 0.80, "type": "Comprehension",
     "question": "Isotopes of an element have the same number of protons but different numbers of:",
     "options": ["Electrons", "Neutrons", "Positrons", "Photons"], "answer": "Neutrons"},
    {"item_id": "CHM9_030", "concept": "Chemical Bonding", "a": 1.40, "b": 1.00, "type": "Application",
     "question": "The bond formed by the sharing of electron pairs between atoms is called:",
     "options": ["Ionic bond", "Covalent bond", "Metallic bond", "Hydrogen bond"], "answer": "Covalent bond"},
    {"item_id": "CHM9_040", "concept": "Periodic Table", "a": 1.25, "b": 0.30, "type": "Recall",
     "question": "Elements in the same group of the periodic table have the same number of:",
     "options": ["Protons", "Valence electrons", "Neutrons", "Electron shells"], "answer": "Valence electrons"},

    # Mathematics
    {"item_id": "MAT9_001", "concept": "Number System", "a": 1.15, "b": -1.20, "type": "Recall",
     "question": "Which of the following is an irrational number?",
     "options": ["√4", "1/3", "π", "0.5"], "answer": "π"},
    {"item_id": "MAT9_010", "concept": "Polynomials", "a": 1.30, "b": -0.40, "type": "Application",
     "question": "The degree of the polynomial 4x³ - 2x² + x - 5 is:",
     "options": ["1", "2", "3", "4"], "answer": "3"},
    {"item_id": "MAT9_020", "concept": "Linear Equations", "a": 1.45, "b": 0.20, "type": "Application",
     "question": "The graph of the equation x = 3 is a line parallel to the:",
     "options": ["x-axis", "y-axis", "Both axes", "Neither axis"], "answer": "y-axis"},
    {"item_id": "MAT9_030", "concept": "Triangles", "a": 1.28, "b": 0.60, "type": "Comprehension",
     "question": "The sum of the angles of a triangle is:",
     "options": ["90°", "180°", "270°", "360°"], "answer": "180°"},
    {"item_id": "MAT9_040", "concept": "Probability", "a": 1.35, "b": 0.90, "type": "Application",
     "question": "What is the probability of getting an even number when a single die is rolled?",
     "options": ["1/6", "1/3", "1/2", "2/3"], "answer": "1/2"},
]

def get_item(item_id: str) -> Dict[str, Any]:
    for item in ITEM_BANK:
        if item["item_id"] == item_id:
            return item
    return {}

def get_items_by_subject(subject: str) -> List[Dict[str, Any]]:
    prefix = "PHY" if subject == "Physics" else "CHM" if subject == "Chemistry" else "MAT" if subject == "Mathematics" else ""
    if not prefix:
        return ITEM_BANK
    return [item for item in ITEM_BANK if item["item_id"].startswith(prefix)]
