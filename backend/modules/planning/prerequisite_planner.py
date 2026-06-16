from typing import Dict, Any, List, Set
from collections import deque

def topological_sort(nodes: Set[str], concept_graph: Dict[str, Any]) -> List[str]:
    """
    Perform topological sort on a set of nodes based on concept_graph dependencies.
    A prerequisite comes BEFORE its dependent node.
    """
    # Build adjacency list for this subgraph
    adj = {node: set() for node in nodes}
    in_degree = {node: 0 for node in nodes}
    
    for node in nodes:
        prereqs = concept_graph.get(node, {}).get("prerequisites", [])
        for p in prereqs:
            if p in nodes:
                # p is a prerequisite of node, so p -> node edge
                if node not in adj[p]:
                    adj[p].add(node)
                    in_degree[node] += 1
                    
    # Standard Kahn's algorithm
    queue = deque([node for node in nodes if in_degree[node] == 0])
    result = []
    
    while queue:
        u = queue.popleft()
        result.append(u)
        for v in adj[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)
                
    # If there's a cycle, Kahn's algorithm output might be incomplete.
    # Append any remaining nodes just in case
    for node in nodes:
        if node not in result:
            result.append(node)
            
    return result

def get_prerequisite_path(target_node_id: str, concept_graph: Dict[str, Any]) -> List[str]:
    """
    Perform BFS/DFS to retrieve all ancestors (prerequisites) of target_node_id,
    and return them in topologically sorted order.
    """
    if target_node_id not in concept_graph:
        return []
        
    visited: Set[str] = set()
    queue = deque([target_node_id])
    
    # Traverse backward along prerequisite edges to find all ancestors
    while queue:
        curr = queue.popleft()
        prereqs = concept_graph.get(curr, {}).get("prerequisites", [])
        for p in prereqs:
            if p not in visited and p != target_node_id:
                visited.add(p)
                queue.append(p)
                
    # Sort them topologically so they are ordered pedagogically
    sorted_path = topological_sort(visited, concept_graph)
    return sorted_path
