# scripts/backtest_model.py
"""
Enhanced backtester for saved ML model.

Features:
 - Aligns features to model.feature_names_in_ (best-effort)
 - Uses predict_proba thresholding if available (--prob-threshold)
 - Hold for H bars (--hold)
 - Cooldown between trades (--cooldown)
 - Fee & slippage parameters
 - Saves CSV, JSON metrics and equity PNG

Usage example:
  conda activate deep3d_py310
  python scripts\backtest_model.py --symbol RELIANCE.NS --period 60d --interval 5m --prob-threshold 0.6 --hold 1 --cooldown 0
"""
import os
import json
import joblib
import argparse
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

MODEL_PATH = os.path.join("app", "storage", "rf_model.pkl")
OUT_DIR = Path("scripts")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------
# Utilities: fetch + candidate features
# -------------------------
def load_model(path=MODEL_PATH):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    mdl = joblib.load(path)
    return mdl

def fetch_yf(symbol, period="60d", interval="5m"):
    t = yf.Ticker(symbol)
    df = t.history(period=period, interval=interval, actions=False)
    if df is None or df.empty:
        raise RuntimeError("yfinance returned no data for symbol=%s period=%s interval=%s" % (symbol, period, interval))
    df.index = pd.to_datetime(df.index)
    return df

def build_candidate_features(df):
    """Create many common features that a model might expect."""
    df2 = df.copy()
    close = df2["Close"]
    vol = df2["Volume"] if "Volume" in df2.columns else df2.get("volume", pd.Series(0, index=df2.index))

    # returns
    df2["r1"] = close.pct_change(1).fillna(0)
    df2["r2"] = close.pct_change(2).fillna(0)
    df2["ret1"] = df2["r1"]  # alias
    df2["ret2"] = df2["r2"]

    # moving averages
    df2["ma5"] = close.rolling(5).mean()
    df2["ma15"] = close.rolling(15).mean()
    df2["ma20"] = close.rolling(20).mean()

    # volatility / normalized volume
    df2["vol_mean20"] = vol.rolling(20).mean()
    df2["vol_norm"] = vol / (df2["vol_mean20"] + 1e-9)
    df2["vol"] = vol

    # simple momentum / price ratios
    df2["close_ma5_diff"] = (close - df2["ma5"]) / (df2["ma5"] + 1e-9)
    df2["close_ma15_diff"] = (close - df2["ma15"]) / (df2["ma15"] + 1e-9)

    # RSI-ish
    delta = close.diff()
    up = delta.clip(lower=0).rolling(14).mean()
    down = -delta.clip(upper=0).rolling(14).mean()
    df2["rsi14"] = 100 - (100 / (1 + (up / (down + 1e-9))))

    # basic lag features
    df2["lag1_close"] = close.shift(1)
    df2["lag1_ret"] = df2["r1"].shift(1)

    # cleanup
    df2 = df2.replace([np.inf, -np.inf], np.nan).dropna()
    return df2

# -------------------------
# Feature alignment
# -------------------------
def get_model_expected_features(model):
    """
    Try to discover feature names expected by the model.
    Returns list of names or raises if not discoverable.
    """
    if hasattr(model, "feature_names_in_"):
        return list(model.feature_names_in_)
    try:
        if hasattr(model, "named_steps"):
            final = None
            if "clf" in model.named_steps:
                final = model.named_steps["clf"]
            else:
                final = list(model.named_steps.values())[-1]
            if hasattr(final, "feature_names_in_"):
                return list(final.feature_names_in_)
    except Exception:
        pass
    try:
        if hasattr(model, "steps"):
            last = model.steps[-1][1]
            if hasattr(last, "feature_names_in_"):
                return list(last.feature_names_in_)
    except Exception:
        pass
    raise RuntimeError("Model does not expose expected feature names (feature_names_in_). Provide training feature list.")

