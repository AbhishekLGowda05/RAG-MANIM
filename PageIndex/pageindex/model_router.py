"""Per-stage Ollama model routing."""

from __future__ import annotations

from typing import Any, Dict, Optional

STAGE_MODEL_MAP: Dict[str, str] = {
    "toc_detection": "ollama/qwen2.5:3b",
    "toc_index_extractor": "ollama/qwen2.5:3b",
    "no_toc_outline": "ollama/qwen2.5:3b",
    "tree_construction": "ollama/qwen2.5:3b",
    "summary_generation": "ollama/qwen2.5:3b",
    "chapter_summary": "ollama/qwen2.5:3b",
    "title_cleanup": "ollama/qwen2.5:3b",
    "ocr_cleanup": "ollama/qwen2.5:3b",
    "extractive_polish": "ollama/qwen2.5:3b",
    "doc_description": "ollama/qwen2.5:3b",
}

# Stages promoted to a heavier model under --quality flag
QUALITY_STAGE_OVERRIDES: Dict[str, str] = {
    "chapter_summary": "ollama/qwen2.5-coder:7b",
    "toc_index_extractor": "ollama/qwen2.5-coder:7b",
    "no_toc_outline": "ollama/qwen2.5-coder:7b",
}

_stage_models_override: Optional[Dict[str, str]] = None
_quality_mode: bool = False


def configure_stage_models(stage_models: Optional[Dict[str, Any]] = None) -> None:
    global _stage_models_override
    if not stage_models:
        _stage_models_override = None
        return
    _stage_models_override = {str(k): str(v) for k, v in stage_models.items() if v}


def set_quality_mode(enabled: bool = True, quality_overrides: Optional[Dict[str, str]] = None) -> None:
    """Enable or disable quality mode (routes selected stages to a larger model)."""
    global _quality_mode, _stage_models_override
    _quality_mode = enabled
    if enabled:
        overrides = quality_overrides or QUALITY_STAGE_OVERRIDES
        merged = dict(_stage_models_override or {})
        merged.update(overrides)
        _stage_models_override = merged
        import logging
        logging.getLogger(__name__).info(
            "quality_mode=ON stages=%s", list(overrides.keys())
        )


def model_for_stage(stage: Optional[str], default: str) -> str:
    if not stage:
        return default
    if _stage_models_override and stage in _stage_models_override:
        return _stage_models_override[stage]
    return STAGE_MODEL_MAP.get(stage, default)
