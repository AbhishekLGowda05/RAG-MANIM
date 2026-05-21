"""Per-stage Ollama model routing."""

from __future__ import annotations

from typing import Any, Dict, Optional

STAGE_MODEL_MAP: Dict[str, str] = {
    "toc_detection": "ollama/gemma4:e4b",
    "toc_index_extractor": "ollama/gemma4:e4b",
    "no_toc_outline": "ollama/gemma4:e4b",
    "tree_construction": "ollama/gemma4:e4b",
    "summary_generation": "ollama/gemma4:e4b",
    "chapter_summary": "ollama/gemma4:e4b",
    "title_cleanup": "ollama/qwen2.5:3b",
    "ocr_cleanup": "ollama/qwen2.5:3b",
    "extractive_polish": "ollama/qwen2.5:3b",
    "doc_description": "ollama/qwen2.5:3b",
}

_stage_models_override: Optional[Dict[str, str]] = None


def configure_stage_models(stage_models: Optional[Dict[str, Any]] = None) -> None:
    global _stage_models_override
    if not stage_models:
        _stage_models_override = None
        return
    _stage_models_override = {str(k): str(v) for k, v in stage_models.items() if v}


def model_for_stage(stage: Optional[str], default: str) -> str:
    if not stage:
        return default
    if _stage_models_override and stage in _stage_models_override:
        return _stage_models_override[stage]
    return STAGE_MODEL_MAP.get(stage, default)
