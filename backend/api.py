#!/usr/bin/env python3
"""LearnOS Python API Backend Server.

Implements all required API endpoints for the LearnOS educational platform:
  - /api/health: health check and diagnostics
  - /api/persist: user data atomic persistence
  - /api/load/{filename}: load user configurations and histories
  - /api/pipeline/run: bootstrap the multi-stage video generation task
  - /api/pipeline/status/{sessionId}: SSE status stream
"""
import asyncio
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend_api")

# Define roots and add to python path
ROOT = Path(__file__).resolve().parent
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Dynamically prepend user-level Python Scripts and project local bin directory to system PATH.
# This ensures that Manim, FFmpeg, FFprobe, and Uvicorn executables can be resolved properly.
USER_SCRIPTS_PATH = r"C:\Users\malla\AppData\Roaming\Python\Python313\Scripts"
LOCAL_BIN_PATH = str(ROOT / "bin")

current_path = os.environ.get("PATH", "")
path_list = current_path.split(os.pathsep)

if USER_SCRIPTS_PATH not in path_list:
    path_list.insert(0, USER_SCRIPTS_PATH)
if LOCAL_BIN_PATH not in path_list:
    path_list.insert(0, LOCAL_BIN_PATH)

os.environ["PATH"] = os.pathsep.join(path_list)
logger.info(f"Dynamically injected execution paths. Updated PATH: {os.environ['PATH'][:300]}...")

import modules.config
from modules.config import PATHS, RenderWorkspace
from modules.llm.nvidia_client import NvidiaClient
from modules.planning.storyboard import build_storyboard
from modules.planning.semantic_plan import build_all_semantic_plans
from modules.planning.narration_writer import write_all_narrations
from modules.planning.asset_registry import reset_registry
from modules.planning.profile_context import format_learner_context
from modules.planning.grounding_validator import validate_storyboard_grounding, log_grounding_issues

from modules.retrieval.pageindex_retriever import (
    clear_artifacts_cache,
    indexed_folders,
    list_documents,
    resolve_document,
    retrieve_curriculum,
    validate_document_request,
)

from modules.tts.piper_tts import synthesize
from modules.sync.sync_engine import synchronize_all
from modules.manim.semantic_compiler import semantic_compile_all
from modules.manim.renderer import render, reset_llm_repair_state
from modules.video.ffmpeg_merge import merge

app = FastAPI(title="LearnOS Python API Backend")

# Enable CORS for all routes (to support local Vite client port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active jobs tracking for SSE status streaming
ACTIVE_JOBS: Dict[str, Dict[str, Any]] = {}

class PersistRequest(BaseModel):
    filename: str
    payload: Dict[str, Any]

class LearnerProfilePayload(BaseModel):
    learner_id: str = ""
    name: str = "Learner"
    academic_level: str = "class_11"
    exam_target: List[str] = []
    learning_style: str = "visual"
    pace_preference: str = "balanced"
    weak_subjects: List[str] = []
    confidence_map: Dict[str, int] = {}
    subject_for_lesson: str = "Physics"
    subject_confidence: int = 50

class PipelineRunRequest(BaseModel):
    topic: str
    subject: str
    documentId: Optional[str] = None
    apiKey: Optional[str] = None
    geminiApiKey: Optional[str] = None
    nvidiaApiKey: Optional[str] = None
    learnerProfile: Optional[LearnerProfilePayload] = None


class IndexCurriculumRequest(BaseModel):
    filename: str

# Ensure folders exist
USER_DATA_DIR = ROOT / "data" / "user"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CURRICULUM_RESULTS_DIR = ROOT.parent / "PageIndex" / "results"
PAGEINDEX_ROOT = ROOT.parent / "PageIndex"
PAGEINDEX_DOCUMENTS_DIR = PAGEINDEX_ROOT / "examples" / "documents"

