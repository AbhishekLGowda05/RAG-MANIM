"""Semantic validation for pipeline output trees."""

from __future__ import annotations

import re
from typing import Any, Dict, List

JUNK_TITLE_RE = re.compile(
    r"^(?:PHYSICS|CBSE\s+Grade|NCERT|Visual\s+AI\s+Teaching|Physics\s+for\s+Everyone|Grade\s+\d+\s*\|)",
    re.IGNORECASE,
)


def _walk_nodes(structure: List[dict]) -> List[dict]:
    nodes: List[dict] = []

    def visit(node: dict) -> None:
        nodes.append(node)
        for ch in node.get("children") or node.get("nodes") or []:
            visit(ch)

    for root in structure:
        visit(root)
    return nodes


def validate_semantic_tree(result: dict, logger=None) -> dict:
    """Run semantic checks; return report dict with pass/fail per check."""
    structure = result.get("structure") or []
    nodes = _walk_nodes(structure) if structure else []
    checks: Dict[str, Any] = {}

    checks["has_hierarchy_depth"] = any(
        (n.get("children") or n.get("nodes")) for n in structure
    )
    chapters = [n for n in nodes if n.get("content_type") == "chapter"]
    checks["chapters_have_children"] = (
        not chapters
        or all((n.get("children") or n.get("nodes")) for n in chapters)
    )
    summary_nodes = [
        n for n in nodes
        if n.get("content_type") not in ("preface",)
    ]
    checks["summaries_non_empty"] = (
        not summary_nodes
        or all(len((n.get("summary") or "").strip()) >= 30 for n in summary_nodes)
    )

    monotonic_ok = True
    last_start = 0
    for n in nodes:
        sp = n.get("start_page") or n.get("start_index")
        ep = n.get("end_page") or n.get("end_index")
        if sp is not None and sp < last_start:
            monotonic_ok = False
        if sp is not None:
            last_start = sp
        if sp is not None and ep is not None and ep < sp:
            monotonic_ok = False
    checks["monotonic_spans"] = monotonic_ok

    checks["no_minimal_success"] = result.get("fallback") != "minimal_success"
    checks["no_junk_headings"] = not any(
        JUNK_TITLE_RE.match((n.get("title") or "").strip()) for n in nodes
    )
    checks["min_node_count"] = len(nodes) >= 6

    failures = [k for k, v in checks.items() if not v]
    report = {
        "passed": len(failures) == 0,
        "checks": checks,
        "failures": failures,
        "node_count": len(nodes),
        "chapter_count": len(chapters),
    }
    if logger:
        if failures:
            logger.info({"semantic_validation_failed": failures})
        else:
            logger.info({"semantic_validation": "all_passed", "node_count": len(nodes)})
    return report
