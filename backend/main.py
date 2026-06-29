"""
FastAPI Backend — Pushup Posture Detection
==========================================
Endpoints:
  GET  /health                   → server + model status
  POST /predict/image            → posture from uploaded image file
  POST /predict/capture          → posture from base64 camera capture
  WS   /ws/realtime/{session_id} → real-time frame stream
  GET  /session/new              → generate new session ID
"""

import base64
import json
import logging
import time
import uuid
from datetime import datetime

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import POSE_LANDMARKER_MODEL
from database import ensure_table, get_sessions, save_session
from inference import is_model_ready, predict_landmarks
from pose_utils import (
    extract_landmarks_from_bytes,
    extract_landmarks_from_bgr,
    get_body_alignment,
    get_elbow_angles,
    make_video_landmarker,
    is_valid_pushup_pose,
    get_landmark_coords,
)
from rep_counter import RepCounter

logger = logging.getLogger(__name__)


# ── App init ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Pushup Posture Detection API",
    description="MediaPipe Tasks-powered pushup form analysis backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup():
    ensure_table()


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class CaptureRequest(BaseModel):
    image_base64: str


class PredictionResult(BaseModel):
    label: str
    confidence: float
    probabilities: dict
    pose_detected: bool
    alignment: dict | None = None
    elbow_angles: dict | None = None
    message: str | None = None
    landmarks: list | None = None


class SaveSessionRequest(BaseModel):
    start_time:     str   # ISO-8601 string from frontend
    end_time:       str
    total_reps:     int
    correct_reps:   int
    incorrect_reps: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _decode_base64_image(b64: str) -> bytes:
    if "," in b64:
        b64 = b64.split(",", 1)[1]
    return base64.b64decode(b64)


def _form_feedback(label: str, left_angle: float, right_angle: float, alignment: dict) -> str:
    msgs = []
    if left_angle < 90 or right_angle < 90:
        msgs.append("Siku terlalu ditekuk")
    if alignment["hip_level_diff"] > 0.05:
        msgs.append("Pinggul tidak sejajar")
    if alignment["back_angle"] < 150:
        msgs.append("Punggung tidak lurus")
    if label == "correct" and not msgs:
        msgs.append("Postur pushup sudah benar!")
    elif label == "wrong" and not msgs:
        msgs.append("Postur kurang tepat, perbaiki form kamu")
    return " | ".join(msgs) if msgs else ""


def _build_prediction_result(image_bytes: bytes) -> PredictionResult:
    if not is_model_ready():
        raise HTTPException(503, "Model belum di-train. Jalankan train.py terlebih dahulu.")

    vec, lm_list = extract_landmarks_from_bytes(image_bytes)

    if vec is None or lm_list is None:
        return PredictionResult(
            label="unknown",
            confidence=0.0,
            probabilities={"correct": 0.0, "wrong": 0.0},
            pose_detected=False,
            message="Pose tidak terdeteksi. Pastikan seluruh tubuh terlihat dalam frame.",
        )

    prediction = predict_landmarks(vec)
    left_angle, right_angle = get_elbow_angles(lm_list)
    alignment = get_body_alignment(lm_list)
    
    # --- HYBRID LOGIC ---
    # Only override the MLP when ALL anatomical conditions confidently agree.
    # Thresholds are intentionally strict to avoid false positives from odd angles.
    is_plank_straight  = alignment["back_angle"]          >= 155   # very straight back
    is_hips_level      = alignment["hip_level_diff"]      <= 0.06  # hips not rotated
    is_not_piked       = alignment["hip_pike_ratio"]      <= 0.05  # butt not in the air
    is_body_line_ok    = abs(alignment["body_line_deviation"]) <= 0.07  # no sag or pike

    all_correct_anatomy = is_plank_straight and is_hips_level and is_not_piked and is_body_line_ok
    any_wrong_anatomy   = not is_plank_straight or not is_not_piked or not is_body_line_ok

    # Promote wrong→correct only when anatomy is unambiguously perfect
    if prediction["label"] == "wrong" and all_correct_anatomy:
        prediction["label"] = "correct"
        prediction["confidence"] = 0.82
        prediction["probabilities"]["correct"] = 0.82
        prediction["probabilities"]["wrong"] = 0.18
    # Demote correct→wrong when at least one clear anatomical violation exists
    elif prediction["label"] == "correct" and any_wrong_anatomy:
        prediction["label"] = "wrong"
        prediction["confidence"] = 0.85
        prediction["probabilities"]["correct"] = 0.15
        prediction["probabilities"]["wrong"] = 0.85
        
    msg = _form_feedback(prediction["label"], left_angle, right_angle, alignment)

    return PredictionResult(
        label=prediction["label"],
        confidence=prediction["confidence"],
        probabilities=prediction["probabilities"],
        pose_detected=True,
        alignment=alignment,
        elbow_angles={
            "left": round(left_angle, 1),
            "right": round(right_angle, 1),
            "average": round((left_angle + right_angle) / 2, 1),
        },
        message=msg or None,
        landmarks=get_landmark_coords(lm_list),
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model_ready": is_model_ready(),
        "timestamp": time.time(),
    }