def ensure_features_for_model(df_with_feats: pd.DataFrame, feature_names):
    """
    Map / synthesize DataFrame columns to model.feature_names_in_.
    If mapping not possible, return (X, missing_list).
    """
    df = df_with_feats.copy()
    available = set(df.columns)
    missing = []
    for f in feature_names:
        if f in available:
            continue
        aliases = {
            "r1": ["r1","ret1","r_1","return_1"],
            "r2": ["r2","ret2","r_2","return_2"],
            "vol_norm": ["vol_norm","volume_norm","vol/ma","volume/vol_mean20","vol_mean20","vol_norm"],
            "ma5": ["ma5","sma5","ma_5"],
            "ma15": ["ma15","sma15","ma_15"],
            "rsi14": ["rsi14","rsi_14"],
            "vol": ["vol","volume","Volume"],
            "lag1_ret": ["lag1_ret","r1_lag","lag1_ret"],
        }
        done = False
        if f in aliases:
            for c in aliases[f]:
                if c in available:
                    df[f] = df[c]
                    done = True
                    break
        if done:
            continue
        # case-insensitive direct match
        for a in available:
            if a.lower() == f.lower():
                df[f] = df[a]
                done = True
                break
        if done:
            continue
        # substring match
        for a in available:
            if f.lower() in a.lower() or a.lower() in f.lower():
                df[f] = df[a]
                done = True
                break
        if not done:
            missing.append(f)
    X = df[[c for c in feature_names if c in df.columns]]
    return X, missing

# -------------------------
# Backtest logic & metrics
# -------------------------
def backtest_from_preds(df_full: pd.DataFrame, preds: np.ndarray, hold_bars=1, fee_per_trade=0.0005, slippage=0.0002, cooldown=0):
    df = df_full.copy()
    df = df.iloc[:len(preds)].copy()
    df["pred"] = preds
    # compute H-bar forward close and return
    df["exit_close"] = df["Close"].shift(-hold_bars)
    df["forward_return"] = (df["exit_close"] / df["Close"]) - 1.0
    df["strategy_ret"] = 0.0

    # apply cooldown logic: go through index sequentially
    last_trade_idx = -9999
    indices = list(df.index)
    for i, idx in enumerate(indices):
        if df.at[idx, "pred"] == 1:
            if (i - last_trade_idx) <= cooldown:
                # skip due to cooldown
                continue
            # compute return over hold_bars (if available)
            ret = df.at[idx, "forward_return"]
            if pd.isna(ret):
                # cannot compute return (near end), skip
                continue
            df.at[idx, "strategy_ret"] = ret - (fee_per_trade + slippage)
            last_trade_idx = i

    # cumulative
    df["cum_strategy"] = (1 + df["strategy_ret"]).cumprod().ffill()
    df["cum_buyhold"] = (1 + df["forward_return"]).cumprod().ffill()

    # metrics
    r = df["strategy_ret"].dropna()
    try:
        inferred = pd.infer_freq(df.index[:20])
        if inferred and "T" in inferred:
            minutes = int(''.join(filter(str.isdigit, inferred)) or 1)
            bars_per_day = int(390 / minutes) if minutes else 1
            bars_per_year = bars_per_day * 252
        else:
            bars_per_year = 252
    except Exception:
        bars_per_year = 252

    if len(r) > 1:
        mean_ret = r.mean() * bars_per_year
        std_ret = r.std() * np.sqrt(bars_per_year)
        sharpe = mean_ret / (std_ret + 1e-9)
    else:
        sharpe = float("nan")

    cum = df["cum_strategy"].fillna(1.0)
    rolling_max = cum.cummax()
    drawdown = (cum - rolling_max) / (rolling_max + 1e-9)
    max_dd = float(drawdown.min())

    enter_mask = df["strategy_ret"] != 0
    trades = df[enter_mask]
    wins = trades[trades["strategy_ret"] > 0]
    win_rate = float(len(wins) / (len(trades) + 1e-9))
    avg_win = float(wins["strategy_ret"].mean()) if len(wins) else 0.0
    avg_loss = float(trades[trades["strategy_ret"] <= 0]["strategy_ret"].mean()) if len(trades) else 0.0
    profit_factor = float(wins["strategy_ret"].sum() / ( - trades[trades["strategy_ret"] <= 0]["strategy_ret"].sum() + 1e-9)) if len(trades) else float("nan")

    return {
        "cumulative_return": float(cum.iloc[-2]) if len(df) > 2 else float(cum.iloc[-1]),
        "total_return": float(df["strategy_ret"].sum()),
        "sharpe": float(sharpe) if not np.isnan(sharpe) else None,
        "max_drawdown": max_dd,
        "n_trades": int(len(trades)),
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "df": df
    }

