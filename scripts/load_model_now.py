# scripts/load_model_now.py
"""
Load a trained model file into the app.ml_model wrapper object so StrategyEngine
and other parts can use it at runtime.

It tries joblib first, then pickle. It attaches:
  ml_model.model = loaded_model
  ml_model.model_path = absolute_path
"""

import os
import sys
import joblib
import pickle

from pathlib import Path

MODEL_REL = os.path.join("app", "storage", "rf_model.pkl")
MODEL_PATH = str(Path(MODEL_REL).resolve())

print("Trying to load model from:", MODEL_PATH)
if not os.path.exists(MODEL_PATH):
    raise SystemExit("Model file not found: " + MODEL_PATH)

# import ml_model wrapper
try:
    from app import ml_model
except Exception as e:
    raise SystemExit("Failed to import app.ml_model: " + str(e))

loaded = None
# 1) try joblib
try:
    loaded = joblib.load(MODEL_PATH)
    print("Loaded model with joblib:", type(loaded))
except Exception as e:
    print("joblib.load failed:", e)

# 2) try pickle if joblib failed
if loaded is None:
    try:
        with open(MODEL_PATH, "rb") as f:
            loaded = pickle.load(f)
        print("Loaded model with pickle:", type(loaded))
    except Exception as e:
        print("pickle.load failed:", e)

if loaded is None:
    raise SystemExit("Failed to load model with joblib or pickle.")

# attach to ml_model wrapper
setattr(ml_model, "model", loaded)
setattr(ml_model, "model_path", MODEL_PATH)

# optional: if ml_model has predict wrapper names, try to set them
if not hasattr(ml_model, "predict") and hasattr(loaded, "predict"):
    setattr(ml_model, "predict", loaded.predict)
if not hasattr(ml_model, "predict_proba") and hasattr(loaded, "predict_proba"):
    setattr(ml_model, "predict_proba", loaded.predict_proba)

print("Model attached to app.ml_model: ", getattr(ml_model, "model", None))
print("If strategy uses ml_model.predict or ml_model.predict_proba, they should be available now.")
