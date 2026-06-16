import re
from typing import Dict, Any, List

def _flesch_kincaid(text: str) -> float:
    """Calculate Flesch-Kincaid grade level."""
    sentences = len(re.findall(r'[.!?]+', text)) or 1
    words = len(text.split()) or 1
    syllables = sum(max(1, len(re.findall(r'[aeiouyAEIOUY]+', word))) for word in text.split())
    
    score = 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
    return max(0.0, score)

def compute_content_difficulty(retrieved_context: Dict[str, Any], topic: str) -> float:
    """
    Compute beta difficulty score from retrieved content.
    beta = 0.4 * CD_norm + 0.35 * DD_norm + 0.25 * SC_norm
    """
    nodes = retrieved_context.get("nodes", [])
    if not nodes:
        return 0.5 # Default medium difficulty
        
    # Concept Density (CD) - proxy: words > 6 letters per sentence
    total_text = " ".join([n.get("summary", "") for n in nodes])
    sentences = max(1, len(re.findall(r'[.!?]+', total_text)))
    complex_words = len([w for w in total_text.split() if len(w) > 6])
    cd = complex_words / sentences
    cd_norm = min(1.0, cd / 5.0) # Assume 5 complex words per sentence is max density
    
    # Dependency Depth (DD)
    prereqs = retrieved_context.get("prerequisites", [])
    dd = 2 if prereqs else 1 # Simplified depth estimation
    dd_norm = dd / 3.0 # Max depth 3
    
    # Summary Complexity (SC)
    sc = _flesch_kincaid(total_text)
    sc_norm = min(1.0, max(0.0, (sc - 5) / 10.0)) # Normalize grade 5-15 to 0-1
    
    beta = 0.4 * cd_norm + 0.35 * dd_norm + 0.25 * sc_norm
    return round(beta, 2)

def compute_scaffolding(beta: float, theta: float) -> Dict[str, Any]:
    """
    Determine scaffolding strategy based on delta gap.
    delta = beta - theta
    """
    delta = beta - theta
    
    if delta < -0.2:
        level = "minimal"
        scene_count = 3
        analogies = 0
        prereq_review = "Not required"
    elif -0.2 <= delta < 0.1:
        level = "light"
        scene_count = 4
        analogies = 1
        prereq_review = "Optional"
    elif 0.1 <= delta < 0.3:
        level = "moderate"
        scene_count = 6
        analogies = 2
        prereq_review = "Required"
    elif 0.3 <= delta < 0.5:
        level = "heavy"
        scene_count = 8
        analogies = 3
        prereq_review = "Required with expansion"
    else:
        level = "intensive"
        scene_count = 10
        analogies = 4
        prereq_review = "Required with worked examples"
        
    # Complexity ceiling: for concepts with beta below 0.3, cap scene count at 4
    if beta < 0.3:
        scene_count = min(scene_count, 4)
        
    return {
        "delta": round(delta, 2),
        "scaffolding_level": level,
        "scene_count": scene_count,
        "analogies": analogies,
        "prerequisite_review": prereq_review
    }

def format_pedagogical_context(scaffolding: Dict[str, Any]) -> str:
    """Format the scaffolding decisions into a prompt block for the LLM."""
    return f"""
PEDAGOGICAL STRATEGY:
- Scaffolding Level: {scaffolding['scaffolding_level'].upper()}
- Target Scene Count: {scaffolding['scene_count']} scenes
- Required Analogies: {scaffolding['analogies']}
- Prerequisite Review: {scaffolding['prerequisite_review']}
"""
