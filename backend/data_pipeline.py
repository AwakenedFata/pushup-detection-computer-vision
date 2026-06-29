"""
Dataset pipeline: extract landmarks from all videos -> save as .npz feature file.
Run this script once before training.

Usage:
    python data_pipeline.py
"""

import os
import numpy as np

from config import (
    CORRECT_DIR, WRONG_DIR, FEATURES_PATH, FRAME_SAMPLE_RATE,
)
from pose_utils import sample_video_landmarks


def process_folder(folder: str, label: int) -> tuple[list, list]:
    X, y = [], []
    videos = [f for f in os.listdir(folder) if f.lower().endswith(".mp4")]
    total = len(videos)

    for i, fname in enumerate(videos, 1):
        path = os.path.join(folder, fname)
        print(f"  [{i:02d}/{total}] {fname}", end=" ", flush=True)
        landmarks = sample_video_landmarks(path, sample_rate=FRAME_SAMPLE_RATE)

        if landmarks:
            X.extend(landmarks)
            y.extend([label] * len(landmarks))
            print(f"-> {len(landmarks)} frames")
        else:
            print("-> no pose detected, skipped")

    return X, y


def main():
    print("=" * 60)
    print("PUSHUP POSE DATASET PIPELINE")
    print("=" * 60)

    X_all, y_all = [], []

    print("\n[1/2] Processing CORRECT pushup videos...")
    X_c, y_c = process_folder(CORRECT_DIR, label=1)
    X_all.extend(X_c)
    y_all.extend(y_c)
    print(f"      -> {len(X_c)} frames extracted (label=1 Correct)")

    print("\n[2/2] Processing WRONG pushup videos...")
    X_w, y_w = process_folder(WRONG_DIR, label=0)
    X_all.extend(X_w)
    y_all.extend(y_w)
    print(f"      -> {len(X_w)} frames extracted (label=0 Wrong)")

    X_arr = np.array(X_all, dtype=np.float32)
    y_arr = np.array(y_all, dtype=np.int32)

    print(f"\nTotal samples: {X_arr.shape[0]}  |  Feature dim: {X_arr.shape[1]}")
    print(f"Class distribution -> Correct(1): {(y_arr==1).sum()}  |  Wrong(0): {(y_arr==0).sum()}")

    os.makedirs(os.path.dirname(FEATURES_PATH), exist_ok=True)
    np.savez_compressed(FEATURES_PATH, X=X_arr, y=y_arr)
    print(f"\nSaved features to: {FEATURES_PATH}")
    print("Done.")


if __name__ == "__main__":
    main()
