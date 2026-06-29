"""
Inference helpers — loads classifier + scaler once at startup.
"""

import os
import joblib
import numpy as np

from config import CLASSIFIER_MODEL_PATH, SCALER_PATH

_clf = None
_scaler = None


def _load():
    global _clf, _scaler
    if _clf is None:
        if not os.path.exists(CLASSIFIER_MODEL_PATH):
            raise FileNotFoundError(
                f"Model not found at {CLASSIFIER_MODEL_PATH}. "
                "Run data_pipeline.py then train.py first."
            )
        _clf = joblib.load(CLASSIFIER_MODEL_PATH)
        _scaler = joblib.load(SCALER_PATH)


def predict_landmarks(features: np.ndarray) -> dict:
    """
    Classify a single 132-dim landmark vector.
    Returns label, confidence, and per-class probabilities.
    """
    _load()
    vec = features.reshape(1, -1)
    vec_scaled = _scaler.transform(vec)
    proba = _clf.predict_proba(vec_scaled)[0]
    pred = int(_clf.predict(vec_scaled)[0])

    return {
        "label": "correct" if pred == 1 else "wrong",
        "confidence": float(proba[pred]),
        "probabilities": {
            "correct": float(proba[1]),
            "wrong": float(proba[0]),
        },
    }


def is_model_ready() -> bool:
    return os.path.exists(CLASSIFIER_MODEL_PATH) and os.path.exists(SCALER_PATH)
