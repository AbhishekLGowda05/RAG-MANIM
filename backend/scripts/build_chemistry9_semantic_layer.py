import sys
import json
from pathlib import Path

# Add backend directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from modules.config import RESULTS_DIR, get_logger
from modules.rag.dependency_graph_builder import generate_dependency_graph

logger = get_logger(__name__)

def main():
    logger.info("Building semantic layer and dependency graph...")
    
    # Normally this would process a specific document, but for now we look for any
    # extracted structure.json in the results directory.
    # In a real system this would accept a document_id
    
    structure_path = RESULTS_DIR / "structure.json"
    if not structure_path.exists():
        logger.error(f"Cannot find {structure_path}. Have you indexed a document yet?")
        sys.exit(1)
        
    try:
        with open(structure_path, "r", encoding="utf-8") as f:
            document_tree = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load structure.json: {e}")
        sys.exit(1)
        
    logger.info(f"Loaded document tree. Generating dependency graph...")
    graph = generate_dependency_graph(document_tree)
    
    out_path = RESULTS_DIR / "concept_graph.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)
        
    logger.info(f"Successfully generated dependency graph with {len(graph)} nodes and saved to {out_path}")

if __name__ == "__main__":
    main()
