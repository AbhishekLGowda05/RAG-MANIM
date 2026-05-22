"""Hierarchy repair and semantic boundary refinement (deterministic)."""

from __future__ import annotations

import logging
import re
from typing import List, Optional

_RE_HEADING = re.compile(
    r"^\s*(?:CHAPTER\s+\d+|\d+(?:\.\d+)+\s+[A-Z]|[A-Z][A-Z\s]{4,})\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_RE_LOGICAL_PAGE_MARKER = re.compile(
    r"---\s*Page\s+(\d+)\s*---|—\s*(\d+)\s*—",
    re.IGNORECASE,
)


def build_logical_to_physical_map(page_list: list, start_index: int = 1) -> dict:
    """Map logical textbook page numbers to physical PDF page indices."""
    mapping: dict = {}
    for phys_idx, (text, _) in enumerate(page_list):
        physical_page = phys_idx + start_index
        if not text:
            continue
        for m in _RE_LOGICAL_PAGE_MARKER.finditer(text):
            logical = m.group(1) or m.group(2)
            if logical:
                logical_n = int(logical)
                if logical_n not in mapping:
                    mapping[logical_n] = physical_page
    return mapping


def map_toc_pages_to_physical(
    toc_items: List[dict],
    page_list: list,
    start_index: int = 1,
    logger=None,
) -> List[dict]:
    """Rewrite physical_index using logical page markers embedded in PDF text."""
    l2p = build_logical_to_physical_map(page_list, start_index=start_index)
    if logger and l2p:
        logger.info({"logical_to_physical_map_size": len(l2p)})
    result = []
    for item in toc_items:
        row = dict(item)
        logical = row.get("physical_index") or row.get("page")
        if logical is not None:
            try:
                logical = int(logical)
            except (TypeError, ValueError):
                logical = None
        if logical is not None and logical in l2p:
            row["physical_index"] = l2p[logical]
        elif logical is not None:
            row["physical_index"] = logical
        result.append(row)
    return result


_CONTINUATION_MARKERS = (
    "continued",
    "(cont.)",
    "in summary",
    "recall that",
    "as we saw",
    "chapter summary",
)


def _normalize_structure(structure: Optional[str]) -> Optional[str]:
    if structure is None:
        return None
    s = str(structure).strip().rstrip(".")
    if not s:
        return None
    parts = [p for p in s.split(".") if p.isdigit()]
    return ".".join(parts) if parts else None


def _structure_level(structure: Optional[str]) -> int:
    if not structure:
        return 1
    return len(structure.split("."))


def _parent_structure(structure: str) -> Optional[str]:
    parts = structure.split(".")
    if len(parts) <= 1:
        return None
    return ".".join(parts[:-1])


