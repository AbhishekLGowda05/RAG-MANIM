from typing import List, Dict, Any, Set
from collections import deque

def expand_dependencies(
    target_node_id: str,
    concept_graph: Dict[str, Any],
    document_tree: Dict[str, Any],
    depth_limit: int = 2
) -> List[Dict[str, Any]]:
    """
    Perform BFS to expand prerequisite dependencies.
    """
    if target_node_id not in concept_graph:
        return []
        
    prerequisites_ids: Set[str] = set()
    queue = deque([(target_node_id, 0)])
    
    while queue:
        current_node, depth = queue.popleft()
        
        if depth >= depth_limit:
            continue
            
        node_data = concept_graph.get(current_node, {})
        prereqs = node_data.get("prerequisites", [])
        
        for prereq in prereqs:
            if prereq not in prerequisites_ids and prereq != target_node_id:
                prerequisites_ids.add(prereq)
                queue.append((prereq, depth + 1))
                
    # Assemble full node data for prerequisites
    expanded_nodes = []
    nodes_data = document_tree.get("nodes", {})
    for pid in prerequisites_ids:
        if pid in nodes_data:
            node_info = nodes_data[pid].copy()
            node_info["id"] = pid
            expanded_nodes.append(node_info)
            
    return expanded_nodes
