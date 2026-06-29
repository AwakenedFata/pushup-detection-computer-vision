import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.vision import PoseLandmarkerOptions, RunningMode
from typing import Optional

from config import POSE_LANDMARKER_MODEL

# MediaPipe pose landmark indices
LEFT_SHOULDER = 11;  RIGHT_SHOULDER = 12
LEFT_ELBOW    = 13;  RIGHT_ELBOW    = 14
LEFT_WRIST    = 15;  RIGHT_WRIST    = 16
LEFT_HIP      = 23;  RIGHT_HIP      = 24
LEFT_ANKLE    = 27;  RIGHT_ANKLE    = 28


def _make_landmarker(running_mode: RunningMode) -> mp_vision.PoseLandmarker:
    opts = PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=POSE_LANDMARKER_MODEL),
        running_mode=running_mode,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return mp_vision.PoseLandmarker.create_from_options(opts)


def _to_vector(pose_landmarks) -> np.ndarray:
    features = []
    for lm in pose_landmarks:
        features.extend([lm.x, lm.y, lm.z, getattr(lm, "visibility", 0.0)])
    return np.array(features, dtype=np.float32)


def _coords(lm_list, idx: int) -> list:
    lm = lm_list[idx]
    return [lm.x, lm.y, lm.z]


def _angle(a, b, c) -> float:
    """Angle in degrees at joint B formed by points A-B-C (2D projection)."""
    a, b, c = np.array(a[:2]), np.array(b[:2]), np.array(c[:2])
    ba, bc = a - b, c - b
    cos = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    return float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))


# ---------------------------------------------------------------------------
# Public extraction functions
# ---------------------------------------------------------------------------

def extract_landmarks_from_bytes(
    image_bytes: bytes,
) -> tuple[Optional[np.ndarray], Optional[list]]:
    """
    Decode image bytes (JPEG/PNG) and extract pose landmarks.

    Returns:
        (feature_vector [132-dim], raw_landmark_list) or (None, None)
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if bgr is None:
        return None, None

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    with _make_landmarker(RunningMode.IMAGE) as landmarker:
        result = landmarker.detect(mp_image)

    if not result.pose_landmarks:
        return None, None

    lm_list = result.pose_landmarks[0]
    return _to_vector(lm_list), lm_list


def extract_landmarks_from_bgr(
    bgr_frame: np.ndarray,
    landmarker: mp_vision.PoseLandmarker,
    ts_ms: int,
) -> tuple[Optional[np.ndarray], Optional[list]]:
    """
    Extract landmarks from a BGR frame using a VIDEO-mode landmarker.
    ts_ms must be monotonically increasing across calls on the same instance.

    Returns:
        (feature_vector [132-dim], raw_landmark_list) or (None, None)
    """
    rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = landmarker.detect_for_video(mp_image, ts_ms)

    if not result.pose_landmarks:
        return None, None

    lm_list = result.pose_landmarks[0]
    return _to_vector(lm_list), lm_list


def make_video_landmarker() -> mp_vision.PoseLandmarker:
    """Create a reusable VIDEO-mode landmarker (caller is responsible for .close())."""
    return _make_landmarker(RunningMode.VIDEO)


def sample_video_landmarks(video_path: str, sample_rate: int = 5) -> list[np.ndarray]:
    """
    Extract sampled landmark vectors from a video file.
    Used only during dataset preprocessing (data_pipeline.py).

    Returns:
        List of 132-dim feature vectors.
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    results = []
    frame_idx = 0

    with _make_landmarker(RunningMode.VIDEO) as landmarker:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % sample_rate == 0:
                ts_ms = int((frame_idx / fps) * 1000)
                vec, _ = extract_landmarks_from_bgr(frame, landmarker, ts_ms)
                if vec is not None:
                    results.append(vec)
            frame_idx += 1

    cap.release()
    return results


# ---------------------------------------------------------------------------
# Form analysis helpers
# ---------------------------------------------------------------------------