DEFAULT_ANALYTICS = {
    "total_sessions": 0,
    "total_watch_time_seconds": 0,
    "topics_covered": [],
    "weak_topic_flags": [],
    "daily_activity": [],
    "subject_distribution": {},
    "weekly_contributions": [0, 0, 0, 0, 0, 0, 0],
    "strength_matrix": {
        "Mechanics": 50,
        "Electromagnetism": 50,
        "Thermodynamics": 50,
        "Optics": 50,
        "Modern Physics": 50,
    },
}

DEFAULT_SESSION_DURATION_SECONDS = 90


def _parse_duration_seconds(duration: str | int | float | None) -> int:
    if isinstance(duration, (int, float)):
        return int(duration)
    if not duration:
        return DEFAULT_SESSION_DURATION_SECONDS
    try:
        parts = str(duration).split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except (ValueError, TypeError):
        pass
    return DEFAULT_SESSION_DURATION_SECONDS


def _session_date_str(session: Dict[str, Any]) -> str:
    completed = session.get("completed_at") or session.get("date") or ""
    return str(completed)[:10]


def _weekday_index(date_str: str) -> int | None:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return (dt.weekday() + 1) % 7
    except ValueError:
        return None


def _load_user_json(filename: str, default: Dict[str, Any]) -> Dict[str, Any]:
    file_path = USER_DATA_DIR / filename
    if not file_path.exists():
        return dict(default)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return dict(default)


def _save_user_json(filename: str, payload: Dict[str, Any]) -> None:
    file_path = USER_DATA_DIR / filename
    temp_path = file_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    if file_path.exists():
        file_path.unlink()
    temp_path.rename(file_path)


