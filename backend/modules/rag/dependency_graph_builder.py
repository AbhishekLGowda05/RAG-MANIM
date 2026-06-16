import json
import logging
from typing import Dict, Any

from modules.config import NVIDIA_PLANNER_MODEL, PATHS
from modules.llm.nvidia_client import NvidiaClient

logger = logging.getLogger(__name__)

DEPENDENCY_SYSTEM_PROMPT = """You are an expert educational ontologist.
Given a list of textbook sections (concepts), identify the direct pedagogical prerequisites for each concept.
Return a JSON object mapping each node identifier to a list of prerequisite node identifiers.
Only include direct prerequisites necessary to understand the target concept.
"""

def generate_dependency_graph(document_tree: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a concept dependency graph using LLM, and apply hallucination filter."""
    nodes = document_tree.get("nodes", {})
    if not nodes:
        return {}
        
    # Extract node metadata for prompt
    node_summaries = {}
    for node_id, node_data in nodes.items():
        node_summaries[node_id] = {
            "title": node_data.get("title", ""),
            "summary": node_data.get("summary", ""),
            "keywords": node_data.get("keywords", [])
        }
        
    client = NvidiaClient()
    prompt = f"""
    Given the following curriculum concepts and their summaries, build a prerequisite graph.
    
    Concepts:
    {json.dumps(node_summaries, indent=2)}
    
    Output Format Example:
    {{
      "concept_1_id": {{
        "prerequisites": ["concept_2_id", "concept_3_id"],
        "confidence": 0.9
      }}
    }}
    
    Return ONLY valid JSON.
    """
    
    messages = [
        {"role": "system", "content": DEPENDENCY_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    
    try:
        raw_graph = client.chat_json(NVIDIA_PLANNER_MODEL, messages, temperature=0.2)
    except Exception as e:
        logger.error(f"Failed to generate dependency graph: {e}")
        return {}
        
    # Hallucination filter: ensure all claimed prereqs exist in the tree
    valid_graph = {}
    for node_id, data in raw_graph.items():
        if node_id not in nodes:
            continue
            
        prereqs = data.get("prerequisites", [])
        valid_prereqs = [p for p in prereqs if p in nodes and p != node_id]
        
        valid_graph[node_id] = {
            "prerequisites": valid_prereqs,
            "confidence": data.get("confidence", 0.8)
        }
        
    return valid_graph
