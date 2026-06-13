"""Retrieve curriculum context from PageIndex pipeline artifacts on disk."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PageIndex.pageindex.results_loader import DocumentArtifacts

_TOPIC2MANIM_ROOT = Path(__file__).resolve().parents[3]
_PAGEINDEX_ROOT = _TOPIC2MANIM_ROOT / "PageIndex"
_DEFAULT_PDF = (
    _PAGEINDEX_ROOT
    / "examples"
    / "documents"
    / "SCERT Kerala State Syllabus 10th Standard Physics Textbooks English Medium Part 1.pdf"
)

_TOP_K = 3
_CONTENT_CHAR_CAP = 3000

logger = logging.getLogger(__name__)

_artifacts: Optional[DocumentArtifacts] = None
_concept_graph_cache: Optional[dict] = None


def _resolve_active_doc() -> str:
    env_doc = os.environ.get("PAGEINDEX_ACTIVE_DOC", "").strip()
    if env_doc:
        return env_doc
    results_root = _PAGEINDEX_ROOT / "results"
    if results_root.is_dir():
        candidates = sorted(
            (p for p in results_root.iterdir() if p.is_dir() and (p / "structure.json").is_file()),
            key=lambda p: (p / "structure.json").stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return candidates[0].name
    return _DEFAULT_PDF.name


def _resolve_pdf_path() -> Path:
    active = _resolve_active_doc()
    if active.endswith(".pdf"):
        candidate = _PAGEINDEX_ROOT / "examples" / "documents" / active
        if candidate.is_file():
            return candidate
    return _DEFAULT_PDF


def _get_artifacts() -> DocumentArtifacts:
    global _artifacts
    if _artifacts is None:
        active = _resolve_active_doc()
        if active.endswith(".pdf") and (_PAGEINDEX_ROOT / "results" / active).is_dir():
            _artifacts = DocumentArtifacts(_PAGEINDEX_ROOT / "results" / active)
        else:
            _artifacts = DocumentArtifacts.from_pdf_path(str(_resolve_pdf_path()))
    if not _artifacts.exists():
        raise FileNotFoundError(
            f"PageIndex results not found at {_artifacts.results_dir}. "
            f"Run: cd PageIndex && PYTHONPATH=. python run_pageindex.py "
            f'--pdf_path "<path/to/doc.pdf>" --model qwen2.5:3b --force-reindex'
        )
    return _artifacts


def _load_concept_graph(artifacts: DocumentArtifacts) -> dict:
    global _concept_graph_cache
    if _concept_graph_cache is not None:
        return _concept_graph_cache
    data = artifacts.load("concept_graph.json") or {}
    _concept_graph_cache = data
    return data


def _resolve_prerequisites(node_id: str, graph: dict, all_nodes: list) -> List[dict]:
    if not node_id or not graph:
        return []
    id_to_node = {n.get("node_id"): n for n in all_nodes if n.get("node_id")}
    title_map = {n.get("node_id"): n.get("title") for n in graph.get("nodes") or []}
    prereqs: List[dict] = []
    for edge in graph.get("edges") or []:
        if edge.get("to") != node_id or edge.get("relation") != "prerequisite":
            continue
        fid = edge.get("from")
        if not fid:
            continue
        node = id_to_node.get(fid) or {}
        prereqs.append({
            "node_id": fid,
            "title": title_map.get(fid) or node.get("title") or fid,
        })
    return prereqs


def _score_node(node: dict, topic_words: set) -> float:
    title = (node.get("title") or "").lower()
    summary = (node.get("summary") or "").lower()
    keywords = " ".join(node.get("keywords") or []).lower()
    tags = " ".join(node.get("semantic_tags") or []).lower()
    combined = f"{title} {summary} {keywords} {tags}"
    hits = sum(1 for w in topic_words if w in combined)
    depth_bonus = 0.1 * (node.get("level", 1) - 1)
    summary_bonus = 0.2 if len((node.get("summary") or "")) > 30 else 0.0
    return hits + depth_bonus + summary_bonus


def _breadcrumb(node: dict, all_nodes: list) -> str:
    parent_id = node.get("parent_id")
    parts = [node.get("title", "")]
    visited = {node.get("node_id")}
    while parent_id:
        parent = next((n for n in all_nodes if n.get("node_id") == parent_id), None)
        if not parent or parent.get("node_id") in visited:
            break
        parts.insert(0, parent.get("title", ""))
        visited.add(parent.get("node_id"))
        parent_id = parent.get("parent_id")
    return " > ".join(p for p in parts if p)


def retrieve_curriculum_sections(topic: str) -> List[Dict[str, Any]]:
    """Return matched sections with page text pulled from extracted_pages.json."""
    artifacts = _get_artifacts()
    all_nodes = artifacts.walk_nodes()
    graph = _load_concept_graph(artifacts)
    if not all_nodes:
        logger.warning("No nodes in structure.json at %s", artifacts.results_dir)
        return []

    topic_words = set(w for w in topic.lower().split() if len(w) > 2)
    scored = [
        (node, _score_node(node, topic_words))
        for node in all_nodes
        if node.get("content_type") != "preface"
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    top_matches = [(n, s) for n, s in scored[:_TOP_K] if s > 0]
    if not top_matches:
        logger.info("No matching nodes for topic=%s", topic)
        return []

    sections: List[Dict[str, Any]] = []
    for node, score in top_matches:
        start = node.get("start_page") or node.get("start_index")
        end = node.get("end_page") or node.get("end_index")
        page_text = ""
        page_numbers: List[int] = []
        if start and end:
            pages = artifacts.get_pages(int(start), int(end))
            page_numbers = [int(p["page"]) for p in pages if p.get("page")]
            page_text = artifacts.get_page_text(
                int(start), int(end), max_chars=_CONTENT_CHAR_CAP, skip_garbled=True
            )

        node_id = node.get("node_id", "")
        sections.append({
            "title": node.get("title", ""),
            "breadcrumb": _breadcrumb(node, all_nodes),
            "node_id": node_id,
            "start_page": start,
            "end_page": end,
            "page_numbers": page_numbers,
            "summary": node.get("summary", ""),
            "keywords": node.get("keywords", []),
            "semantic_tags": node.get("semantic_tags", []),
            "learning_objectives": node.get("learning_objectives", []),
            "visualizable_elements": node.get("visualizable_elements", []),
            "grade_appropriateness": node.get("grade_appropriateness", ""),
            "prerequisites": _resolve_prerequisites(node_id, graph, all_nodes),
            "score": score,
            "content": page_text,
            "artifacts_dir": str(artifacts.results_dir),
        })

    logger.info(
        "Found %d sections for topic=%s from %s",
        len(sections), topic, artifacts.results_dir,
    )
    return sections


def retrieve_curriculum_context(topic: str) -> str:
    """Return a prompt-ready context string built from on-disk pipeline artifacts."""
    result = retrieve_curriculum(topic)
    return result.get("context_text", "")


def retrieve_curriculum(topic: str) -> Dict[str, Any]:
    """Return structured curriculum object for downstream agents."""
    sections = retrieve_curriculum_sections(topic)
    if not sections:
        return {"topic": topic, "matched": False, "sections": [], "context_text": ""}

    parts = []
    for sec in sections:
        crumb = sec["breadcrumb"] or sec["title"]
        start, end = sec.get("start_page"), sec.get("end_page")
        page_ref = f"pages {start}-{end}" if start and end else "pages unknown"
        kw = ", ".join(sec["keywords"][:6]) if sec["keywords"] else ""
        tags = ", ".join(sec.get("semantic_tags") or [])[:80]
        prereq_titles = ", ".join(p.get("title", "") for p in sec.get("prerequisites") or [])
        chunk = f"[{crumb}] ({page_ref})"
        if sec["summary"]:
            chunk += f"\nSummary: {sec['summary']}"
        if kw:
            chunk += f"\nKeywords: {kw}"
        if tags:
            chunk += f"\nTags: {tags}"
        if prereq_titles:
            chunk += f"\nPrerequisites: {prereq_titles}"
        if sec.get("learning_objectives"):
            chunk += f"\nObjectives: {'; '.join(sec['learning_objectives'][:3])}"
        if sec["content"]:
            chunk += f"\nSource text:\n{sec['content']}"
        else:
            chunk += "\n(No readable page text.)"
        parts.append(chunk)

    return {
        "topic": topic,
        "matched": True,
        "sections": sections,
        "context_text": "\n\n---\n\n".join(parts),
    }


# Backward compatibility for api health endpoint
PDF_PATH = _resolve_pdf_path()
RESULTS_DIR = _PAGEINDEX_ROOT / "results" / _resolve_active_doc()
