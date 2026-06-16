import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from modules.planning.difficulty import get_node_difficulty
from modules.planning.prerequisite_planner import get_prerequisite_path

logger = logging.getLogger("hierarchical_retriever")

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "pageindex_workspace"

def get_flat_nodes(document_tree: Any) -> Dict[str, Any]:
    """Helper to convert any document structure (list or nested dict) to a flat dict of node_id -> node_data."""
    nodes_dict = {}
    if not document_tree:
        return {}

    structure = []
    if isinstance(document_tree, dict):
        if "nodes" in document_tree:
            nodes_val = document_tree["nodes"]
            if isinstance(nodes_val, dict):
                return nodes_val
            elif isinstance(nodes_val, list):
                structure = nodes_val
        elif "structure" in document_tree:
            structure = document_tree["structure"]
        else:
            structure = [document_tree]
    elif isinstance(document_tree, list):
        structure = document_tree

    def walk(items):
        for item in items:
            if isinstance(item, dict):
                nid = item.get("node_id") or item.get("id")
                if nid:
                    nodes_dict[str(nid)] = item
                if "nodes" in item and isinstance(item["nodes"], list):
                    walk(item["nodes"])
                elif "structure" in item and isinstance(item["structure"], list):
                    walk(item["structure"])
    walk(structure)
    return nodes_dict

