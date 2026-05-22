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
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import logging

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

class PipelineRunRequest(BaseModel):
    topic: str
    subject: str
    apiKey: Optional[str] = None
    geminiApiKey: Optional[str] = None
    nvidiaApiKey: Optional[str] = None

# Ensure folders exist
USER_DATA_DIR = ROOT / "data" / "user"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

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
                return {
                    "total_sessions": 0,
                    "total_watch_time_seconds": 0,
                    "topics_covered": [],
                    "weak_topic_flags": [],
                    "weekly_contributions": [0, 0, 0, 0, 0, 0, 0],
                    "strength_matrix": {
                        "Mechanics": 50,
                        "Electromagnetism": 50,
                        "Thermodynamics": 50,
                        "Optics": 50,
                        "Modern Physics": 50
                    }
                }
            elif filename == "profile.json":
                return {
                    "learner_id": "default-learner",
                    "fullname": "Explorer",
                    "learning_goal": "Master Physics Concept Grounding",
                    "favourite_subject": "Mechanics",
                    "difficulty_level": "Standard",
                    "curriculum_board": "CBSE (Class 10)",
                    "exam_integration": [],
                    "weak_adapted_focus": True
                }
            return {}
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error loading {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_pipeline_task(session_id: str, topic: str, api_key: str | None, gemini_api_key: str | None = None, nvidia_api_key: str | None = None):
    job = ACTIVE_JOBS.get(session_id)
    if not job:
        return
        
    queue = job["queue"]
    
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
        
        explanation_package = None
        try:
            client = NvidiaClient()
            prompt = f"Topic: {topic}. Generate a structured educational blueprint with objectives, prerequisites, and real-world analogies."
            messages = [
                {"role": "system", "content": "You are a professional NCERT/CBSE Physics explanation assistant. Respond ONLY with a valid JSON object matching this schema: {\"topic\": \"...\", \"learning_objectives\": [\"...\"], \"core_explanation\": \"...\", \"analogies\": [\"...\"], \"prerequisites\": [\"...\"]}. Do not use markdown blocks or formatting fences."},
                {"role": "user", "content": prompt}
            ]
            raw_expl = client.chat_json(modules.config.NVIDIA_PLANNER_MODEL, messages, temperature=0.3, max_tokens=1024)
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

        # --- Stage 1: Storyboard ---
        await queue.put({"stage": "planning", "progress": 35, "message": "[1/8] Generating CBSE/NCERT-aligned pedagogical lesson storyboard..."})
        # Fresh asset registry for this run
        reset_registry()
        storyboard = build_storyboard(topic)
        
        await queue.put({
            "stage": "planning",
            "progress": 45,
            "message": "Syllabus storyboard arc finalized with 5 scenes!",
            "data": storyboard
        })
        await asyncio.sleep(0.5)

        # --- Stage 2: Semantic plans ---
        await queue.put({"stage": "generating", "progress": 55, "message": "[2/8] Creating visual scene blueprints and vector templates..."})
        plans = build_all_semantic_plans(storyboard)
        
        # --- Stage 3: Narration ---
        await queue.put({"stage": "generating", "progress": 65, "message": "[3/8] Writing detailed scene explanations and word cues..."})
        plans = write_all_narrations(plans)
        
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
            wav_path = ROOT / "data" / "audio" / f"scene_{sid}.wav"
            wav, _duration = synthesize(plan["narration"], wav_path)
            audio_paths[sid] = wav
            
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
                
        # Append new session details
        history_data["sessions"].insert(0, {
            "session_id": session_id,
            "topic": topic,
            "duration": "01:30",
            "date": time.strftime("%Y-%m-%d"),
            "video_path": video_url,
            "subject": job.get("subject", "Physics")
        })
        
        with open(history_file_path, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)

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
    
    # Store active job
    ACTIVE_JOBS[session_id] = {
        "topic": req.topic,
        "subject": req.subject,
        "api_key": req.apiKey,
        "gemini_api_key": req.geminiApiKey,
        "nvidia_api_key": req.nvidiaApiKey,
        "queue": asyncio.Queue(),
        "status": "queued"
    }
    
    # Add pipeline task to background executors
    background_tasks.add_task(
        run_pipeline_task, 
        session_id, 
        req.topic, 
        req.apiKey, 
        req.geminiApiKey, 
        req.nvidiaApiKey
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
