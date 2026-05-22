"""Manim renderer with Gemini-driven repair retry loop."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from modules.config import (
    MANIM_MAX_RETRIES,
    MANIM_QUALITY,
    NVIDIA_REPAIR_MODEL,
    PATHS,
    get_logger,
)
from modules.llm.nvidia_client import NvidiaClient

logger = get_logger(__name__)

REPAIR_SYSTEM = """You are an expert Manim Community Edition debugger.
Return ONLY the corrected Python file. No markdown fences, no commentary.
Keep class name GeneratedScene and keep all run_time values exactly as-is.
Never use .get_edge() (use .get_left/right/top/bottom). Never use ApplyMethod.
Ensure no mobjects overlap (use .arrange or .next_to with buff)."""

REPAIR_PROMPT = """The following Manim script failed to render.

ERROR:
{error}

CURRENT CODE:
{code}

Return the COMPLETE fixed Python file only."""


def render(
    scene_py: Path,
    scene_class: str = "GeneratedScene",
    fallback_code: str | None = None,
) -> Path:
    """Render a Manim scene file to MP4 with retry on failure."""
    media_dir = PATHS["manim"] / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Rendering Manim scene: %s", scene_py.name)

    for attempt in range(MANIM_MAX_RETRIES):
        mp4 = _run_manim(scene_py, scene_class, media_dir)
        if mp4 and mp4.exists():
            dest = PATHS["renders"] / f"{scene_py.stem}.mp4"
            if mp4 != dest:
                import shutil

                shutil.copy2(mp4, dest)
            logger.info("Render success: %s (attempt %d)", dest, attempt + 1)
            return dest

        error = _last_error or "Unknown render error"
        logger.warning("Render attempt %d failed: %s", attempt + 1, error[:200])

        if attempt < MANIM_MAX_RETRIES - 1:
            repaired = _try_repair(scene_py, error)
            if not repaired and fallback_code:
                logger.warning(
                    "Repair unavailable; writing template fallback to %s",
                    scene_py,
                )
                scene_py.write_text(fallback_code, encoding="utf-8")

    if fallback_code:
        logger.warning(
            "All LLM attempts failed; falling back to deterministic template for %s",
            scene_py.name,
        )
        scene_py.write_text(fallback_code, encoding="utf-8")
        mp4 = _run_manim(scene_py, scene_class, media_dir)
        if mp4 and mp4.exists():
            dest = PATHS["renders"] / f"{scene_py.stem}.mp4"
            import shutil

            shutil.copy2(mp4, dest)
            logger.info("Template fallback render success: %s", dest)
            return dest

    raise RuntimeError(
        f"Manim render failed after {MANIM_MAX_RETRIES} attempts: {scene_py}"
    )

_last_error: str = ""


def _run_manim(scene_py: Path, scene_class: str, media_dir: Path) -> Path | None:
    """Execute manim CLI and locate output MP4."""
    global _last_error
    cmd = [
        "manim",
        "render",
        MANIM_QUALITY,
        str(scene_py),
        scene_class,
        "--media_dir",
        str(media_dir),
        "--disable_caching",
    ]
    logger.info("Running: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(PATHS["root"]),
        )
        if result.returncode != 0:
            _last_error = result.stderr or result.stdout
            return None

        mp4_files = sorted(
            media_dir.rglob("*.mp4"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if mp4_files:
            return mp4_files[0]
        _last_error = "No MP4 output found after render"
        return None
    except subprocess.TimeoutExpired:
        _last_error = "Manim render timed out after 300s"
        return None
    except Exception as exc:
        _last_error = str(exc)
        return None


def _try_repair(scene_py: Path, error: str) -> bool:
    """Send failed code to NVIDIA NIM for repair. Returns True on success."""
    logger.info("Requesting NVIDIA repair for %s", scene_py.name)
    code = scene_py.read_text(encoding="utf-8")
    try:
        client = NvidiaClient()
        messages = [
            {"role": "system", "content": REPAIR_SYSTEM},
            {
                "role": "user",
                "content": REPAIR_PROMPT.format(error=error[:3000], code=code[:8000]),
            },
        ]
        fixed = client.chat(
            NVIDIA_REPAIR_MODEL, messages, temperature=0.1, max_tokens=8192
        )
    except Exception as exc:
        logger.warning("Repair LLM call failed: %s", exc)
        return False

    fixed = fixed.strip()
    if "```python" in fixed:
        match = re.search(r"```python\s*(.*?)\s*```", fixed, re.DOTALL)
        if match:
            fixed = match.group(1)
    elif "```" in fixed:
        match = re.search(r"```\s*(.*?)\s*```", fixed, re.DOTALL)
        if match:
            fixed = match.group(1)
    fixed = fixed.strip()
    if "from manim import" in fixed and "GeneratedScene" in fixed:
        scene_py.write_text(fixed, encoding="utf-8")
        logger.info("Repaired code written to %s", scene_py)
        return True
    logger.warning("Repair output invalid; keeping original")
    return False