@app.get("/session/new")
async def new_session():
    return {"session_id": str(uuid.uuid4())}


@app.post("/predict/image", response_model=PredictionResult)
async def predict_image(file: UploadFile = File(...)):
    """Accept uploaded image file (JPEG/PNG) and return posture prediction."""
    image_bytes = await file.read()
    return _build_prediction_result(image_bytes)


@app.post("/predict/capture", response_model=PredictionResult)
async def predict_capture(body: CaptureRequest):
    """Accept base64-encoded image from camera capture and return posture prediction."""
    try:
        image_bytes = _decode_base64_image(body.image_base64)
    except Exception:
        raise HTTPException(400, "Invalid base64 image data.")
    return _build_prediction_result(image_bytes)


@app.websocket("/ws/realtime/{session_id}")
async def realtime_ws(websocket: WebSocket, session_id: str):
    """
    WebSocket for real-time pushup detection + rep counting.

    Client → Server (JSON):
        { "frame": "<base64_jpeg>", "action": "frame" | "reset" }

    Server → Client (JSON):
        {
            "pose_detected": bool,
            "label": str,
            "confidence": float,
            "probabilities": {...},
            "rep_count": int,
            "pushup_state": str,
            "avg_elbow_angle": float|null,
            "elbow_angles": {...}|null,
            "alignment": {...}|null,
            "message": str|null,
            "timestamp": float,
            "landmarks": list|null
        }
    """
    await websocket.accept()

    counter = RepCounter()
    landmarker = make_video_landmarker()
    frame_ts = 0

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            action = data.get("action", "frame")

            if action == "reset":
                counter.reset()
                await websocket.send_json({
                    "pose_detected": False,
                    "label": "unknown",
                    "confidence": 0.0,
                    "probabilities": {"correct": 0.0, "wrong": 0.0},
                    "rep_count": 0,
                    "pushup_state": "idle",
                    "avg_elbow_angle": None,
                    "elbow_angles": None,
                    "alignment": None,
                    "message": "Counter reset",
                    "timestamp": time.time(),
                    "landmarks": None,
                })
                frame_ts = 0
                continue

            try:
                image_bytes = _decode_base64_image(data["frame"])
                nparr = np.frombuffer(image_bytes, np.uint8)
                bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            except Exception:
                await websocket.send_json({"error": "Invalid frame data"})
                continue

            if bgr is None:
                await websocket.send_json({"error": "Cannot decode frame"})
                continue

            frame_ts += 33  # ~30fps
            vec, lm_list = extract_landmarks_from_bgr(bgr, landmarker, frame_ts)

            if vec is None or lm_list is None:
                await websocket.send_json({
                    "pose_detected": False,
                    "label": "unknown",
                    "confidence": 0.0,
                    "probabilities": {"correct": 0.0, "wrong": 0.0},
                    "rep_count": counter.count,
                    "pushup_state": counter.state,
                    "avg_elbow_angle": counter.last_angle,
                    "elbow_angles": None,
                    "alignment": None,
                    "message": "Pose tidak terdeteksi",
                    "timestamp": time.time(),
                    "landmarks": None,
                })
                continue

            left_angle, right_angle = get_elbow_angles(lm_list)
            alignment = get_body_alignment(lm_list)
            
            # Check if actually in a pushup position
            if not is_valid_pushup_pose(lm_list):
                await websocket.send_json({
                    "pose_detected": False,
                    "label": "unknown",
                    "confidence": 0.0,
                    "probabilities": {"correct": 0.0, "wrong": 0.0},
                    "rep_count": counter.count,
                    "pushup_state": counter.state,
                    "avg_elbow_angle": counter.last_angle,
                    "elbow_angles": {
                        "left": round(left_angle, 1),
                        "right": round(right_angle, 1),
                    },
                    "alignment": {k: round(v, 4) for k, v in alignment.items()},
                    "message": "Silakan ambil posisi pushup (plank) untuk mulai",
                    "timestamp": time.time(),
                    "landmarks": get_landmark_coords(lm_list),
                })
                continue

            # --- ML prediction + hybrid override ---
            if is_model_ready():
                prediction = predict_landmarks(vec)
            else:
                prediction = {"label": "unknown", "confidence": 0.0, "probabilities": {"correct": 0.0, "wrong": 0.0}}

            is_plank_straight  = alignment["back_angle"]          >= 155
            is_hips_level      = alignment["hip_level_diff"]      <= 0.06
            is_not_piked       = alignment["hip_pike_ratio"]      <= 0.05
            is_body_line_ok    = abs(alignment["body_line_deviation"]) <= 0.07

            all_correct_anatomy = is_plank_straight and is_hips_level and is_not_piked and is_body_line_ok
            any_wrong_anatomy   = not is_plank_straight or not is_not_piked or not is_body_line_ok

            if prediction["label"] == "wrong" and all_correct_anatomy:
                prediction["label"] = "correct"
                prediction["confidence"] = 0.82
                prediction["probabilities"]["correct"] = 0.82
                prediction["probabilities"]["wrong"] = 0.18
            elif prediction["label"] == "correct" and any_wrong_anatomy:
                prediction["label"] = "wrong"
                prediction["confidence"] = 0.85
                prediction["probabilities"]["correct"] = 0.15
                prediction["probabilities"]["wrong"] = 0.85

            frame_label = prediction["label"] if prediction["label"] in ("correct", "wrong") else None

            # Pass frame_label so counter can accumulate it during the DOWN phase
            rep_state = counter.update(left_angle, right_angle, frame_label)

            msg = _form_feedback(prediction["label"], left_angle, right_angle, alignment)

            await websocket.send_json({
                "pose_detected":   True,
                "label":           rep_state["last_rep_label"] or prediction["label"],
                "confidence":      round(prediction["confidence"], 4),
                "probabilities":   {k: round(v, 4) for k, v in prediction["probabilities"].items()},
                "rep_count":       rep_state["count"],
                "correct_count":   rep_state["correct_count"],
                "incorrect_count": rep_state["incorrect_count"],
                "last_rep_label":  rep_state["last_rep_label"],
                "pushup_state":    rep_state["state"],
                "avg_elbow_angle": rep_state["avg_elbow_angle"],
                "elbow_angles": {
                    "left":  round(left_angle, 1),
                    "right": round(right_angle, 1),
                },
                "alignment":  {k: round(v, 4) for k, v in alignment.items()},
                "message":    msg or None,
                "timestamp":  time.time(),
                "landmarks":  get_landmark_coords(lm_list),
            })

    except WebSocketDisconnect:
        pass
    finally:
        landmarker.close()


@app.post("/session/save")
async def api_save_session(body: SaveSessionRequest):
    """Save a completed tracking session to MySQL."""
    try:
        start = datetime.fromisoformat(body.start_time)
        end   = datetime.fromisoformat(body.end_time)
    except ValueError:
        raise HTTPException(400, "Invalid datetime format. Use ISO-8601.")

    row_id = save_session(
        start_time=start,
        end_time=end,
        total_reps=body.total_reps,
        correct_reps=body.correct_reps,
        incorrect_reps=body.incorrect_reps,
    )
    if row_id is None:
        raise HTTPException(503, "Database tidak tersedia. Cek koneksi MySQL.")

    return {"status": "saved", "session_id": row_id}


@app.get("/sessions/history")
async def api_get_sessions(limit: int = 50):
    """Return the most recent tracking sessions from MySQL."""
    return {"sessions": get_sessions(limit=limit)}
