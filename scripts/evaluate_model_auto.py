# scripts/evaluate_model_auto.py
"""
Attempt to evaluate the saved model by auto-creating common features.
This is a best-effort approach: it inspects model.feature_names_in_ (if available)
and synthesizes common features (r1, r2, vol_norm, ma5, ma15, rsi14, etc.)
so feature names match the model.

Usage:
    conda activate deep3d_py310
    python scripts\evaluate_model_auto.py --symbol RELIANCE.NS --period 60d --interval 5m
"""

import argparse, os, joblib
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score, confusion_matrix
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
import yfinance as yf

MODEL_PATH = os.path.join("app", "storage", "rf_model.pkl")

def load_model(path=MODEL_PATH):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    mdl = joblib.load(path)
    return mdl

def fetch_yf(symbol, period="60d", interval="5m"):
    t = yf.Ticker(symbol)
    df = t.history(period=period, interval=interval, actions=False)
    df.index = pd.to_datetime(df.index)
    return df

def build_candidate_features(df):
    """create a wide set of common features used in trading models"""
    df2 = df.copy()
    close = df2["Close"]
    vol = df2["Volume"] if "Volume" in df2.columns else df2.get("volume", pd.Series(0, index=df2.index))
    # simple returns
    df2["r1"] = close.pct_change(1).fillna(0)
    df2["r2"] = close.pct_change(2).fillna(0)
    df2["ret1"] = df2["r1"]  # alias
    df2["ret2"] = df2["r2"]
    # moving avgs
    df2["ma5"] = close.rolling(5).mean()
    df2["ma15"] = close.rolling(15).mean()
    # RSI-like crude
    delta = close.diff()
    up = delta.clip(lower=0).rolling(14).mean()
    down = -delta.clip(upper=0).rolling(14).mean()
    df2["rsi14"] = 100 - (100 / (1 + (up / (down + 1e-9))))
    # volume normalized
    df2["vol_mean20"] = vol.rolling(20).mean()
    df2["vol_norm"] = vol / (df2["vol_mean20"] + 1e-9)
    # other aliases
    df2["vol"] = vol
    df2 = df2.replace([np.inf, -np.inf], np.nan).dropna()
    return df2

def ensure_features_for_model(df_with_feats, feature_names):
    """
    Ensure df has columns matching feature_names.
    If a feature is missing, try some common aliases.
    Returns (X, missing) where X is DataFrame subset for model and missing is list of unresolved names.
    """
    df = df_with_feats.copy()
    available = set(df.columns)
    missing = []
    resolved = []
    for f in feature_names:
        if f in available:
            resolved.append(f)
            continue
        # try common mappings
        mapping_candidates = {
            "r1": ["r1","ret1","r_1","return_1"],
            "r2": ["r2","ret2","r_2","return_2"],
            "vol_norm": ["vol_norm","volume_norm","vol/ma","volume/vol_mean20","vol_norm"],
            "ma5": ["ma5","sma5","ma_5"],
            "ma15": ["ma15","sma15","ma_15"],
        }
        done = False
        # search candidates
        for k,cands in mapping_candidates.items():
            if f == k or f.lower() == k.lower():
                for c in cands:
                    if c in available:
                        df[f] = df[c]
                        resolved.append(f)
                        done = True
                        break
                if done:
                    break
        # try direct alias: lower-case match
        if not done:
            for a in available:
                if a.lower() == f.lower():
                    df[f] = df[a]
                    resolved.append(f)
                    done = True
                    break
        if not done:
            # try prefix/suffix matching
            for a in available:
                if f.lower() in a.lower() or a.lower() in f.lower():
                    df[f] = df[a]
                    resolved.append(f)
                    done = True
                    break
        if not done:
            missing.append(f)
    # return X with columns in model order if available
    X = df[[c for c in feature_names if c in df.columns]]
    return X, missing

def print_classification(y_true, y_pred):
    acc = accuracy_score(y_true, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
    try:
        auc = roc_auc_score(y_true, y_pred)
    except Exception:
        auc = None
    cm = confusion_matrix(y_true, y_pred)
    print("Accuracy:", acc)
    print("Precision:", prec, "Recall:", rec, "F1:", f1)
    print("ROC AUC:", auc)
    print("Confusion matrix:\n", cm)

def main(symbol, period="60d", interval="5m"):
    print("Loading model:", MODEL_PATH)
    model = load_model()
    # get expected feature names
    exp_names = None
    if hasattr(model, "feature_names_in_"):
        exp_names = list(model.feature_names_in_)
        print("Model expects feature_names_in_: ", exp_names)
    else:
        # sometimes wrapped in a pipeline with named step "clf" or so
        try:
            # attempt to find a classifier inside pipeline
            for attr in ["steps","named_steps"]:
                if hasattr(model, attr):
                    # try to inspect final estimator
                    if hasattr(model, "named_steps") and "clf" in model.named_steps:
                        sub = model.named_steps["clf"]
                        if hasattr(sub, "feature_names_in_"):
                            exp_names = list(sub.feature_names_in_)
                            break
        except Exception:
            pass
    if exp_names is None:
        print("Model does not expose feature_names_in_; cannot auto-align safely.")
        print("Please provide training feature pipeline or the expected feature list.")
        return

    print("Fetching data:", symbol, period, interval)
    df_raw = fetch_yf(symbol, period=period, interval=interval)
    df_feats = build_candidate_features(df_raw)
    print("Built candidate features; total rows:", len(df_feats))

    X_full, missing = ensure_features_for_model(df_feats, exp_names)
    if missing:
        print("ERROR: Could not synthesize these required features for the model:", missing)
        print("Available candidate columns:", list(df_feats.columns))
        print("Please provide the original feature-building code from training (app/ml_model.py) so we can replicate it exactly.")
        return

    # build target (next bar up/down) aligned with X_full
    df_aligned = df_feats.loc[X_full.index].copy()
    df_aligned["target"] = (df_aligned["Close"].shift(-1) > df_aligned["Close"]).astype(int)
    # drop last row with no next target
    df_aligned = df_aligned.dropna(subset=["target"])
    X = X_full.loc[df_aligned.index]
    y = df_aligned["target"]

    # split into train/test by time
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    print("Running prediction on test set, rows:", len(X_test))
    y_pred = model.predict(X_test)
    print_classification(y_test, y_pred)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="RELIANCE.NS")
    p.add_argument("--period", default="60d")
    p.add_argument("--interval", default="5m")
    args = p.parse_args()
    main(args.symbol, args.period, args.interval)
