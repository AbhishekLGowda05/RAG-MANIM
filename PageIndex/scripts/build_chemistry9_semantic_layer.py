#!/usr/bin/env python3
"""Build concept_graph.json and pedagogical_metadata.json from structure.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

SCHEMA_VERSION = "1.0"

# Allow running from PageIndex/ or repo root
_PAGEINDEX_ROOT = Path(__file__).resolve().parent.parent
if str(_PAGEINDEX_ROOT) not in sys.path:
    sys.path.insert(0, str(_PAGEINDEX_ROOT))

from pageindex.pedagogy_metadata import (  # noqa: E402
    derive_learning_objectives,
    derive_semantic_tags,
    derive_visualizable_elements,
)
from pageindex.results_loader import DocumentArtifacts  # noqa: E402


def _walk_nodes(structure: List[dict]) -> List[dict]:
    flat: List[dict] = []
    for node in structure:
        flat.append(node)
        children = node.get("children") or node.get("nodes") or []
        flat.extend(_walk_nodes(children))
    return flat


def _keyword_overlap(a: dict, b: dict) -> float:
    ka = set((a.get("keywords") or []) + (a.get("semantic_tags") or []))
    kb = set((b.get("keywords") or []) + (b.get("semantic_tags") or []))
    if not ka or not kb:
        return 0.0
    return len(ka & kb) / max(len(ka | kb), 1)


def _build_prerequisite_edges(nodes: List[dict]) -> List[dict]:
    """Earlier section in same chapter → later section (ordered appearance)."""
    edges: List[dict] = []
    seen: Set[Tuple[str, str]] = set()
    by_chapter: Dict[str, List[dict]] = {}
    for n in nodes:
        if n.get("content_type") == "preface":
            continue
        struct = str(n.get("structure") or "")
        chapter_key = struct.split(".")[0] if struct else n.get("node_id", "")
        by_chapter.setdefault(chapter_key, []).append(n)

    for _ch, chapter_nodes in by_chapter.items():
        ordered = sorted(
            chapter_nodes,
            key=lambda x: (
                x.get("start_page") or x.get("start_index") or 0,
                x.get("level") or 1,
            ),
        )
        for i in range(len(ordered) - 1):
            prev, nxt = ordered[i], ordered[i + 1]
            if prev.get("level", 1) == 1 and nxt.get("level", 1) == 1:
                continue
            fid, tid = prev.get("node_id"), nxt.get("node_id")
            if not fid or not tid or (fid, tid) in seen:
                continue
            if _keyword_overlap(prev, nxt) >= 0.05 or prev.get("level", 1) < nxt.get("level", 1):
                edges.append({"from": fid, "to": tid, "relation": "prerequisite"})
                seen.add((fid, tid))
    return edges


def build_concept_graph(structure: List[dict], doc_name: str) -> dict:
    nodes = _walk_nodes(structure)
    graph_nodes = [
        {
            "node_id": n.get("node_id"),
            "title": n.get("title"),
            "keywords": n.get("keywords") or [],
            "semantic_tags": n.get("semantic_tags") or [],
        }
        for n in nodes
        if n.get("node_id")
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "doc_name": doc_name,
        "nodes": graph_nodes,
        "edges": _build_prerequisite_edges(nodes),
    }


def build_pedagogical_metadata(structure: List[dict], doc_name: str) -> dict:
    nodes = _walk_nodes(structure)
    per_node: Dict[str, dict] = {}
    for n in nodes:
        nid = n.get("node_id")
        if not nid:
            continue
        child_titles = [
            (c.get("title") or "").strip()
            for c in (n.get("children") or n.get("nodes") or [])
        ]
        per_node[nid] = {
            "title": n.get("title"),
            "learning_objectives": n.get("learning_objectives")
            or derive_learning_objectives(n.get("title") or "", child_titles),
            "semantic_tags": n.get("semantic_tags")
            or derive_semantic_tags(n.get("title") or "", n.get("keywords")),
            "visualizable_elements": n.get("visualizable_elements")
            or derive_visualizable_elements("", n.get("keywords"), n.get("title") or ""),
            "common_misconceptions": n.get("common_misconceptions") or [],
            "grade_appropriateness": n.get("grade_appropriateness") or "Class IX",
        }
    chapter_titles = [
        n.get("title") for n in nodes if n.get("content_type") == "chapter"
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "doc_name": doc_name,
        "doc_summary": f"Curriculum tree for {doc_name}: {len(nodes)} nodes, "
        f"{len(chapter_titles)} chapters.",
        "primary_topics": [t for t in chapter_titles if t],
        "nodes": per_node,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build semantic layer artifacts from structure.json")
    parser.add_argument("--doc", default="Chemistry_9.pdf", help="Document results folder name")
    parser.add_argument(
        "--results-root",
        type=Path,
        default=_PAGEINDEX_ROOT / "results",
        help="PageIndex results root directory",
    )
    parser.add_argument(
        "--quality",
        action="store_true",
        help="Optional SLM polish (default: fully deterministic, no LLM calls)",
    )
    args = parser.parse_args()

    results_dir = args.results_root / args.doc
    arts = DocumentArtifacts(results_dir)
    if not arts.exists():
        print(f"ERROR: structure.json not found at {results_dir}", file=sys.stderr)
        return 1

    data = arts.load("structure.json") or {}
    structure = data.get("structure") or []
    doc_name = data.get("doc_name") or args.doc

    concept_graph = build_concept_graph(structure, doc_name)
    ped_meta = build_pedagogical_metadata(structure, doc_name)

    if args.quality:
        print("[semantic_layer] --quality requested; SLM polish not yet implemented — deterministic output written.")

    for fname, payload in (
        ("concept_graph.json", concept_graph),
        ("pedagogical_metadata.json", ped_meta),
    ):
        out = results_dir / fname
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"Wrote {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
