"""Hierarchy repair and semantic boundary refinement (deterministic)."""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

from .heading_hints import (
    CONTINUATION_WORDS,
    JUNK_STARTERS,
    SCIENCE_HEADING_HINTS,
    SINGLE_WORD_HEADINGS,
)

_GARBLED_RE = re.compile(r"/G\d{2,3}")

# Numbered headings: "1.1 Title" or "1.1.2 Title"
_RE_NUMBERED_HEADING = re.compile(
    r"^\s*(\d+\.\d+(?:\.\d+)?)\s+([A-Z][^\n]{3,80})\s*$",
    re.MULTILINE,
)
# All-caps section headings: "HEATING EFFECT OF CURRENT" (single line only — no \n in match)
_RE_ALLCAPS_HEADING = re.compile(
    r"^\s*([A-Z][A-Z \-]{5,60})\s*$",
    re.MULTILINE,
)

_FRONT_MATTER_TITLE_RE = re.compile(
    r"^(?:Chemistry|Part|Standard|Contents|Pledge|Anthem|Preface)\b",
    re.IGNORECASE,
)


def _is_junk_heading(title: str) -> bool:
    """Reject headings that are front-matter noise, abbreviations, or symbol fragments."""
    if not title or "\n" in title:
        return True
    if len(title) < 4:
        return True
    compact = re.sub(r"\s+", "", title)
    if re.match(r"^([A-Za-z]{3,30})\1$", compact, re.IGNORECASE):
        return True
    words = title.split()
    if words and all(len(w) <= 4 for w in words):
        return True
    for w in words:
        if len(w) >= 4:
            from collections import Counter
            counts = Counter(w.lower())
            if counts and counts.most_common(1)[0][1] / len(w) > 0.6:
                return True
    if re.search(r"(.)\1{3,}", title):
        return True
    if _FRONT_MATTER_TITLE_RE.match(title.strip()):
        return True
    alpha = title.replace(" ", "").replace("-", "")
    if alpha.isupper() and len(set(alpha.lower())) <= 5:
        return True
    letters = sum(1 for c in title if c.isalpha())
    if letters and (len(title) - letters) / len(title) >= 0.5:
        return True
    return False

_RE_HEADING = re.compile(
    r"^\s*(?:CHAPTER\s+\d+|\d+(?:\.\d+)+\s+[A-Z]|[A-Z][A-Z\s]{4,})\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_RE_LOGICAL_PAGE_MARKER = re.compile(
    r"---\s*Page\s+(\d+)\s*---|—\s*(\d+)\s*—",
    re.IGNORECASE,
)


def _is_garbled(text: str) -> bool:
    if not text:
        return False
    sample = text[:2000]
    hits = len(_GARBLED_RE.findall(sample))
    return hits > 10 and (hits / max(len(sample), 1)) > 0.02


def _merge_wrapped_heading(line: str, next_line: Optional[str]) -> Tuple[str, bool]:
    """Merge a heading wrapped onto the next line when clearly a continuation.

    Returns (merged_text, consumed_next_line).
    """
    s = line.rstrip()
    if not next_line:
        return s, False
    nxt = next_line.strip()
    if not nxt:
        return s, False
    # Next line is already a complete heading — do not merge.
    if len(nxt.split()) >= 3 and _is_title_case_heading(nxt):
        return s, False
    words = s.split()
    last_word = words[-1].lower().rstrip("'s") if words else ""
    next_is_cont = (
        nxt[0].islower()
        or nxt.split()[0].lower() in CONTINUATION_WORDS
    )
    if (last_word in CONTINUATION_WORDS or next_is_cont) and len(nxt.split()) <= 4:
        merged = f"{s} {nxt}".strip()
        if _is_exercise_or_table_artifact(merged):
            return s, False
        return merged, True
    return s, False


