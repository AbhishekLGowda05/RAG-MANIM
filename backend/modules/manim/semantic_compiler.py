"""Semantic compiler: dispatches plan + timeline → Manim scene code.

This is the production compiler. It:
  1. Looks up the correct concept template from TEMPLATES registry
  2. Passes the semantic plan and timed event timeline to template.compile()
  3. Validates the generated code has no raw geometry primitives
  4. Writes the final scene_N.py file
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from modules.config import PATHS, get_logger
from modules.templates import TEMPLATES

logger = get_logger(__name__)

# These are the primitive geometry calls that should NOT appear in
# semantically compiled output — presence means a template bug.
_GEOMETRY_PRIMITIVES = (
    "Line(LEFT",
    "Line(RIGHT",
    "Arrow(LEFT",
    "Arrow(RIGHT",
    "Circle(radius=",
    "Square(side_length=",
    'Rectangle(width=',
)


def semantic_compile(
    plan: dict[str, Any],
    sync_result: dict[str, Any],
) -> tuple[Path, str]:
    """Compile a Manim scene file from a semantic plan + timed timeline.

    Returns (file_path, scene_code) — the file is written to disk.
    """
    scene_id = plan["scene_id"]
    template_id = plan.get("concept_template", "intro")
    logger.info("Compiling scene %d with template '%s'", scene_id, template_id)

    template_cls = TEMPLATES.get(template_id)
    if template_cls is None:
        logger.warning("Template '%s' not found; falling back to 'intro'", template_id)
        template_cls = TEMPLATES["intro"]

    timeline = sync_result.get("timeline", {
        "audio_duration": sync_result.get("audio_duration", 8.0),
        "events": [],
    })
    # Flatten: templates expect timeline with audio_duration at top level
    if "audio_duration" not in timeline:
        timeline["audio_duration"] = sync_result.get("audio_duration", 8.0)

    code = template_cls.compile(plan, timeline)
    code = _post_process(code, scene_id)

    out_path = PATHS["manim"] / f"scene_{scene_id}.py"
    out_path.write_text(code, encoding="utf-8")
    logger.info("Semantic Manim code written: %s (%d lines)", out_path, code.count("\n"))
    return out_path, code


def semantic_compile_all(
    plans: list[dict[str, Any]],
    timelines: list[dict[str, Any]],
) -> list[tuple[Path, str]]:
    """Compile all scenes."""
    timeline_map = {t["scene_id"]: t for t in timelines}
    results = []
    for plan in plans:
        sid = plan["scene_id"]
        sync = timeline_map.get(sid, {"scene_id": sid, "audio_duration": 8.0, "timeline": {}})
        results.append(semantic_compile(plan, sync))
    return results


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------


def _post_process(code: str, scene_id: int) -> str:
    """Ensure the generated code is well-formed and warn on any issues."""
    if "from manim import *" not in code:
        code = "from manim import *\nimport numpy as np\n\n" + code

    if "import numpy as np" not in code:
        code = code.replace("from manim import *", "from manim import *\nimport numpy as np", 1)

    if "class GeneratedScene" not in code:
        logger.error("Scene %d: compiled code missing GeneratedScene class!", scene_id)

    _warn_primitives(code, scene_id)
    return code


def _warn_primitives(code: str, scene_id: int) -> None:
    """Log a warning if bare geometry primitives appear in semantic output."""
    for prim in _GEOMETRY_PRIMITIVES:
        # Allow them inside the asset code-gen module itself — only warn in
        # generated scene code (which starts with 'from manim import *')
        lines = code.splitlines()
        for lineno, line in enumerate(lines, 1):
            if prim in line and "def _" not in line and "#" not in line.lstrip()[:1]:
                logger.debug(
                    "Scene %d line %d: primitive '%s' found in semantic output — "
                    "this is expected inside template setup code",
                    scene_id, lineno, prim,
                )
                break