def generate_default_concept_graph(nodes_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a sequential and semantic-overlap based concept graph if missing.
    Matches Section 2.2 model: sequential + semantic overlap.
    """
    sorted_node_ids = sorted(nodes_dict.keys())
    concept_graph = {}
    
    # 1. Sequential dependencies: each page/section depends on the previous one
    for i, nid in enumerate(sorted_node_ids):
        concept_graph[nid] = {
            "prerequisites": [sorted_node_ids[i-1]] if i > 0 else [],
            "confidence": 0.8
        }
        
    # 2. Semantic overlap: if later node shares title keywords with earlier node, link them
    for i, nid_b in enumerate(sorted_node_ids):
        title_b = nodes_dict[nid_b].get("title", "").lower()
        words_b = set([w for w in title_b.split() if len(w) > 4])
        if not words_b:
            continue
            
        for nid_a in sorted_node_ids[:i]:
            title_a = nodes_dict[nid_a].get("title", "").lower()
            words_a = set([w for w in title_a.split() if len(w) > 4])
            
            # If significant keyword overlap in titles, add A as prereq of B
            if words_a.intersection(words_b):
                if nid_a not in concept_graph[nid_b]["prerequisites"]:
                    concept_graph[nid_b]["prerequisites"].append(nid_a)
                    
    return concept_graph

def score_node(node: Dict[str, Any], query_tokens: set, theta: float, concept_graph: Dict[str, Any]) -> float:
    """Score node based on keyword overlap + theta-based difficulty distance boost."""
    text = (node.get("title", "") + " " + node.get("summary", "") + " " + node.get("content", "")).lower()
    text_tokens = set(text.split())
    if not query_tokens:
        return 0.0
        
    overlap = len(query_tokens.intersection(text_tokens))
    keyword_score = overlap / len(query_tokens)
    
    # Personalization: Boost nodes matching student's ability (theta)
    difficulty = get_node_difficulty(node, concept_graph.get(node.get("node_id", ""), {}).get("prerequisites", []))
    diff_distance = abs(difficulty - theta)
    # Distance of 0 gets 1.0 boost factor, distance of 4 (max) gets 0.0 boost factor
    difficulty_boost = max(0.0, 1.0 - (diff_distance / 4.0))
    
    # Final score combines keyword match and difficulty appropriateness
    return keyword_score * (0.7 + 0.3 * difficulty_boost)

def get_forward_concepts(target_node_id: str, concept_graph: Dict[str, Any], limit: int) -> List[str]:
    """Find concepts that have target_node_id as a prerequisite."""
    forward = []
    for nid, data in concept_graph.items():
        if target_node_id in data.get("prerequisites", []):
            forward.append(nid)
            if len(forward) >= limit:
                break
    return forward

def retrieve_personalized(
    query: str,
    document_tree: Dict[str, Any],
    concept_graph: Dict[str, Any],
    grade: int = 11,
    theta: float = 0.0,
    learner_profile: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Personalized Curriculum Retrieval:
    Topic + Learner Model (grade, theta) -> Rank Concepts
    - Ranks concepts based on title keywords & difficulty match.
    - Limits prerequisites and forward concepts depending on student grade.
    - Excludes prerequisites where student confidence is already high (>= 70%).
    """
    nodes_dict = get_flat_nodes(document_tree)
    if not nodes_dict:
        return {"nodes": [], "prerequisites": [], "forward_concepts": []}
        
    if not concept_graph:
        concept_graph = generate_default_concept_graph(nodes_dict)
        
    query_tokens = set(query.lower().split())
    
    scored_nodes = []
    for nid, node_data in nodes_dict.items():
        score = score_node(node_data, query_tokens, theta, concept_graph)
        node_copy = node_data.copy()
        node_copy["node_id"] = nid
        node_copy["id"] = nid
        scored_nodes.append((score, node_copy))
        
    # Sort by score descending
    scored_nodes.sort(key=lambda x: x[0], reverse=True)
    target_node = scored_nodes[0][1] if scored_nodes and scored_nodes[0][0] > 0 else list(nodes_dict.values())[0]
    target_node_id = str(target_node.get("node_id") or target_node.get("id"))
    
    # Grade-based limits (Stage 4)
    if grade <= 5:
        prereq_limit = 1
        forward_limit = 0
    elif grade <= 9:
        prereq_limit = 2
        forward_limit = 1
    else: # grade >= 10
        prereq_limit = 3
        forward_limit = 2
        
    # Get prerequisites using full path planner sorted topologically
    all_prereqs = get_prerequisite_path(target_node_id, concept_graph)
    
    # Filter out prerequisites where student already has HIGH confidence (>= 70%)
    confidence_map = {}
    if learner_profile:
        confidence_map = learner_profile.get("confidence_map") or {}
        mastery_map = learner_profile.get("mastery_map") or {}
        # Merge them
        for k, v in mastery_map.items():
            if k not in confidence_map:
                confidence_map[k] = v
                
    filtered_prereqs_ids = []
    for pid in all_prereqs:
        node_data = nodes_dict.get(pid, {})
        title = node_data.get("title", "")
        
        # Check confidence by node_id or title
        conf = 50 # Default middle confidence
        if pid in confidence_map:
            conf = confidence_map[pid]
        elif title in confidence_map:
            conf = confidence_map[title]
        elif title.lower() in confidence_map:
            conf = confidence_map[title.lower()]
            
        if isinstance(conf, dict):
            conf = conf.get("score") or conf.get("confidence") or 50
            
        if isinstance(conf, float) and conf <= 1.0:
            conf = conf * 100
            
        if conf >= 70:
            logger.info(f"Skipping prerequisite '{title}' (ID: {pid}) because student confidence is high ({conf}%)")
            continue
            
        filtered_prereqs_ids.append(pid)
        
    # Apply limit after filtering
    limited_prereqs_ids = filtered_prereqs_ids[:prereq_limit]
    
    # Get forward concepts
    forward_ids = get_forward_concepts(target_node_id, concept_graph, forward_limit)
    
    # Collect nodes data
    prereqs_nodes = [nodes_dict[pid].copy() for pid in limited_prereqs_ids if pid in nodes_dict]
    for n, pid in zip(prereqs_nodes, limited_prereqs_ids):
        n["id"] = pid
        n["node_id"] = pid
        
    forward_nodes = [nodes_dict[fid].copy() for fid in forward_ids if fid in nodes_dict]
    for n, fid in zip(forward_nodes, forward_ids):
        n["id"] = fid
        n["node_id"] = fid
        
    # Combine results
    all_retrieved = [target_node] + prereqs_nodes + forward_nodes
    
    return {
        "target_node": target_node,
        "nodes": all_retrieved,
        "prerequisites": prereqs_nodes,
        "forward_concepts": forward_nodes
    }

def resolve(
    query: str,
    document_tree: Dict[str, Any],
    concept_graph: Dict[str, Any],
    condition: str = "C",
    grade: int = 11,
    theta: float = 0.0,
    learner_profile: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Resolve curriculum query with theta and grade personalization."""
    # Always perform personalized retrieval
    return retrieve_personalized(query, document_tree, concept_graph, grade, theta, learner_profile)