def _normalize_history_session(session: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(session)
    date_str = _session_date_str(normalized)
    if date_str and not normalized.get("completed_at"):
        normalized["completed_at"] = f"{date_str}T12:00:00"
    if date_str and not normalized.get("date"):
        normalized["date"] = date_str
    if "duration_seconds" not in normalized:
        normalized["duration_seconds"] = _parse_duration_seconds(normalized.get("duration"))
    if "follow_up_count" not in normalized:
        normalized["follow_up_count"] = 0
    return normalized


def _build_analytics_from_history(history_data: Dict[str, Any]) -> Dict[str, Any]:
    analytics = dict(DEFAULT_ANALYTICS)
    sessions = [
        _normalize_history_session(s)
        for s in history_data.get("sessions", [])
    ]
    daily_map: Dict[str, int] = {}

    for session in sessions:
        duration_sec = session.get("duration_seconds", DEFAULT_SESSION_DURATION_SECONDS)
        analytics["total_watch_time_seconds"] += duration_sec

        topic = (session.get("topic") or "").strip()
        if topic and topic not in analytics["topics_covered"]:
            analytics["topics_covered"].append(topic)

        subject = session.get("subject") or "Physics"
        analytics["subject_distribution"][subject] = (
            analytics["subject_distribution"].get(subject, 0) + 1
        )

        date_str = _session_date_str(session)
        if date_str:
            daily_map[date_str] = daily_map.get(date_str, 0) + max(1, duration_sec // 60)
            weekday_idx = _weekday_index(date_str)
            if weekday_idx is not None:
                analytics["weekly_contributions"][weekday_idx] += 1

    analytics["total_sessions"] = len(sessions)
    analytics["daily_activity"] = [
        {"date": date_key, "minutes": minutes}
        for date_key, minutes in sorted(daily_map.items())
    ]
    return analytics


def _sync_analytics_from_history() -> Dict[str, Any]:
    history_data = _load_user_json("history.json", {"sessions": []})
    normalized_sessions = [
        _normalize_history_session(s) for s in history_data.get("sessions", [])
    ]
    if normalized_sessions != history_data.get("sessions", []):
        history_data["sessions"] = normalized_sessions
        _save_user_json("history.json", history_data)

    analytics = _build_analytics_from_history(history_data)
    _save_user_json("analytics.json", analytics)
    return analytics

@app.post("/api/persist")
async def persist_data(req: PersistRequest):
    try:
        filename = os.path.basename(req.filename)
        file_path = USER_DATA_DIR / filename
        
        # Safe atomic write
        temp_path = file_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(req.payload, f, ensure_ascii=False, indent=2)
        
        if file_path.exists():
            file_path.unlink()
        temp_path.rename(file_path)
        
        logger.info(f"Successfully persisted {filename} to user data")
        return {"success": True}
    except Exception as e:
        logger.error(f"Error persisting {req.filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/load/{filename}")
async def load_data(filename: str):
    try:
        filename = os.path.basename(filename)
        file_path = USER_DATA_DIR / filename
        if not file_path.exists():
            # Graceful default fallbacks matching client expectations
            if filename == "history.json":
                return {"sessions": []}
            elif filename == "analytics.json":
                history_data = _load_user_json("history.json", {"sessions": []})
                if history_data.get("sessions"):
                    return _sync_analytics_from_history()
                return dict(DEFAULT_ANALYTICS)
            elif filename == "profile.json":
                return {
                    "learner_id": "default-learner",
                    "name": "Explorer",
                    "academic_level": "class_11",
                    "exam_target": ["JEE"],
                    "learning_style": "visual",
                    "pace_preference": "balanced",
                    "weak_subjects": [],
                    "confidence_map": {
                        "Chemistry": 50,
                        "Physics": 50,
                        "Mathematics": 50
                    },
                    "created_at": "",
                    "updated_at": ""
                }
            return {}
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if filename == "analytics.json":
            history_data = _load_user_json("history.json", {"sessions": []})
            history_count = len(history_data.get("sessions", []))
            if history_count and (data.get("total_sessions", 0) < history_count):
                return _sync_analytics_from_history()

        if filename == "history.json":
            sessions = data.get("sessions", [])
            normalized = [_normalize_history_session(s) for s in sessions]
            if normalized != sessions:
                data["sessions"] = normalized
                _save_user_json("history.json", data)

        return data
    except Exception as e:
        logger.error(f"Error loading {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_pipeline_task(
    session_id: str,
    topic: str,
    api_key: str | None,
    gemini_api_key: str | None = None,
    nvidia_api_key: str | None = None,
    learner_profile: Optional[Dict[str, Any]] = None,
    subject: str = "Physics",
    document_id: str | None = None,
    resolution=None,
):
    job = ACTIVE_JOBS.get(session_id)
    if not job:
        return

    queue = job["queue"]

    if learner_profile is None:
        profile_path = USER_DATA_DIR / "profile.json"
        if profile_path.exists():
            try:
                learner_profile = json.loads(profile_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to read learner profile from disk: {e}")
                learner_profile = None

    if learner_profile:
        logger.info(
            "Pipeline personalization: learner=%s level=%s style=%s pace=%s subj_conf=%s",
            learner_profile.get("learner_id", "?"),
            learner_profile.get("academic_level", "?"),
            learner_profile.get("learning_style", "?"),
            learner_profile.get("pace_preference", "?"),
            learner_profile.get("subject_confidence", "?"),
        )

    reset_llm_repair_state()
    workspace = RenderWorkspace.make(session_id)
    logger.info(
        "[SESSION] isolated workspace=%s force_regenerate=True",
        workspace.root,
    )
    # 1. Update API Keys based on request payload parameters
    g_key = gemini_api_key or api_key
    n_key = nvidia_api_key or api_key
    
    if g_key:
        modules.config.GEMINI_API_KEY = g_key
        os.environ["GEMINI_API_KEY"] = g_key
    if n_key:
        modules.config.NVIDIA_API_KEY = n_key
        os.environ["NVIDIA_API_KEY"] = n_key
        
    logger.info(f"Dynamically set LLM keys: GEMINI_API_KEY={'set' if g_key else 'not set'} | NVIDIA_API_KEY={'set' if n_key else 'not set'}")
    
    try:
        # --- Stage 0: Retrieve curriculum context ---
        await queue.put({"stage": "retrieving", "progress": 5, "message": "Searching curriculum structure and textbook evidence..."})
        if resolution is None:
            resolution = resolve_document(document_id, subject)
        logger.info(
            "[RESOLUTION] pipeline topic=%r requested_document_id=%r subject=%r "
            "resolved_folder=%r source=%s llm_only=%s indexed=%s",
            topic,
            document_id,
            subject,
            resolution.folder,
            resolution.source,
            resolution.llm_only,
            resolution.indexed,
        )

        if resolution.llm_only:
            logger.warning(
                "[RESOLUTION][DEGRADED] -> LLM-only mode for topic=%r reason=%s",
                topic,
                resolution.reason,
            )
            await queue.put({
                "stage": "retrieving",
                "progress": 8,
                "message": (
                    "No indexed textbook for this subject; continuing with "
                    "LLM-only lesson generation..."
                ),
            })

        curriculum_result = retrieve_curriculum(topic, resolution=resolution)

        curriculum_sections = curriculum_result.get("sections", [])
        curriculum_context = curriculum_result.get("context_text", "")
        _resolution_source = curriculum_result.get("resolution_source", "unknown")
        _resolved_document_id = curriculum_result.get("document_id") or resolution.folder or "llm_only"
        logger.info(
            "Retrieved %d curriculum sections",
            len(curriculum_sections)
        )
        logger.info(
            "Curriculum context chars=%d",
            len(curriculum_context)
        )
        if curriculum_context:
            logger.info(
                "Curriculum preview:\n%s",
                curriculum_context[:1500]
            )
        if curriculum_sections:
            section_log = [
                {
                    "title": s.get("title"),
                    "breadcrumb": s.get("breadcrumb"),
                    "pages": f"{s.get('start_page')}-{s.get('end_page')}",
                    "score": round(s.get("score", 0), 3),
                    "keywords": s.get("keywords", [])[:5],
                    "artifacts_dir": s.get("artifacts_dir"),
                }
                for s in curriculum_sections
            ]
            logger.info(
                "curriculum_sections topic=%r matched=%d sections=%s",
                topic, len(curriculum_sections), section_log,
            )
        else:
            logger.warning("curriculum_sections topic=%r matched=0 (no sections found)", topic)
        logger.info("curriculum_context topic=%r length=%s", topic, len(curriculum_context))

        # Write retrieval audit log for observability / debugging
        try:
            retrieval_audit = {
                "session_id": session_id,
                "topic": topic,
                "subject": subject,
                "document_id": _resolved_document_id,
                "resolution_source": _resolution_source,
                "requested_document_id": document_id,
                "sections": [
                    {
                        "title": s.get("title"),
                        "node_id": s.get("node_id"),
                        "score": round(s.get("score", 0), 3),
                        "breadcrumb": s.get("breadcrumb"),
                        "pages": f"{s.get('start_page')}-{s.get('end_page')}",
                        "semantic_tags": s.get("semantic_tags", []),
                        "visualizable_elements": s.get("visualizable_elements", []),
                    }
                    for s in curriculum_sections
                ],
            }
            (PATHS["json"] / "retrieval_audit.json").write_text(
                json.dumps(retrieval_audit, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as _audit_err:
            logger.warning("Failed to write retrieval_audit.json: %s", _audit_err)

        # --- Stage 1: Generate explanation package ---
        await queue.put({"stage": "explaining", "progress": 15, "message": "Formulating pedagogical syllabus objectives..."})

        learner_context_block = format_learner_context(learner_profile, topic, subject)

        explanation_package = None
        try:
            client = NvidiaClient()
            prompt = (
                f"CURRICULUM CONTEXT:\n{curriculum_context}\n\n"
                f"{learner_context_block}\n\n"
                f"Topic: {topic}. Generate a structured educational blueprint with "
                "learning objectives, prerequisites, and 2-3 DIFFERENT real-world analogies "
                "calibrated to the learner above. Each analogy must be distinct."
            )
            messages = [
                {"role": "system", "content": "You are a professional NCERT/CBSE explanation assistant. Use the curriculum context as the primary source of truth. Personalize content to the LEARNER CONTEXT below. Respond ONLY with a valid JSON object matching this schema: {\"topic\": \"...\", \"learning_objectives\": [\"...\"], \"core_explanation\": \"...\", \"analogies\": [\"...\"], \"prerequisites\": [\"...\"]}. Do not use markdown blocks or formatting fences."},
                {"role": "user", "content": prompt}
            ]
            raw_expl = client.chat_json(modules.config.NVIDIA_PLANNER_MODEL, messages, temperature=0.4, max_tokens=1024)
            if isinstance(raw_expl, dict) and "topic" in raw_expl:
                explanation_package = raw_expl
        except Exception as e:
            logger.warning(f"Failed to generate structured explanation package: {e}")

        if not explanation_package:
            # Fallback values
            explanation_package = {
                "topic": topic,
                "learning_objectives": [
                    f"Understand the core physics principles of {topic}.",
                    f"Analyze real-world scenarios representing {topic}."
                ],
                "core_explanation": f"This lesson explores {topic}. We examine the fundamental definitions, equations, and mechanics involved.",
                "analogies": [
                    f"Like a sliding puck on smooth ice representing frictionless motion, {topic} describes how systems behave under physical constraints."
                ],
                "prerequisites": ["Basic Physical Quantities", "Concept of Forces"]
            }

        await queue.put({
            "stage": "explaining",
            "progress": 25,
            "message": "Pedagogical explanation summary synthesized!",
            "data": explanation_package
        })
        await asyncio.sleep(0.5)

        # --- Stage 2: Storyboard ---
        await queue.put({
            "stage": "planning",
            "progress": 35,
            "message": "[1/8] Generating CBSE/NCERT-aligned pedagogical lesson storyboard..."
        })
        reset_registry()
        storyboard = build_storyboard(
            topic=topic,
            curriculum_context=curriculum_context,
            curriculum_sections=curriculum_sections,
            learner_profile=learner_profile,
            subject=subject
        )
        
        # Grounding validation — warns if storyboard scenes don't overlap with curriculum
        try:
            grounding_issues = validate_storyboard_grounding(
                storyboard, curriculum_sections, strict=False
            )
            log_grounding_issues(grounding_issues, logger, topic=topic)
            if grounding_issues:
                # Save issues to data/json for debugging
                (PATHS["json"] / "grounding_issues.json").write_text(
                    json.dumps(grounding_issues, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
        except Exception as _gv_err:
            logger.warning("Grounding validator error (non-fatal): %s", _gv_err)

        await queue.put({
            "stage": "planning",
            "progress": 45,
            "message": "Syllabus storyboard arc finalized with 5 scenes!",
            "data": storyboard
        })
        await asyncio.sleep(0.5)

        # --- Stage 2: Semantic plans ---
        await queue.put({"stage": "generating", "progress": 55, "message": "[2/8] Creating visual scene blueprints and vector templates..."})
        plans = build_all_semantic_plans(
            storyboard,
            curriculum_context=curriculum_context,
            curriculum_sections=curriculum_sections,
            learner_profile=learner_profile,
            topic=topic,
            subject=subject,
        )

        # --- Stage 3: Narration ---
        await queue.put({"stage": "generating", "progress": 65, "message": "[3/8] Writing detailed scene explanations and word cues..."})
        plans = write_all_narrations(
            plans,
            curriculum_context=curriculum_context,
            curriculum_sections=curriculum_sections,
            learner_profile=learner_profile,
            topic=topic,
            subject=subject,
        )
        
        # Concatenate script text for the script inspector
        concatenated_script = ""
        for p in plans:
            concatenated_script += f"# Scene {p['scene_id']}: {p.get('title', '')}\n"
            concatenated_script += f"# Template: {p['concept_template']}\n"
            concatenated_script += f"Narration: \"{p.get('narration', '')}\"\n\n"
            concatenated_script += "Events:\n"
            for ev in p.get("events", []):
                concatenated_script += f"  - {ev.get('type')}: {ev.get('anchor_phrase')}\n"
            concatenated_script += "\n" + "="*40 + "\n\n"
            
        await queue.put({
            "stage": "generating",
            "progress": 70,
            "message": "Audio narration scripts successfully drafted!",
            "data": {"script": concatenated_script}
        })
        await asyncio.sleep(0.5)

        # --- Stage 4: Synthesize Audio ---
        await queue.put({"stage": "tts", "progress": 75, "message": "[4/8] Running offline TTS audio synthesizer per scene..."})
        audio_paths = {}
        for plan in plans:
            sid = plan["scene_id"]
            wav_path = workspace.audio_dir / f"scene_{sid}.wav"
            wav, _duration = synthesize(plan["narration"], wav_path)
            audio_paths[sid] = wav
            
        await queue.put({"stage": "tts", "progress": 80, "message": "Narration voiceovers generated successfully!"})
        await asyncio.sleep(0.5)

        # --- Stage 5: Sync Timelines ---
        await queue.put({"stage": "tts", "progress": 83, "message": "[5/8] Aligning audio timestamps and event scheduling..."})
        timelines = synchronize_all(plans, audio_paths, workspace=workspace)

        # --- Stage 6: Manim Compilation ---
        await queue.put({"stage": "generating", "progress": 87, "message": "[6/8] Compiling scenes into timed mathematical Python Manim code..."})
        manim_files = semantic_compile_all(
            plans, timelines, workspace=workspace, force_regenerate=True
        )
        
        # Read the generated Manim code and concatenate for Script Inspector!
        manim_code_combined = ""
        for manim_py, fallback_code in manim_files:
            if manim_py.exists():
                with open(manim_py, "r", encoding="utf-8") as f:
                    manim_code_combined += f.read() + "\n\n# " + "="*60 + "\n\n"
            else:
                manim_code_combined += fallback_code + "\n\n# " + "="*60 + "\n\n"
                
        # Send the generated code to update the visual script panel
        await queue.put({
            "stage": "generating",
            "progress": 90,
            "message": "Python Manim math scripts generated!",
            "data": {"script": manim_code_combined}
        })
        await asyncio.sleep(0.5)

        # --- Stage 7: Render scenes ---
        await queue.put({"stage": "generating", "progress": 92, "message": "[7/8] Spawning Manim Community engine to render vector animations..."})
        scene_mp4s = []
        for manim_py, fallback_code in manim_files:
            mp4 = render(manim_py, fallback_code=fallback_code, workspace=workspace)
            scene_mp4s.append(mp4)

        # --- Stage 8: Merge audio + video ---
        await queue.put({"stage": "generating", "progress": 96, "message": "[8/8] Merging high-quality scenes with voice overlays via FFmpeg..."})

        final_mp4_path = workspace.root / f"manim_{session_id}.mp4"

        scene_wavs = [audio_paths[p["scene_id"]] for p in plans]
        final = merge(scene_mp4s, scene_wavs, output=final_mp4_path, workspace=workspace)
        
        video_url = f"/generated/{session_id}/manim_{session_id}.mp4"

        # Construct complete output payload
        final_payload = {
            "video_url": video_url,
            "explanation_package": explanation_package,
            "scene_plan": plans,
            "script": manim_code_combined
        }
        
        # Save session file in user data
        session_file_path = USER_DATA_DIR / "session.json"
        with open(session_file_path, "w", encoding="utf-8") as f:
            json.dump({
                "session_id": session_id,
                "topic_query": topic,
                "topic_resolved": topic,
                "pipeline_stage": "complete",
                "video_url": video_url,
                "explanation_package": explanation_package,
                "scene_plan": plans,
                "script": manim_code_combined,
                "notes": f"# Notes: {topic}\n\n## Summary\n{explanation_package['core_explanation']}\n\n## Analogies\n* " + "\n* ".join(explanation_package['analogies'])
            }, f, ensure_ascii=False, indent=2)

        # Save to history file
        history_file_path = USER_DATA_DIR / "history.json"
        history_data = {"sessions": []}
        if history_file_path.exists():
            try:
                with open(history_file_path, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
            except Exception:
                pass
                
        completed_at = datetime.now().isoformat()
        session_date = completed_at[:10]
        duration_seconds = DEFAULT_SESSION_DURATION_SECONDS
        session_subject = job.get("subject", "Physics")

        history_data["sessions"].insert(0, {
            "session_id": session_id,
            "topic": topic,
            "duration": "01:30",
            "duration_seconds": duration_seconds,
            "date": session_date,
            "completed_at": completed_at,
            "video_path": video_url,
            "subject": session_subject,
            "follow_up_count": 0,
        })

        with open(history_file_path, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)

        _sync_analytics_from_history()

        # Finish!
        await queue.put({
            "stage": "complete",
            "progress": 100,
            "message": "AI micro-lecture rendered completely!",
            "data": final_payload
        })
        
    except Exception as e:
        logger.error(f"Error in pipeline generation: {e}", exc_info=True)
        await queue.put({
            "stage": "error",
            "progress": 100,
            "message": f"Pipeline generation failed: {str(e)}",
            "data": None
        })

@app.post("/api/pipeline/run")
async def start_pipeline(req: PipelineRunRequest, background_tasks: BackgroundTasks):
    session_id = f"session_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

    resolution_preview = resolve_document(req.documentId, req.subject)
    if resolution_preview.llm_only:
        logger.warning(
            "Pipeline %s will run LLM-only: %s",
            session_id,
            resolution_preview.reason,
        )
    elif resolution_preview.source == "newest":
        logger.warning(
            "Pipeline %s document warning: no document_id or subject; using %r",
            session_id,
            resolution_preview.folder,
        )
    logger.info(
        "Pipeline %s queued topic=%r subject=%r documentId=%r will_resolve=%r via=%s llm_only=%s",
        session_id,
        req.topic,
        req.subject,
        req.documentId,
        resolution_preview.folder,
        resolution_preview.source,
        resolution_preview.llm_only,
    )

    learner_profile_dict = req.learnerProfile.model_dump() if req.learnerProfile else None

    ACTIVE_JOBS[session_id] = {
        "topic": req.topic,
        "subject": req.subject,
        "document_id": req.documentId,
        "api_key": req.apiKey,
        "gemini_api_key": req.geminiApiKey,
        "nvidia_api_key": req.nvidiaApiKey,
        "learner_profile": learner_profile_dict,
        "resolution": resolution_preview,
        "queue": asyncio.Queue(),
        "status": "queued"
    }

    background_tasks.add_task(
        run_pipeline_task,
        session_id,
        req.topic,
        req.apiKey,
        req.geminiApiKey,
        req.nvidiaApiKey,
        learner_profile_dict,
        req.subject,
        req.documentId,
        resolution_preview,
    )

    return {"sessionId": session_id, "resolvedTopic": req.topic}

@app.get("/api/pipeline/status/{session_id}")
async def get_pipeline_status(session_id: str):
    job = ACTIVE_JOBS.get(session_id)
    if not job:
        raise HTTPException(status_code=404, detail="Session not found")
        
    async def sse_event_generator():
        queue = job["queue"]
        while True:
            try:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
                if event["stage"] in ("complete", "error"):
                    break
            except Exception as e:
                logger.error(f"Error inside SSE generator: {e}")
                break
                
    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")

@app.get("/api/curriculum/documents")
async def curriculum_documents():
    return {
        "documents": list_documents(),
        "indexed_folders": indexed_folders(),
    }


@app.get("/api/curriculum/validate")
async def curriculum_validate(documentId: Optional[str] = None, subject: Optional[str] = None):
    """Debug endpoint: preview how document_id/subject will resolve before pipeline run."""
    return validate_document_request(documentId, subject)


@app.post("/api/curriculum/index")
async def curriculum_index(req: IndexCurriculumRequest):
    filename = req.filename.strip()
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    pdf_path = PAGEINDEX_DOCUMENTS_DIR / filename
    if not pdf_path.is_file():
        raise HTTPException(status_code=404, detail=f"PDF not found in examples/documents: {filename}")

    script_path = PAGEINDEX_ROOT / "run_pageindex.py"
    if not script_path.is_file():
        raise HTTPException(status_code=500, detail="PageIndex run_pageindex.py not found")

    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            [
                sys.executable,
                str(script_path),
                "--pdf_path",
                str(pdf_path),
                "--force-reindex",
            ],
            cwd=str(PAGEINDEX_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=3600,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}") from e

    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "")[-2000:]
        raise HTTPException(status_code=500, detail=f"PageIndex exited with {result.returncode}: {tail}")

    clear_artifacts_cache()
    return {
        "status": "indexed",
        "filename": filename,
        "stdout_tail": (result.stdout or "")[-1500:],
    }


@app.get("/api/pageindex/health")
async def pageindex_health():
    """Check PageIndex artifact freshness and return tree summary."""
    from modules.retrieval.pageindex_retriever import PDF_PATH, _get_artifacts
    try:
        arts = _get_artifacts()
    except FileNotFoundError as e:
        return {
            "status": "not_indexed",
            "message": str(e),
            "pdf": str(PDF_PATH),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

    available = arts.list_artifacts()
    structure_data = arts.load("structure.json") or {}
    nodes = arts.walk_nodes()
    chapters = [n for n in nodes if n.get("content_type") == "chapter"]
    validation = arts.load("semantic_validation.json") or {}
    metrics = arts.load("pipeline_metrics.json") or {}

    return {
        "status": "ready",
        "pdf": str(PDF_PATH),
        "results_dir": str(arts.results_dir),
        "artifacts": available,
        "node_count": len(nodes),
        "chapter_count": len(chapters),
        "chapters": [
            {
                "title": c.get("title"),
                "pages": f"{c.get('start_page') or c.get('start_index')}-{c.get('end_page') or c.get('end_index')}",
                "children": len(c.get("nodes") or c.get("children") or []),
            }
            for c in chapters
        ],
        "validation_passed": validation.get("passed"),
        "validation_failures": validation.get("failures", []),
        "validation_advisory": validation.get("advisory", []),
        "total_runtime_s": metrics.get("total_runtime_s"),
    }


@app.get("/api/health")
async def health_check():
    import shutil
    ffmpeg_avail = shutil.which("ffmpeg") is not None
    ffprobe_avail = shutil.which("ffprobe") is not None
    manim_avail = shutil.which("manim") is not None
    piper_avail = shutil.which("piper") is not None
    
    return {
        "status": "healthy",
        "service": "LearnOS Python Pipeline API",
        "diagnostics": {
            "ffmpeg": "Available" if ffmpeg_avail else "Missing",
            "ffprobe": "Available" if ffprobe_avail else "Missing",
            "manim": "Available" if manim_avail else "Missing",
            "piper": "Available" if piper_avail else "Missing"
        }
    }

# Mount static folders for generated assets
app.mount("/generated", StaticFiles(directory=str(ROOT / "data" / "renders")), name="generated")
_results_mount = CURRICULUM_RESULTS_DIR if CURRICULUM_RESULTS_DIR.is_dir() else RESULTS_DIR
app.mount("/results", StaticFiles(directory=str(_results_mount)), name="results")

if __name__ == "__main__":
    import uvicorn
    logger.info("=" * 80)
    logger.info("LearnOS Python API Server")
    logger.info("=" * 80)
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=5000,
        log_level="info",
        reload=False
    )
