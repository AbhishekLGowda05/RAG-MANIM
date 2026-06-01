"""Central configuration: paths, environment variables, and logging."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

PATHS = {
    "root": ROOT,
    "json": ROOT / "data" / "json",
    "audio": ROOT / "data" / "audio",
    "timelines": ROOT / "data" / "timelines",
    "manim": ROOT / "data" / "manim",
    "renders": ROOT / "data" / "renders",
    "piper_models": ROOT / "data" / "models" / "piper",
    "samples": ROOT / "samples",
}

for _path in PATHS.values():
    if isinstance(_path, Path):
        _path.mkdir(parents=True, exist_ok=True)

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

PIPER_MODEL = os.getenv("PIPER_MODEL", "en_US-lessac-medium")
USE_WHISPERX = os.getenv("USE_WHISPERX", "false").lower() in ("1", "true", "yes")
WHISPERX_MODEL = os.getenv("WHISPERX_MODEL", "base")
WHISPERX_DEVICE = os.getenv("WHISPERX_DEVICE", "cpu")
WHISPERX_COMPUTE_TYPE = os.getenv("WHISPERX_COMPUTE_TYPE", "int8")
MANIM_REPAIR_TIMEOUT = int(os.getenv("MANIM_REPAIR_TIMEOUT", "45"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

NVIDIA_PLANNER_MODEL = os.getenv("NVIDIA_PLANNER_MODEL", "meta/llama-3.3-70b-instruct")
NVIDIA_REPAIR_MODEL = os.getenv("NVIDIA_REPAIR_MODEL", "deepseek-ai/deepseek-r1")

MANIM_QUALITY = os.getenv("MANIM_QUALITY", "-ql")
MANIM_MAX_RETRIES = int(os.getenv("MANIM_MAX_RETRIES", "3"))

FINAL_VIDEO = PATHS["renders"] / "final_video.mp4"


def get_logger(name: str) -> logging.Logger:
    """Return a configured module logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
        logger.propagate = False
    return logger


def ensure_api_keys() -> None:
    """Validate that at least one LLM API key is present."""
    if not NVIDIA_API_KEY and not GEMINI_API_KEY:
        raise EnvironmentError(
            "No LLM API key found. Set NVIDIA_API_KEY (or GEMINI_API_KEY) in .env"
        )