def get_elbow_angles(lm_list) -> tuple[float, float]:
    """Return (left_elbow_angle, right_elbow_angle) in degrees."""
    left = _angle(
        _coords(lm_list, LEFT_SHOULDER),
        _coords(lm_list, LEFT_ELBOW),
        _coords(lm_list, LEFT_WRIST),
    )
    right = _angle(
        _coords(lm_list, RIGHT_SHOULDER),
        _coords(lm_list, RIGHT_ELBOW),
        _coords(lm_list, RIGHT_WRIST),
    )
    return left, right


def get_body_alignment(lm_list) -> dict:
    """
    Compute alignment metrics for form feedback.

    Returns:
        hip_level_diff:      absolute Y-axis difference between hips (normalised 0-1).
        back_angle:          shoulder-hip-ankle angle in degrees (180 = perfectly straight).
        hip_pike_ratio:      how much the hip is elevated above the shoulder-ankle line.
                             >0.06 = hips piked up (butt in the air) — wrong form.
        body_line_deviation: max perpendicular distance (normalised) of hip from the
                             shoulder→ankle line. Sensitive to both sag and pike.
    """
    hip_level_diff = abs(lm_list[LEFT_HIP].y - lm_list[RIGHT_HIP].y)

    shoulder_mid = np.mean([_coords(lm_list, LEFT_SHOULDER), _coords(lm_list, RIGHT_SHOULDER)], axis=0)
    hip_mid      = np.mean([_coords(lm_list, LEFT_HIP),      _coords(lm_list, RIGHT_HIP)],      axis=0)
    ankle_mid    = np.mean([_coords(lm_list, LEFT_ANKLE),     _coords(lm_list, RIGHT_ANKLE)],    axis=0)

    back_angle = _angle(shoulder_mid, hip_mid, ankle_mid)

    # Perpendicular distance of hip_mid from the shoulder→ankle line (2-D)
    s = np.array(shoulder_mid[:2])
    a = np.array(ankle_mid[:2])
    h = np.array(hip_mid[:2])
    line_len = np.linalg.norm(a - s) + 1e-8
    # Signed cross-product: negative Y = hip is above the line (pike), positive = sag
    cross = (a[0] - s[0]) * (s[1] - h[1]) - (s[0] - h[0]) * (a[1] - s[1])
    body_line_deviation = float(cross / line_len)       # normalised, signed
    hip_pike_ratio      = float(max(0.0, -body_line_deviation))  # positive when piked

    return {
        "hip_level_diff":      float(hip_level_diff),
        "back_angle":          float(back_angle),
        "hip_pike_ratio":      hip_pike_ratio,
        "body_line_deviation": body_line_deviation,
    }


def is_valid_pushup_pose(lm_list) -> bool:
	"""
	Heuristic to check if the person is actually in a pushup (plank) position.
	Prevents random arm movements from being counted as pushups.
	"""
	# Wrists must be physically below shoulders in the image (Y grows downwards)
	wrists_below = (lm_list[LEFT_WRIST].y > lm_list[LEFT_SHOULDER].y) and \
				   (lm_list[RIGHT_WRIST].y > lm_list[RIGHT_SHOULDER].y)
	
	# Hips should be above the wrists (closer to the top of the frame)
	hip_y = (lm_list[LEFT_HIP].y + lm_list[RIGHT_HIP].y) / 2
	wrist_y = (lm_list[LEFT_WRIST].y + lm_list[RIGHT_WRIST].y) / 2
	hip_above_wrist = hip_y < wrist_y

	# Back must be somewhat straight (not crouching or sitting upright with bent back)
	align = get_body_alignment(lm_list)
	is_plank = align["back_angle"] > 120

	return wrists_below and hip_above_wrist and is_plank


def get_landmark_coords(lm_list) -> list:
	"""
	Extract (x, y) coordinates for all 33 landmarks to be drawn by the frontend.
	Returns list of dicts: [{'x': 0.5, 'y': 0.5}, ...]
	"""
	return [{"x": lm.x, "y": lm.y} for lm in lm_list]
