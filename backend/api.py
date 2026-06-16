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
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File
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
from modules.config import PATHS
from modules.llm.nvidia_client import NvidiaClient
from modules.planning.storyboard import build_storyboard
from modules.planning.semantic_plan import build_all_semantic_plans
from modules.planning.narration_writer import write_all_narrations
from modules.planning.asset_registry import reset_registry
from modules.planning.profile_context import format_learner_context

try:
    from modules.retrieval.pageindex_retriever import retrieve_curriculum_context
except Exception as e:
    logger = logging.getLogger("backend_api")
    logger.warning(f"Optional PageIndex dependency not available: {e}. Continuing with empty curriculum context.")
    def retrieve_curriculum_context(topic, document_tree, concept_graph, **kwargs):
        return {"nodes": []}

from modules.tts.piper_tts import synthesize
from modules.sync.sync_engine import synchronize_all
from modules.manim.semantic_compiler import semantic_compile_all
from modules.manim.renderer import render
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
    apiKey: Optional[str] = None
    geminiApiKey: Optional[str] = None
    nvidiaApiKey: Optional[str] = None
    learnerProfile: Optional[LearnerProfilePayload] = None

# Ensure folders exist
USER_DATA_DIR = ROOT / "data" / "user"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

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
        # --- Stage 0: Initializing explanation package ---
        await queue.put({"stage": "retrieving", "progress": 5, "message": "Contacting classroom agent pipeline..."})
        await asyncio.sleep(1.0)
        
        # Generate the explanation package using the LLM client
        await queue.put({"stage": "explaining", "progress": 15, "message": "Formulating pedagogical syllabus objectives..."})
        
        learner_context_block = format_learner_context(learner_profile, topic, subject)

        explanation_package = None
        try:
            client = NvidiaClient()
            prompt = (
                f"{learner_context_block}\n\n"
                f"Topic: {topic}. Generate a structured educational blueprint with "
                "learning objectives, prerequisites, and 2-3 DIFFERENT real-world analogies "
                "calibrated to the learner above. Each analogy must be distinct."
            )
            messages = [
                {"role": "system", "content": "You are a professional NCERT/CBSE explanation assistant. Personalize content to the LEARNER CONTEXT below. Respond ONLY with a valid JSON object matching this schema: {\"topic\": \"...\", \"learning_objectives\": [\"...\"], \"core_explanation\": \"...\", \"analogies\": [\"...\"], \"prerequisites\": [\"...\"]}. Do not use markdown blocks or formatting fences."},
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

        # --- Stage 1: Retrieve curriculum context ---
        import os
        from modules.rag.hierarchical_retriever import resolve
        from modules.planning.pedagogical_planner import compute_content_difficulty, compute_scaffolding, format_pedagogical_context
        from modules.learner.learner_model import LearnerModel
        
        # Load unified learner model (Stage 1, 4, 6)
        model = LearnerModel.from_dict(learner_profile or {})
        grade = model.grade
        theta = model.theta if model.theta is not None else 0.0
        
        # Load from pageindex_workspace if empty in results
        document_tree = {}
        concept_graph = {}
        
        workspace_dir = ROOT.parent / "pageindex_workspace"
        workspace_json_files = list(workspace_dir.glob("*.json"))
        structure_file = None
        for f in workspace_json_files:
            if f.name != "_meta.json":
                structure_file = f
                break
                
        if structure_file and structure_file.exists():
            try:
                with open(structure_file, "r", encoding="utf-8") as f:
                    document_tree = json.load(f)
                logger.info(f"Loaded curriculum document structure from workspace: {structure_file.name}")
            except Exception as e:
                logger.error(f"Error loading document structure from workspace: {e}")
                
        if not document_tree:
            structure_path = RESULTS_DIR / "structure.json"
            if structure_path.exists():
                with open(structure_path, "r", encoding="utf-8") as f:
                    document_tree = json.load(f)
                    
        graph_path = RESULTS_DIR / "concept_graph.json"
        if graph_path.exists():
            with open(graph_path, "r", encoding="utf-8") as f:
                concept_graph = json.load(f)
                
        retrieved_context = resolve(topic, document_tree, concept_graph, condition="C", grade=grade, theta=theta, learner_profile=learner_profile)
        
        # Build curriculum context string using both summary and content fields
        context_parts = []
        for n in retrieved_context.get("nodes", []):
            text_body = n.get("summary") or n.get("content") or n.get("text") or ""
            context_parts.append(f"Title: {n.get('title')}\nContent: {text_body}")
        curriculum_context = "\n\n".join(context_parts)
        
        logger.info("Retrieved curriculum context length=%s", len(curriculum_context))

        # --- Stage 1.5: Pedagogical Planning ---
        beta = compute_content_difficulty(retrieved_context, topic)
        scaffolding = compute_scaffolding(beta, theta)
        pedagogical_context = format_pedagogical_context(scaffolding)
        scene_count = scaffolding["scene_count"]

        # --- Stage 2: Storyboard ---
        await queue.put({
            "stage": "planning",
            "progress": 35,
            "message": f"[1/8] Generating {scene_count}-scene lesson storyboard..."
        })
        reset_registry()
        storyboard = build_storyboard(
            topic=topic,
            curriculum_context=curriculum_context,
            learner_profile=learner_profile,
            subject=subject,
            scene_count=scene_count,
            pedagogical_context=pedagogical_context
        )
        
        await queue.put({
            "stage": "planning",
            "progress": 45,
            "message": f"Syllabus storyboard arc finalized with {scene_count} scenes!",
            "data": storyboard
        })
        await asyncio.sleep(0.5)

        # --- Stage 2: Semantic plans ---
        await queue.put({"stage": "generating", "progress": 55, "message": "[2/8] Creating visual scene blueprints and vector templates..."})
        plans = build_all_semantic_plans(
            storyboard, learner_profile=learner_profile, topic=topic, subject=subject
        )

        # --- Stage 3: Narration ---
        await queue.put({"stage": "generating", "progress": 65, "message": "[3/8] Writing detailed scene explanations and word cues..."})
        plans = write_all_narrations(
            plans, learner_profile=learner_profile, topic=topic, subject=subject
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
        tts_speed = model.pedagogical_profile.get("tts_speed", 1.0)
        
        for plan in plans:
            sid = plan["scene_id"]
            wav_path = ROOT / "data" / "audio" / f"scene_{sid}.wav"
            wav, _duration, is_silent = synthesize(plan["narration"], wav_path, speed=tts_speed)
            audio_paths[sid] = wav
            if is_silent:
                logger.warning(f"TTS fallback to silent audio detected for scene {sid}!")
                await queue.put({
                    "stage": "tts",
                    "progress": 78,
                    "message": f"Warning: TTS synthesized silent audio for scene {sid}."
                })
            
        await queue.put({"stage": "tts", "progress": 80, "message": "Narration voiceovers generated successfully!"})
        await asyncio.sleep(0.5)

        # --- Stage 5: Sync Timelines ---
        await queue.put({"stage": "tts", "progress": 83, "message": "[5/8] Aligning audio timestamps and event scheduling..."})
        timelines = synchronize_all(plans, audio_paths)

        # --- Stage 6: Manim Compilation ---
        await queue.put({"stage": "generating", "progress": 87, "message": "[6/8] Compiling scenes into timed mathematical Python Manim code..."})
        manim_files = semantic_compile_all(plans, timelines)
        
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
            mp4 = render(manim_py, fallback_code=fallback_code)
            scene_mp4s.append(mp4)

        # --- Stage 8: Merge audio + video ---
        await queue.put({"stage": "generating", "progress": 96, "message": "[8/8] Merging high-quality scenes with voice overlays via FFmpeg..."})
        
        # Create a unique output directory under generated/session_id
        session_render_dir = ROOT / "data" / "renders" / session_id
        session_render_dir.mkdir(parents=True, exist_ok=True)
        final_mp4_path = session_render_dir / f"manim_{session_id}.mp4"
        
        scene_wavs = [audio_paths[p["scene_id"]] for p in plans]
        final = merge(scene_mp4s, scene_wavs, output=final_mp4_path)
        
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
    session_id = f"session_{int(time.time() * 1000)}"

    learner_profile_dict = req.learnerProfile.model_dump() if req.learnerProfile else None

    ACTIVE_JOBS[session_id] = {
        "topic": req.topic,
        "subject": req.subject,
        "api_key": req.apiKey,
        "gemini_api_key": req.geminiApiKey,
        "nvidia_api_key": req.nvidiaApiKey,
        "learner_profile": learner_profile_dict,
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


@app.post("/api/curriculum/upload")
async def upload_pdf(file: UploadFile = File(...)):
    from modules.config import PATHS
    import shutil
    import uuid
    
    doc_id = str(uuid.uuid4())
    filename = file.filename or f"doc_{doc_id}.pdf"
    file_path = PATHS["textbooks"] / filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"document_id": doc_id, "filename": filename, "path": str(file_path)}
    except Exception as e:
        logger.error(f"Error uploading PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/curriculum/index/{document_id}")
async def index_pdf(document_id: str, req: dict):
    from PageIndex.pageindex.client import PageIndexClient
    from modules.config import PATHS
    
    file_path = req.get("path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        workspace = str(PATHS["curriculum_results"])
        client = PageIndexClient(workspace=workspace)
        logger.info(f"Starting indexing for {file_path}")
        
        new_doc_id = client.index(file_path)
        
        from modules.rag.dependency_graph_builder import generate_dependency_graph
        doc_structure = client.get_document_structure(new_doc_id)
        if doc_structure:
            struct = json.loads(doc_structure)
            graph = generate_dependency_graph(struct)
            
            graph_path = PATHS["curriculum_results"] / "concept_graph.json"
            with open(graph_path, "w", encoding="utf-8") as f:
                json.dump(graph, f, indent=2)
                
        return {"status": "success", "document_id": new_doc_id}
    except Exception as e:
        logger.error(f"Error indexing PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/curriculum/documents")
async def list_documents():
    from PageIndex.pageindex.client import PageIndexClient
    from modules.config import PATHS
    try:
        workspace = str(PATHS["curriculum_results"])
        client = PageIndexClient(workspace=workspace)
        docs = []
        if hasattr(client, 'documents') and client.documents:
            docs = [doc for doc in client.documents.values()]
        return {"documents": docs}
    except Exception as e:
        return {"documents": []}

@app.get("/api/curriculum/structure/{document_id}")
async def get_structure(document_id: str):
    from PageIndex.pageindex.client import PageIndexClient
    from modules.config import PATHS
    try:
        workspace = str(PATHS["curriculum_results"])
        client = PageIndexClient(workspace=workspace)
        doc_structure = client.get_document_structure(document_id)
        return json.loads(doc_structure) if doc_structure else {}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/learner/theta")
async def get_theta():
    theta_path = USER_DATA_DIR / "theta.json"
    if not theta_path.exists():
        return {"theta": 0.0, "subject_thetas": {}}
    try:
        return json.loads(theta_path.read_text(encoding="utf-8"))
    except Exception:
        return {"theta": 0.0, "subject_thetas": {}}

@app.post("/api/learner/theta")
async def save_theta(req: dict):
    theta_path = USER_DATA_DIR / "theta.json"
    theta = float(req.get("theta", 0.0))
    subject = req.get("subject", "")
    
    data = {"theta": theta, "subject_thetas": {}}
    if theta_path.exists():
        try:
            data = json.loads(theta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
            
    data["theta"] = theta
    if "subject_thetas" not in data:
        data["subject_thetas"] = {}
        
    if subject:
        data["subject_thetas"][subject] = theta
        
    # Atomic save
    temp_path = theta_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    if theta_path.exists():
        theta_path.unlink()
    temp_path.rename(theta_path)
    
    # Also sync to profile.json to keep it as single source of truth
    profile_path = USER_DATA_DIR / "profile.json"
    if profile_path.exists():
        try:
            profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
            profile_data["theta"] = theta
            if "subject_thetas" not in profile_data:
                profile_data["subject_thetas"] = {}
            if "confidence_map" not in profile_data:
                profile_data["confidence_map"] = {}
            if subject:
                profile_data["subject_thetas"][subject] = theta
                # Map theta (-2 to 2) to 0-100 percentage
                percentage = int((theta + 2.0) / 4.0 * 100)
                profile_data["confidence_map"][subject] = max(0, min(100, percentage))
                
            temp_profile = profile_path.with_suffix(".tmp")
            with open(temp_profile, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=2)
            if profile_path.exists():
                profile_path.unlink()
            temp_profile.rename(profile_path)
        except Exception as e:
            logger.error(f"Failed to sync theta to profile.json: {e}")
            
    return {"success": True, "theta": theta}

@app.post("/api/diagnostic/start")
async def start_diagnostic(req: dict):
    from modules.learner.irt_engine import select_next_item
    subject = req.get("subject", "Physics")
    
    # Load profile to get grade
    profile_path = USER_DATA_DIR / "profile.json"
    grade = 11
    if profile_path.exists():
        try:
            profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
            grade_str = profile_data.get("academic_level", "class_11")
            grade_map = {
                "class_5": 5,
                "class_9": 9,
                "class_10": 10,
                "class_11": 11,
                "class_12": 12,
                "undergraduate": 15,
                "competitive": 12
            }
            grade = grade_map.get(grade_str, 11)
        except Exception:
            pass
            
    item = select_next_item(0.0, [], subject, grade)
    return {"item": item, "theta": 0.0, "answered_ids": []}

@app.post("/api/diagnostic/answer")
async def answer_diagnostic(req: dict):
    from modules.learner.irt_engine import select_next_item, estimate_theta
    responses = req.get("responses", [])
    subject = req.get("subject", "Physics")
    
    # Load profile to get grade
    profile_path = USER_DATA_DIR / "profile.json"
    grade = 11
    if profile_path.exists():
        try:
            profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
            grade_str = profile_data.get("academic_level", "class_11")
            grade_map = {
                "class_5": 5,
                "class_9": 9,
                "class_10": 10,
                "class_11": 11,
                "class_12": 12,
                "undergraduate": 15,
                "competitive": 12
            }
            grade = grade_map.get(grade_str, 11)
        except Exception:
            pass

    theta = estimate_theta(responses, subject, use_2pl=True)
    answered_ids = [r["item_id"] for r in responses]
    
    # Update topic-level confidence scores in profile.json
    if profile_path.exists():
        try:
            profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
            if "confidence_map" not in profile_data:
                profile_data["confidence_map"] = {}
                
            from modules.learner.irt_engine import get_item_by_id
            for resp in responses:
                item = get_item_by_id(resp["item_id"], subject)
                if item and "node_id" in item:
                    nid = item["node_id"]
                    diff = item.get("difficulty") or item.get("b") or 0.0
                    is_correct = resp.get("is_correct", 0)
                    
                    if is_correct == 1:
                        if diff < -0.5:
                            conf = 75
                        elif diff <= 0.5:
                            conf = 85
                        else:
                            conf = 95
                    else:
                        if diff < -0.5:
                            conf = 20
                        elif diff <= 0.5:
                            conf = 35
                        else:
                            conf = 50
                            
                    profile_data["confidence_map"][nid] = conf
            
            # Atomic save
            temp_profile = profile_path.with_suffix(".tmp")
            with open(temp_profile, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=2)
            if profile_path.exists():
                profile_path.unlink()
            temp_profile.rename(profile_path)
            logger.info("Successfully updated topic-level confidence map in profile.json")
        except Exception as e:
            logger.error(f"Failed to update topic confidences in profile.json: {e}")

    if len(responses) >= 7:
        await save_theta({"theta": theta, "subject": subject})
        return {"complete": True, "theta": theta}
        
    next_item = select_next_item(theta, answered_ids, subject, grade)
    if not next_item:
        await save_theta({"theta": theta, "subject": subject})
        return {"complete": True, "theta": theta}
        
    return {"complete": False, "item": next_item, "theta": theta, "answered_ids": answered_ids}

# ---------------------------------------------------------------------------
# Multimodal Input Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/input/understand-image")
async def understand_image(file: UploadFile = File(...)):
    """
    Accepts an uploaded image (screenshot, photo of textbook page, diagram, etc.)
    and uses Gemini Vision to extract the topic/question the user is asking about.
    Returns a plain-text string ready to be placed in the topic input field.
    """
    import base64
    import google.generativeai as genai
    from modules.config import GEMINI_API_KEY

    api_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set in environment.")

    try:
        image_bytes = await file.read()
        mime_type = file.content_type or "image/jpeg"

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        image_part = {
            "inline_data": {
                "mime_type": mime_type,
                "data": base64.b64encode(image_bytes).decode("utf-8")
            }
        }

        prompt = """You are an educational assistant. A student has shared an image with you.

Analyze this image carefully. It could be:
- A photo of a textbook page or chapter
- A screenshot of a question or problem
- A diagram, graph, or chart from a science/math topic
- A handwritten note with a question

Your task: Identify the educational topic or question the student wants to learn about.
Return ONLY a clear, concise topic/question string (10-25 words max) that can be used as a search query to generate an educational video lesson.

Examples of good outputs:
- "Newton's Laws of Motion and their applications"
- "Bohr's atomic model and electron energy levels"
- "Photosynthesis process in plants"
- "Quadratic equations and their solutions"

Return ONLY the topic string. No explanations, no preamble."""

        response = model.generate_content([prompt, image_part])
        extracted_topic = (response.text or "").strip()

        if not extracted_topic:
            raise ValueError("Could not extract a topic from the image.")

        return {"topic": extracted_topic, "success": True}

    except Exception as e:
        logger.error(f"Image understanding failed: {e}")
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")


@app.post("/api/input/transcribe-audio")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Accepts a recorded audio blob (webm/ogg/wav) and transcribes it using
    Google Gemini's audio understanding capability. Returns plain text.
    """
    import base64
    import google.generativeai as genai
    from modules.config import GEMINI_API_KEY

    api_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set in environment.")

    try:
        audio_bytes = await file.read()
        mime_type = file.content_type or "audio/webm"

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        audio_part = {
            "inline_data": {
                "mime_type": mime_type,
                "data": base64.b64encode(audio_bytes).decode("utf-8")
            }
        }

        prompt = """Transcribe the spoken words in this audio clip into plain text.
The speaker is a student asking about an educational topic.
Return ONLY the transcribed text, nothing else. No timestamps, no labels."""

        response = model.generate_content([prompt, audio_part])
        transcript = (response.text or "").strip()

        if not transcript:
            raise ValueError("Could not transcribe audio.")

        return {"transcript": transcript, "success": True}

    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.post("/api/chat")
async def chat_copilot(req: dict):
    topic = req.get("topic", "")
    query = req.get("query", "")
    curriculum_context = req.get("curriculum_context", "")
    learner_profile = req.get("learner_profile", {})
    history = req.get("history", [])
    
    # format learner context
    learner_context_block = format_learner_context(learner_profile, topic)
    
    system_prompt = (
        "You are Co-Pilot Classroom, a professional NCERT/CBSE AI learning assistant.\n"
        "You help students clarify doubts about their lessons. Answer their questions accurately, "
        "referencing the curriculum context where appropriate. Keep your answers brief (under 150 words) and helpful.\n"
        f"IMPORTANT: Match your explanation style (vocabulary level, equation density, analogies) to the following learner context:\n{learner_context_block}\n"
    )
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-5:]: # Keep last 5 messages for context
        role = "user" if msg.get("role") == "user" else "assistant"
        messages.append({"role": role, "content": msg.get("content", "")})
        
    messages.append({"role": "user", "content": f"Topic: {topic}\nCurriculum Evidence: {curriculum_context}\nQuestion: {query}"})
    
    try:
        client = NvidiaClient()
        response = client.chat(modules.config.NVIDIA_PLANNER_MODEL, messages, temperature=0.6)
        if response:
            return {"reply": response, "success": True}
    except Exception as e:
        logger.warning(f"Nvidia NIM chat failed, trying Gemini fallback: {e}")
        
    try:
        import google.generativeai as genai
        from modules.config import GEMINI_API_KEY
        api_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
        if api_key:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=system_prompt)
            contents = []
            for msg in messages[1:]:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [msg["content"]]})
            response = model.generate_content(contents)
            text = (response.text or "").strip()
            if text:
                return {"reply": text, "success": True}
    except Exception as e:
        logger.error(f"Gemini fallback chat failed: {e}")
        
    return {
        "reply": f"Based on {topic}, here is a clarification: standard physical principles apply. Can I help you with another concept or equation?",
        "success": True
    }

# Mount static folders for generated assets
app.mount("/generated", StaticFiles(directory=str(ROOT / "data" / "renders")), name="generated")
app.mount("/results", StaticFiles(directory=str(RESULTS_DIR)), name="results")

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
