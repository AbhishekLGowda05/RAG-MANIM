import os
import json
import math
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger("irt_engine")

DIAGNOSTICS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "diagnostics"

def load_question_bank(subject: str) -> List[Dict[str, Any]]:
    """Load diagnostic question bank for the given subject."""
    subject_filename = subject.lower().replace(" ", "_") + ".json"
    file_path = DIAGNOSTICS_DIR / subject_filename
    
    if not file_path.exists():
        logger.warning(f"Question bank file {file_path} not found. Returning empty list.")
        return []
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading question bank {file_path}: {e}")
        return []

def get_item_by_id(item_id: str, subject: str = "") -> Optional[Dict[str, Any]]:
    """Retrieve a specific question by item_id."""
    subjects = [subject] if subject else ["physics", "chemistry", "mathematics"]
    for s in subjects:
        bank = load_question_bank(s)
        for item in bank:
            if item["question_id"] == item_id:
                return item
    return None

def probability(theta: float, a: float, b: float) -> float:
    """Calculate probability of correct response under 2PL IRT model."""
    try:
        exp_val = math.exp(-a * (theta - b))
        return 1.0 / (1.0 + exp_val)
    except OverflowError:
        return 0.0 if -a * (theta - b) > 0 else 1.0

def fisher_information(theta: float, a: float, b: float) -> float:
    """Calculate Fisher information of an item at a given theta."""
    p = probability(theta, a, b)
    return (a ** 2) * p * (1 - p)

def estimate_theta_2pl(responses: List[Dict[str, Any]], subject: str = "") -> float:
    """
    Estimate theta using 2PL Maximum a Posteriori (MAP) inference.
    responses: list of dicts with 'item_id' and 'is_correct' (1 or 0)
    """
    if not responses:
        return 0.0
        
    prior_mean = 0.0
    prior_sigma = 1.0
    theta = prior_mean
    learning_rate = 0.1
    max_iter = 100
    convergence_threshold = 1e-4
    
    for _ in range(max_iter):
        gradient = -theta / (prior_sigma ** 2)
        
        for resp in responses:
            item = get_item_by_id(resp["item_id"], subject)
            if not item:
                continue
            a = item.get("discrimination") or item.get("a") or 1.0
            b = item.get("difficulty") or item.get("b") or 0.0
            r_i = float(resp["is_correct"])
            
            p_i = probability(theta, a, b)
            gradient += a * (r_i - p_i)
            
        theta = theta + learning_rate * gradient
        if abs(gradient) < convergence_threshold:
            break
            
    return max(min(theta, 2.0), -2.0)

def estimate_theta_approximate(responses: List[Dict[str, Any]], subject: str = "") -> float:
    """
    Step 4: Approximate Theta first.
    theta = weighted_correct_answers mapped to -2 -> +2 range.
    easy (difficulty < -0.5) = 1 point
    medium (-0.5 <= difficulty <= 0.5) = 2 points
    hard (difficulty > 0.5) = 3 points
    """
    if not responses:
        return 0.0
        
    total_points = 0
    score = 0
    
    for resp in responses:
        item = get_item_by_id(resp["item_id"], subject)
        if not item:
            continue
        
        diff = item.get("difficulty") or item.get("b") or 0.0
        if diff < -0.5:
            weight = 1
        elif diff <= 0.5:
            weight = 2
        else:
            weight = 3
            
        total_points += weight
        if resp.get("is_correct") == 1:
            score += weight
            
    if total_points == 0:
        return 0.0
        
    ratio = score / total_points
    theta = -2.0 + 4.0 * ratio
    return round(theta, 2)

def estimate_theta(responses: List[Dict[str, Any]], subject: str = "", use_2pl: bool = True) -> float:
    """Wrapper that selects the appropriate estimation method."""
    if use_2pl:
        return estimate_theta_2pl(responses, subject)
    else:
        return estimate_theta_approximate(responses, subject)

def select_next_item(current_theta: float, answered_ids: List[str], subject: str, grade: int) -> Dict[str, Any]:
    """
    Adaptively select the next question using maximum Fisher information, 
    filtered by grade range to show appropriate questions.
    """
    available_items = load_question_bank(subject)
    
    # Filter by answered
    unanswered = [item for item in available_items if item["question_id"] not in answered_ids]
    
    # Filter by grade compatibility if grade range is specified
    grade_compatible = []
    for item in unanswered:
        gr = item.get("grade_range")
        if gr and len(gr) == 2:
            if gr[0] <= grade <= gr[1]:
                grade_compatible.append(item)
        else:
            grade_compatible.append(item)
            
    if not grade_compatible:
        # Fallback to unanswered if no grade-compatible items are left
        grade_compatible = unanswered
        
    if not grade_compatible:
        return {}
        
    best_item = None
    max_info = -1.0
    
    for item in grade_compatible:
        a = item.get("discrimination") or item.get("a") or 1.0
        b = item.get("difficulty") or item.get("b") or 0.0
        info = fisher_information(current_theta, a, b)
        if info > max_info:
            max_info = info
            best_item = item
            
    return best_item or {}