def plot_equity(df, out_png):
    plt.figure(figsize=(10,5))
    plt.plot(df.index, df["cum_strategy"], label="Strategy")
    plt.plot(df.index, df["cum_buyhold"], label="BuyHold")
    plt.title("Equity Curve")
    plt.xlabel("Time")
    plt.ylabel("Cumulative")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()

# -------------------------
# Main
# -------------------------
def main(symbol, period, interval, prob_threshold, hold, cooldown, fee, slip):
    print("Loading model:", MODEL_PATH)
    mdl = load_model()
    print("Discovering model expected features...")
    try:
        exp_names = get_model_expected_features(mdl)
    except Exception as e:
        print("ERROR: cannot detect model.feature_names_in_. Provide training feature list or inspect model. Error:", e)
        return
    print("Model expects features:", exp_names)

    print("Fetching data:", symbol, period, interval)
    df_raw = fetch_yf(symbol, period=period, interval=interval)
    df_feats = build_candidate_features(df_raw)
    print("Candidate features prepared, rows:", len(df_feats))

    X_full, missing = ensure_features_for_model(df_feats, exp_names)
    if missing:
        print("ERROR: Could not synthesize these required features for the model:", missing)
        print("Available candidate columns (sample):", list(df_feats.columns)[:60])
        return

    # align target (next bar up) for potential diagnostics (not used in trading sim)
    df_aligned = df_feats.loc[X_full.index].copy()
    df_aligned["target"] = (df_aligned["Close"].shift(-1) > df_aligned["Close"]).astype(int)
    df_aligned = df_aligned.dropna(subset=["target"])
    X = X_full.loc[df_aligned.index]
    y = df_aligned["target"]

    # prediction (with probability threshold if supported)
    print("Running model.predict on", len(X), "rows")
    if prob_threshold is not None and hasattr(mdl, "predict_proba"):
        probs = mdl.predict_proba(X)[:,1]
        preds = (probs >= prob_threshold).astype(int)
        print(f"Using predict_proba threshold {prob_threshold}: selected {int(preds.sum())} signals")
    else:
        preds = mdl.predict(X)

    # backtest
    res = backtest_from_preds(df_aligned, preds, hold_bars=hold, fee_per_trade=fee, slippage=slip, cooldown=cooldown)
    df_out = res["df"]

    # save CSV, JSON, PNG
    csv_path = OUT_DIR / "backtest_out.csv"
    df_out.to_csv(csv_path)
    metrics = {k:v for k,v in res.items() if k!="df"}
    metrics["symbol"] = symbol
    metrics["model_path"] = MODEL_PATH
    metrics["run_at"] = datetime.utcnow().isoformat()
    metrics["prob_threshold"] = prob_threshold
    metrics["hold_bars"] = hold
    metrics["cooldown"] = cooldown
    json_path = OUT_DIR / "backtest_metrics.json"
    with open(json_path, "w") as f:
        json.dump(metrics, f, indent=2)
    png_path = OUT_DIR / "backtest_equity.png"
    plot_equity(df_out, png_path)

    # print summary
    print("Backtest complete — results:")
    for k,v in metrics.items():
        if k in ("model_path","symbol","run_at"):
            continue
        print(f"  {k}: {v}")
    print("Saved CSV:", csv_path)
    print("Saved metrics:", json_path)
    print("Saved equity PNG:", png_path)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="RELIANCE.NS")
    p.add_argument("--period", default="60d")
    p.add_argument("--interval", default="5m")
    p.add_argument("--prob-threshold", type=float, default=None, help="if given and model supports predict_proba, use this threshold")
    p.add_argument("--hold", type=int, default=1, help="number of bars to hold the trade (1 = next bar only)")
    p.add_argument("--cooldown", type=int, default=0, help="cooldown bars after a trade (prevent immediate flipping)")
    p.add_argument("--fee", type=float, default=0.0005, help="round-trip fee fraction")
    p.add_argument("--slip", type=float, default=0.0002, help="slippage fraction")
    args = p.parse_args()
    main(args.symbol, args.period, args.interval, args.prob_threshold, args.hold, args.cooldown, args.fee, args.slip)