def _is_exercise_or_table_artifact(title: str) -> bool:
    if re.search(r"[\u0180-\u024F]|Ɵ", title):
        return True
    if re.search(r"^\d+\s+[A-Z][a-z]{0,2}\b", title):
        return True
    if "→" in title or re.search(r"\bHint\s*:", title, re.I):
        return True
    if re.search(r"[a-z][A-Z]", title):
        return True
    if re.search(r"Redox ReactionsRedox|\+ water", title, re.I):
        return True
    if re.search(r"\b(?:model|law)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\s*$", title):
        return True
    if re.search(r"\bIUPAC\b|\bSymbol\b|\bConstituent\b|\bElectronegativity\b", title):
        return True
    if re.search(r"Ca\d|Na\+|HNO\d", title):
        return True
    if "diagram" in title.lower() and len(title) > 42:
        return True
    if re.search(r"\s+[A-Z]\.\s*[A-Z]\.\s+\w+\s*$", title):
        return True
    if re.search(r",\s*a\s*$", title, re.I):
        return True
    if re.search(r"\b(?:rays|Neutron)\s+[A-Z][a-z]+\s*$", title):
        return True
    return False


def _is_table_noise(title: str) -> bool:
    if re.search(r"\d+:\d+", title):
        return True
    if title.count(",") >= 2:
        return True
    if re.search(r"(?:H\d+O|C\d+H|\bTable\s+\d)", title, re.I):
        return True
    return False


def _is_person_name(title: str) -> bool:
    s = title.strip()
    if re.match(r"^[A-Z]\.\s*[A-Z]\.\s+\w+", s):
        return True
    words = s.split()
    if 2 <= len(words) <= 3 and all(w[:1].isupper() for w in words):
        if not any(w.lower() in SCIENCE_HEADING_HINTS for w in words):
            if not any(w.lower() in {"model", "law", "experiment", "atom", "table", "group"} for w in words):
                return True
    return False


def _is_title_case_heading(line: str) -> bool:
    s = line.strip()
    words = s.split()
    if not (2 <= len(words) <= 9):
        if len(words) == 1 and words[0].lower() in SINGLE_WORD_HEADINGS:
            return True
        return False
    if s[-1] in ".:,;?":
        return False
    if _is_table_noise(s) or _is_person_name(s) or _is_exercise_or_table_artifact(s):
        return False
    if "diagram" in s.lower() and "experiment" not in s.lower() and "model" not in s.lower():
        return False
    if any(ch.isdigit() for ch in s) and not re.search(r"[A-Za-z]{4,}", s):
        return False
    cap = sum(1 for w in words if w[:1].isupper())
    if cap / len(words) < 0.6:
        return False
    if words[-1].lower() in CONTINUATION_WORDS:
        return False
    if _is_junk_heading(s) or words[0].lower() in JUNK_STARTERS:
        return False
    if any(w.lower().strip("'s") in SCIENCE_HEADING_HINTS for w in words):
        return True
    return len(words) <= 6


def _extract_titlecase_headings_from_text(
    text: str,
    phys: int,
    parent_structure: str,
    sub_idx: int,
    seen: set,
    min_heading_len: int,
) -> Tuple[List[dict], int]:
    """Scan page lines for unnumbered Title-Case headings."""
    found: List[dict] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw_line = lines[i].strip()
        if not raw_line:
            i += 1
            continue
        next_line = lines[i + 1] if i + 1 < len(lines) else None
        candidate, consumed = _merge_wrapped_heading(raw_line, next_line)
        if not _is_title_case_heading(candidate):
            i += 1
            continue
        title = candidate.strip()
        if len(title) < min_heading_len:
            i += 2 if consumed else 1
            continue
        key = title.lower()[:40]
        if key in seen:
            i += 2 if consumed else 1
            continue
        seen.add(key)
        found.append({
            "structure": f"{parent_structure}.{sub_idx}",
            "title": title,
            "level": len(parent_structure.split(".")) + 1,
            "page_number": phys,
            "physical_index": phys,
        })
        sub_idx += 1
        i += 2 if consumed else 1
    return found, sub_idx


