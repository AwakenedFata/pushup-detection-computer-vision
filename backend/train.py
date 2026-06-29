"""
Train a pushup posture classifier on extracted landmark features.
Trains an MLP (neural network) via scikit-learn + saves model + scaler.

Usage:
    python train.py
"""

import os
import sys
import numpy as np
import joblib
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    classification_report, confusion_matrix, accuracy_score
)

from config import FEATURES_PATH, CLASSIFIER_MODEL_PATH as MODEL_PATH, SCALER_PATH


def load_features():
    if not os.path.exists(FEATURES_PATH):
        print(f"ERROR: Feature file not found at {FEATURES_PATH}")
        print("Run data_pipeline.py first.")
        sys.exit(1)

    data = np.load(FEATURES_PATH)
    X, y = data["X"], data["y"]
    print(f"Loaded {X.shape[0]} samples | Feature dim: {X.shape[1]}")
    print(f"  Correct (1): {(y==1).sum()}  |  Wrong (0): {(y==0).sum()}")
    return X, y


def train(X, y):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    clf = MLPClassifier(
        hidden_layer_sizes=(256, 128, 64),
        activation="relu",
        solver="adam",
        max_iter=500,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=20,
        verbose=False,  # Set to False to keep console output clean in production
    )

    print("\nTraining MLP classifier...")
    clf.fit(X_train_scaled, y_train)

    y_pred = clf.predict(X_test_scaled)
    acc = accuracy_score(y_test, y_pred)

    print(f"\n{'='*50}")
    print(f"Test Accuracy : {acc:.4f} ({acc*100:.2f}%)")
    print(f"{'='*50}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Wrong", "Correct"]))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # Cross-validation
    print("\nRunning 5-fold cross-validation on full dataset...")
    X_all_scaled = scaler.transform(X)
    cv_scores = cross_val_score(clf, X_all_scaled, y, cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42))
    print(f"CV Accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    return clf, scaler


def save_model(clf, scaler):
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print(f"\nModel saved to  : {MODEL_PATH}")
    print(f"Scaler saved to : {SCALER_PATH}")


def main():
    print("=" * 60)
    print("PUSHUP POSTURE CLASSIFIER TRAINING")
    print("=" * 60)

    X, y = load_features()
    clf, scaler = train(X, y)
    save_model(clf, scaler)

    print("\nTraining complete.")


if __name__ == "__main__":
    main()
