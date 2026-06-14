"""Retrieve curriculum context from PageIndex pipeline artifacts on disk."""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_TOPIC2MANIM_ROOT = Path(__file__).resolve().parents[3]
if str(_TOPIC2MANIM_ROOT) not in sys.path:
    sys.path.insert(0, str(_TOPIC2MANIM_ROOT))

from PageIndex.pageindex.results_loader import DocumentArtifacts
_PAGEINDEX_ROOT = _TOPIC2MANIM_ROOT / "PageIndex"
_RESULTS_ROOT = _PAGEINDEX_ROOT / "results"
_DEFAULT_PDF = (
    _PAGEINDEX_ROOT
    / "examples"
    / "documents"
    / "SCERT Kerala State Syllabus 10th Standard Physics Textbooks English Medium Part 1.pdf"
)

_TOP_K = 3
_CONTENT_CHAR_CAP = 3000

logger = logging.getLogger(__name__)

_artifacts_cache: Dict[str, DocumentArtifacts] = {}
_concept_graph_cache: Dict[str, dict] = {}


def _guess_subject(name: str) -> str:
    lower = name.lower()
    if "chem" in lower:
        return "Chemistry"
    if "phys" in lower:
        return "Physics"
    return "General"


def _indexed_folders() -> List[Path]:
    if not _RESULTS_ROOT.is_dir():
        return []
    return [
        p for p in _RESULTS_ROOT.iterdir()
        if p.is_dir() and (p / "structure.json").is_file()
    ]


def _match_folder(document_id: str) -> Optional[str]:
    if not document_id or not document_id.strip():
        return None
    doc_id = document_id.strip()
    folders = _indexed_folders()
    if not folders:
        return None

    by_name = {p.name: p for p in folders}
    if doc_id in by_name:
        return doc_id
    if not doc_id.endswith(".pdf") and f"{doc_id}.pdf" in by_name:
        return f"{doc_id}.pdf"
    if doc_id.endswith(".pdf") and doc_id[:-4] in by_name:
        return doc_id[:-4]

    needle = doc_id.lower().replace(".pdf", "")
    for folder in folders:
        hay = folder.name.lower()
        if needle in hay or hay in needle:
            return folder.name
    return None


def _newest_folder() -> Optional[str]:
    candidates = sorted(
        _indexed_folders(),
        key=lambda p: (p / "structure.json").stat().st_mtime,
        reverse=True,
    )
    return candidates[0].name if candidates else None


def _resolve_doc_folder(document_id: Optional[str] = None) -> Tuple[str, str]:
    """Return (folder_name, resolution_source)."""
    if document_id:
        matched = _match_folder(document_id)
        if matched:
            return matched, "request"
        logger.warning("document_id=%r did not match any indexed folder; falling back", document_id)

    env_doc = os.environ.get("PAGEINDEX_ACTIVE_DOC", "").strip()
    if env_doc:
        matched = _match_folder(env_doc)
        if matched:
            return matched, "env"
        if (_RESULTS_ROOT / env_doc).is_dir() and (_RESULTS_ROOT / env_doc / "structure.json").is_file():
            return env_doc, "env"

    newest = _newest_folder()
    if newest:
        return newest, "newest"

    return _DEFAULT_PDF.name, "default"


def _resolve_active_doc() -> str:
    folder, _ = _resolve_doc_folder(None)
    return folder


def _resolve_pdf_path(document_id: Optional[str] = None) -> Path:
    folder, _ = _resolve_doc_folder(document_id)
    if folder.endswith(".pdf"):
        candidate = _PAGEINDEX_ROOT / "examples" / "documents" / folder
        if candidate.is_file():
            return candidate
    return _DEFAULT_PDF


def _artifacts_for(document_id: Optional[str] = None) -> DocumentArtifacts:
    folder, source = _resolve_doc_folder(document_id)
    if folder not in _artifacts_cache:
        results_dir = _RESULTS_ROOT / folder
        if results_dir.is_dir() and (results_dir / "structure.json").is_file():
            _artifacts_cache[folder] = DocumentArtifacts(results_dir)
        else:
            _artifacts_cache[folder] = DocumentArtifacts.from_pdf_path(str(_resolve_pdf_path(document_id)))
        logger.info("Loaded PageIndex artifacts folder=%r source=%s path=%s", folder, source, results_dir)

    artifacts = _artifacts_cache[folder]
    if not artifacts.exists():
        raise FileNotFoundError(
            f"PageIndex results not found at {artifacts.results_dir}. "
            f"Run: cd PageIndex && PYTHONPATH=. python run_pageindex.py "
            f'--pdf_path "<path/to/doc.pdf>" --model qwen2.5:3b --force-reindex'
        )
    return artifacts


def _get_artifacts() -> DocumentArtifacts:
    return _artifacts_for(None)


def clear_artifacts_cache() -> None:
    _artifacts_cache.clear()
    _concept_graph_cache.clear()


def list_documents() -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    for folder in sorted(_indexed_folders(), key=lambda p: p.name.lower()):
        arts = DocumentArtifacts(folder)
        structure = arts.load("structure.json") or {}
        doc_name = structure.get("doc_name") or folder.name
        nodes = arts.walk_nodes()
        docs.append({
            "id": folder.name,
            "doc_name": doc_name,
            "node_count": len(nodes),
            "subject": _guess_subject(doc_name),
        })
    return docs


def _load_concept_graph(artifacts: DocumentArtifacts) -> dict:
    key = str(artifacts.results_dir)
    if key in _concept_graph_cache:
        return _concept_graph_cache[key]
    data = artifacts.load("concept_graph.json") or {}
    _concept_graph_cache[key] = data
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


def retrieve_curriculum_sections(
    topic: str,
    document_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return matched sections with page text pulled from extracted_pages.json."""
    folder, source = _resolve_doc_folder(document_id)
    artifacts = _artifacts_for(document_id)
    all_nodes = artifacts.walk_nodes()
    graph = _load_concept_graph(artifacts)
    if not all_nodes:
        logger.warning("No nodes in structure.json at %s (document=%s source=%s)", artifacts.results_dir, folder, source)
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
        logger.info(
            "No matching nodes topic=%r document=%s source=%s",
            topic, folder, source,
        )
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
            "document_id": folder,
        })

    top = sections[0]
    logger.info(
        "Retrieved %d sections topic=%r document=%s source=%s top=%r breadcrumb=%r pages=%s-%s",
        len(sections),
        topic,
        folder,
        source,
        top.get("title"),
        top.get("breadcrumb"),
        top.get("start_page"),
        top.get("end_page"),
    )
    return sections


def retrieve_curriculum_context(
    topic: str,
    document_id: Optional[str] = None,
) -> str:
    """Return a prompt-ready context string built from on-disk pipeline artifacts."""
    result = retrieve_curriculum(topic, document_id=document_id)
    return result.get("context_text", "")


def retrieve_curriculum(
    topic: str,
    document_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Return structured curriculum object for downstream agents."""
    folder, source = _resolve_doc_folder(document_id)
    sections = retrieve_curriculum_sections(topic, document_id=document_id)
    if not sections:
        return {
            "topic": topic,
            "matched": False,
            "sections": [],
            "context_text": "",
            "document_id": folder,
            "resolution_source": source,
        }

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
        "document_id": folder,
        "resolution_source": source,
    }


# Backward compatibility for api health endpoint
PDF_PATH = _resolve_pdf_path()
RESULTS_DIR = _RESULTS_ROOT / _resolve_active_doc()