def repair_hierarchy(entries: List[dict], logger=None) -> List[dict]:
    """Normalise numbering, infer missing parents, repair orphans before list_to_tree."""
    if not entries:
        return entries

    cleaned: List[dict] = []
    for e in entries:
        row = dict(e)
        row["structure"] = _normalize_structure(row.get("structure"))
        row["level"] = _structure_level(row["structure"])
        title = (row.get("title") or "").strip()
        if not title:
            continue
        cleaned.append(row)

    structures_present = {e["structure"] for e in cleaned if e.get("structure")}
    synthetic: List[dict] = []
    for e in cleaned:
        struct = e.get("structure")
        if not struct:
            continue
        parts = struct.split(".")
        for depth in range(1, len(parts)):
            parent = ".".join(parts[:depth])
            if parent not in structures_present:
                parent_entry = {
                    "structure": parent,
                    "title": f"Section {parent}",
                    "page_number": e.get("page_number") or e.get("page") or 0,
                    "level": depth,
                    "synthetic": True,
                }
                synthetic.append(parent_entry)
                structures_present.add(parent)
    cleaned.extend(synthetic)

    orphan_idx = 0
    prev_struct: Optional[str] = None
    for e in cleaned:
        if e.get("structure"):
            prev_struct = e["structure"]
            continue
        if prev_struct:
            orphan_idx += 1
            e["structure"] = f"{prev_struct}.u{orphan_idx}"
        else:
            orphan_idx += 1
            e["structure"] = str(orphan_idx)
        e["level"] = _structure_level(e["structure"])

    for e in cleaned:
        if e.get("structure") and len(e["structure"].split(".")) > 4:
            e["structure"] = ".".join(e["structure"].split(".")[:4])
            e["level"] = 4
            if logger:
                logger.info("repair_hierarchy: clipped deep structure for '%s'", e.get("title"))

    def _sort_key(x: dict):
        struct = x.get("structure") or "0"
        parts = tuple(int(p) if p.isdigit() else 0 for p in struct.split("."))
        return (parts, x.get("page_number") or x.get("page") or 0)

    cleaned.sort(key=_sort_key)

    last_page = 0
    result: List[dict] = []
    for e in cleaned:
        page = e.get("page_number") or e.get("page")
        if page is not None:
            try:
                page = int(page)
            except (TypeError, ValueError):
                page = None
        if page is not None and page < last_page:
            if logger:
                logger.info(
                    "repair_hierarchy: dropped '%s' (page %s < last %s)",
                    e.get("title"),
                    page,
                    last_page,
                )
            continue
        if page is not None:
            last_page = page
        result.append(e)

    if logger:
        logger.info("repair_hierarchy: %s entries after repair", len(result))
    return result


def _page_has_new_heading(page_text: str) -> bool:
    if not page_text:
        return False
    head = page_text[:600]
    if _RE_HEADING.search(head):
        return True
    if re.search(r"^\s*\d+(?:\.\d+)+\s+[A-Z]", head, re.MULTILINE):
        return True
    if re.search(r"^\s*CHAPTER\s+\d+", head, re.IGNORECASE | re.MULTILINE):
        return True
    return False


def _looks_like_continuation(prev_title: str, page_text: str) -> bool:
    if not page_text:
        return False
    lower = page_text[:800].lower()
    if any(m in lower for m in _CONTINUATION_MARKERS):
        return True
    if prev_title and prev_title.lower()[:20] in lower:
        return True
    return not _page_has_new_heading(page_text)


def semantic_boundary_refiner(
    toc_items: List[dict],
    page_list: list,
    opt=None,
    logger=None,
) -> List[dict]:
    """Extend section end_index when the next page continues the same topic."""
    if not toc_items:
        return toc_items

    max_extend = getattr(opt, "boundary_extend_max_pages", 2) if opt else 2
    items = sorted(
        [dict(x) for x in toc_items],
        key=lambda x: x.get("physical_index") or x.get("start_index") or 0,
    )

    for i in range(len(items) - 1):
        cur = items[i]
        nxt = items[i + 1]
        cur_level = _structure_level(cur.get("structure"))
        nxt_level = _structure_level(nxt.get("structure"))
        if cur_level == 1 and nxt_level == 1:
            continue

        cur_end = cur.get("end_index") or cur.get("physical_index")
        nxt_start = nxt.get("physical_index") or nxt.get("start_index")
        if cur_end is None or nxt_start is None:
            continue

        extended = 0
        while extended < max_extend and (nxt_start - cur_end) <= 1:
            probe_page = cur_end + 1
            if probe_page >= nxt_start:
                break
            list_idx = probe_page - 1
            if list_idx < 0 or list_idx >= len(page_list):
                break
            page_text = page_list[list_idx][0] if page_list[list_idx] else ""
            if _page_has_new_heading(page_text):
                break
            if not _looks_like_continuation(cur.get("title", ""), page_text):
                break
            cur_end = probe_page
            extended += 1
            try:
                from .telemetry import PipelineMetrics
                PipelineMetrics.record_shrink("boundary_refiner")
            except Exception:
                pass
            if logger:
                logger.info(
                    "semantic_boundary_refiner: extended '%s' end to page %s",
                    cur.get("title"),
                    cur_end,
                )

        if cur_end != cur.get("end_index"):
            cur["end_index"] = cur_end

    return items
