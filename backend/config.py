import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "..", "datasets")
MODEL_DIR = os.path.join(BASE_DIR, "models")
FEATURES_DIR = os.path.join(BASE_DIR, "features")

CORRECT_DIR = os.path.join(DATASET_DIR, "Correct sequence")
WRONG_DIR = os.path.join(DATASET_DIR, "Wrong sequence")

CLASSIFIER_MODEL_PATH = os.path.join(MODEL_DIR, "pushup_classifier.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")
FEATURES_PATH = os.path.join(FEATURES_DIR, "landmarks.npz")
POSE_LANDMARKER_MODEL = os.path.join(MODEL_DIR, "pose_landmarker.task")

NUM_LANDMARKS = 33
FEATURE_SIZE = NUM_LANDMARKS * 4  # 132

FRAME_SAMPLE_RATE = 5

# Pushup rep counting thresholds (degrees)
ELBOW_ANGLE_DOWN = 90
ELBOW_ANGLE_UP = 150
