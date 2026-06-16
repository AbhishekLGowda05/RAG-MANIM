import math
from typing import List, Dict, Any, Tuple
from .item_bank import get_item, get_items_by_subject

def probability(theta: float, a: float, b: float) -> float:
    """Calculate probability of correct response under 2PL IRT model."""
    # To prevent overflow
    try:
        exp_val = math.exp(-a * (theta - b))
        return 1.0 / (1.0 + exp_val)
    except OverflowError:
        return 0.0 if -a * (theta - b) > 0 else 1.0

def fisher_information(theta: float, a: float, b: float) -> float:
    """Calculate Fisher information of an item at a given theta."""
    p = probability(theta, a, b)
    return (a ** 2) * p * (1 - p)

def estimate_theta(responses: List[Dict[str, Any]], prior_mean: float = 0.0, prior_sigma: float = 1.0) -> float:
    """
    Estimate theta using Maximum a Posteriori (MAP) inference.
    responses: list of dicts with 'item_id' and 'is_correct' (1 or 0)
    """
    if not responses:
        return prior_mean
        
    theta = prior_mean
    learning_rate = 0.1
    max_iter = 100
    convergence_threshold = 1e-4
    
    for _ in range(max_iter):
        gradient = -theta / (prior_sigma ** 2)
        
        for resp in responses:
            item = get_item(resp["item_id"])
            if not item:
                continue
            a = item.get("a", 1.0)
            b = item.get("b", 0.0)
            r_i = float(resp["is_correct"])
            
            p_i = probability(theta, a, b)
            gradient += a * (r_i - p_i)
            
        theta = theta + learning_rate * gradient
        if abs(gradient) < convergence_threshold:
            break
            
    # Clamp theta to reasonable bounds [-4, 4]
    return max(min(theta, 4.0), -4.0)

def select_next_item(current_theta: float, answered_ids: List[str], subject: str = "") -> Dict[str, Any]:
    """
    Adaptively select the next question using maximum Fisher information criterion.
    """
    available_items = get_items_by_subject(subject)
    unanswered_items = [item for item in available_items if item["item_id"] not in answered_ids]
    
    if not unanswered_items:
        return {}
        
    best_item = None
    max_info = -1.0
    
    for item in unanswered_items:
        info = fisher_information(current_theta, item.get("a", 1.0), item.get("b", 0.0))
        if info > max_info:
            max_info = info
            best_item = item
            
    return best_item
