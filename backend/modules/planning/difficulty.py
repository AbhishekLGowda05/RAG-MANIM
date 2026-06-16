import re
import json
import logging
from typing import Dict, Any, List
from modules.config import NVIDIA_PLANNER_MODEL
from modules.llm.nvidia_client import NvidiaClient

logger = logging.getLogger("difficulty")

def estimate_node_difficulty(node: Dict[str, Any], prerequisites: List[str] = None) -> float:
    """
    Rule-based fallback to estimate node difficulty between -2.0 and 2.0.
    Based on:
    - Title complexity
    - Word counts
    - Prerequisite count
    """
    difficulty = 0.0
    
    # Rule 1: Prerequisite count (more prereqs = harder)
    if prerequisites:
        difficulty += len(prerequisites) * 0.4
        
    # Rule 2: Title keywords complexity
    title_lower = node.get("title", "").lower()
    advanced_keywords = [
        "quantum", "relativity", "maxwell", "lorentz", "schrodinger", "derivative", 
        "integral", "calculus", "electromagnetic induction", "organic", "thermodynamics"
    ]
    easy_keywords = [
        "intro", "what is", "basic", "simple", "speed", "matter", "magnet", "force", 
        "light", "fraction", "perimeter"
    ]
    
    for kw in advanced_keywords:
        if kw in title_lower:
            difficulty += 0.8
    for kw in easy_keywords:
        if kw in title_lower:
            difficulty -= 0.8
            
    # Rule 3: Text length / content complexity proxy
    summary = node.get("summary", "") or node.get("content", "")
    if summary:
        words = summary.split()
        if len(words) > 100:
            difficulty += 0.2
        # Complex words count
        complex_words = len([w for w in words if len(w) > 8])
        if complex_words > 10:
            difficulty += 0.3
            
    # Clamp to [-2.0, 2.0]
    return max(min(difficulty, 2.0), -2.0)

def classify_node_difficulty_llm(node: Dict[str, Any], prerequisites: List[str] = None) -> float:
    """Use Nvidia planner LLM to classify a node's difficulty on the IRT theta scale [-2.0, 2.0]."""
    client = NvidiaClient()
    
    node_info = {
        "title": node.get("title", ""),
        "summary": node.get("summary", "") or node.get("content", "")[:300],
        "prerequisites": prerequisites or []
    }
    
    prompt = f"""
    Given the following curriculum section, classify its conceptual difficulty on a scale from -2.0 (very basic/elementary) to +2.0 (highly advanced/university level).
    
    Concept:
    {json.dumps(node_info, indent=2)}
    
    Respond with ONLY a valid JSON object containing a single key "difficulty" mapping to a float between -2.0 and 2.0. Do not write markdown fences.
    """
    
    messages = [
        {"role": "system", "content": "You are an expert NCERT/CBSE curriculum analyst. Respond only in JSON."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        res = client.chat_json(NVIDIA_PLANNER_MODEL, messages, temperature=0.1, max_tokens=100)
        diff = float(res.get("difficulty", 0.0))
        return max(min(diff, 2.0), -2.0)
    except Exception as e:
        logger.warning(f"Failed to classify difficulty via LLM: {e}. Falling back to rule-based.")
        return estimate_node_difficulty(node, prerequisites)

def get_node_difficulty(node: Dict[str, Any], prerequisites: List[str] = None, use_llm: bool = False) -> float:
    """Get node difficulty. Uses heuristics by default, optionally calls LLM."""
    if use_llm:
        return classify_node_difficulty_llm(node, prerequisites)
    return estimate_node_difficulty(node, prerequisites)