def extract_section_headings_from_pages(
    page_list: list,
    start_page: int,
    end_page: int,
    parent_structure: str,
    min_heading_len: int = 8,
    min_content_page: int = 1,
) -> List[dict]:
    """Deterministically extract sub-section headings from a chapter's pages.

    Returns a list of raw section entries (no node_id yet) with:
      structure, title, level, page_number, physical_index
    """
    sections: List[dict] = []
    sub_idx = 1
    seen: set = set()

    for phys in range(start_page, min(end_page + 1, start_page + len(page_list))):
        if phys < min_content_page:
            continue
        idx = phys - 1
        if idx < 0 or idx >= len(page_list):
            break
        raw = page_list[idx]
        text = raw[0] if isinstance(raw, (tuple, list)) else (raw.get("text") or "")
        if not text or _is_garbled(text):
            continue
        # numbered headings take priority
        for m in _RE_NUMBERED_HEADING.finditer(text):
            num_str, title = m.group(1).strip(), m.group(2).strip()
            key = title.lower()[:40]
            if key in seen or len(title) < min_heading_len or _is_junk_heading(title):
                continue
            seen.add(key)
            sections.append({
                "structure": f"{parent_structure}.{sub_idx}",
                "title": title,
                "level": len(parent_structure.split(".")) + 1,
                "page_number": phys,
                "physical_index": phys,
            })
            sub_idx += 1
        # all-caps headings only if no numbered ones found yet for this page
        if not any(s["physical_index"] == phys for s in sections):
            for m in _RE_ALLCAPS_HEADING.finditer(text):
                title = m.group(1).strip().title()  # normalise to Title Case
                if len(title) < min_heading_len or _is_junk_heading(title):
                    continue
                key = title.lower()[:40]
                if key in seen:
                    continue
                # Skip generic words that appear everywhere
                skip_words = {"chapter", "section", "contents", "physics", "exercises", "summary"}
                if title.lower().split()[0] in skip_words:
                    continue
                seen.add(key)
                sections.append({
                    "structure": f"{parent_structure}.{sub_idx}",
                    "title": title,
                    "level": len(parent_structure.split(".")) + 1,
                    "page_number": phys,
                    "physical_index": phys,
                })
                sub_idx += 1
        # Title-Case headings when no numbered/all-caps found on this page
        if not any(s["physical_index"] == phys for s in sections):
            tc_found, sub_idx = _extract_titlecase_headings_from_text(
                text, phys, parent_structure, sub_idx, seen, min_heading_len,
            )
            sections.extend(tc_found)

    return sections


def inject_subsections_into_tree(
    toc_tree: List[dict],
    page_list: list,
    logger=None,
    min_content_page: int = 1,
) -> int:
    """Add child nodes to flat chapter nodes using deterministic heading detection.

    Returns total number of children added across all chapters.
    """
    added_total = 0
    for node in toc_tree:
        if node.get("nodes") or node.get("children"):
            continue  # already has children — skip
        start = node.get("start_index") or node.get("start_page")
        end = node.get("end_index") or node.get("end_page")
        struct = str(node.get("structure") or "1")
        if not start or not end or end <= start:
            continue

        children_raw = extract_section_headings_from_pages(
            page_list, int(start), int(end), parent_structure=struct,
            min_content_page=min_content_page,
        )
        if not children_raw:
            continue

        # Build child dicts with correct end pages
        child_nodes = []
        for i, ch in enumerate(children_raw):
            next_start = children_raw[i + 1]["physical_index"] if i + 1 < len(children_raw) else int(end)
            child_nodes.append({
                "title": ch["title"],
                "structure": ch["structure"],
                "level": ch["level"],
                "parent_id": node.get("node_id"),
                "node_id": None,
                "start_index": ch["physical_index"],
                "start_page": ch["physical_index"],
                "end_index": next_start - 1 if next_start > ch["physical_index"] else ch["physical_index"],
                "end_page": next_start - 1 if next_start > ch["physical_index"] else ch["physical_index"],
                "summary": "",
                "keywords": [],
                "semantic_tags": [],
                "content_type": "section",
            })

        node["nodes"] = child_nodes
        added_total += len(child_nodes)
        if logger:
            logger.info(
                "inject_subsections: %d children added to '%s' (pages %s-%s)",
                len(child_nodes), node.get("title"), start, end,
            )

    if logger:
        logger.info("inject_subsections: %d total children added across all chapters", added_total)
    return added_total


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
