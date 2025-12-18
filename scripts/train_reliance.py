# scripts/train_reliance.py
"""
Robust training helper for RELIANCE (or other symbols).
Tries AlphaVantage then multiple yfinance fallbacks:
  1) 5m, period=60d
  2) 15m, period=6mo
  3) 1d, period=2y
This avoids '5m for 1y' problem on yfinance.
"""

import os
import time
from datetime import datetime
from dotenv import load_dotenv

import pandas as pd
import requests
import yfinance as yf

from app.ml_model import ml_model
from app import crud

load_dotenv()
ALPHAVANTAGE_KEY = os.getenv("ALPHAVANTAGE_KEY", "").strip()

def av_intraday_to_df(av_json, interval="5min"):
    key = f"Time Series ({interval})"
    if key not in av_json:
        for k in av_json.keys():
            if "Time Series" in k and interval.replace("min","min") in k:
                key = k
                break
    series = av_json.get(key)
    if not series:
        return None
    rows = []
    for ts_str, values in series.items():
        ts = pd.to_datetime(ts_str)
        rows.append({
            "ts": ts,
            "open": float(values.get("1. open")),
            "high": float(values.get("2. high")),
            "low": float(values.get("3. low")),
            "close": float(values.get("4. close")),
            "volume": float(values.get("5. volume", 0))
        })
    df = pd.DataFrame(rows).sort_values("ts").set_index("ts")
    return df

def av_daily_to_df(av_json):
    key = "Time Series (Daily)"
    if key not in av_json:
        for k in av_json.keys():
            if "Time Series" in k and "Daily" in k:
                key = k
                break
    series = av_json.get(key)
    if not series:
        return None
    rows = []
    for ts_str, values in series.items():
        ts = pd.to_datetime(ts_str)
        rows.append({
            "ts": ts,
            "open": float(values.get("1. open")),
            "high": float(values.get("2. high")),
            "low": float(values.get("3. low")),
            "close": float(values.get("4. close")),
            "volume": float(values.get("5. volume", 0))
        })
    df = pd.DataFrame(rows).sort_values("ts").set_index("ts")
    return df

def fetch_from_alphavantage(symbol: str, interval: str = "5min"):
    if not ALPHAVANTAGE_KEY:
        return None, "no_key"
    base = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": symbol,
        "interval": interval,
        "apikey": ALPHAVANTAGE_KEY,
        "outputsize": "compact"
    }
    try:
        r = requests.get(base, params=params, timeout=20)
        j = r.json()
        if "Note" in j or "Error Message" in j or not any("Time Series" in k for k in j.keys()):
            # fallback to daily
            r2 = requests.get(base, params={"function":"TIME_SERIES_DAILY_ADJUSTED","symbol":symbol,"apikey":ALPHAVANTAGE_KEY,"outputsize":"compact"}, timeout=20)
            j2 = r2.json()
            df2 = av_daily_to_df(j2)
            if df2 is not None:
                return df2, "alphavantage-daily"
            return None, "av_error"
        df = av_intraday_to_df(j, interval=interval)
        return df, "alphavantage-intraday"
    except Exception as e:
        return None, f"av_exception:{e}"

def fetch_from_yfinance(symbol: str, period: str, interval: str):
    try:
        t = yf.Ticker(symbol)
        df = t.history(period=period, interval=interval, actions=False)
        if df is None or df.empty:
            return None
        df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
        df = df[["open","high","low","close","volume"]].copy()
        df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return None

def prepare_and_train(symbol="RELIANCE.NS"):
    # Try sequence of sources/intervals
    attempts = [
        ("alphavantage", {"fn": fetch_from_alphavantage, "kwargs": {"interval":"5min"}}),
        ("yf_5m_60d", {"fn": fetch_from_yfinance, "kwargs": {"period":"60d", "interval":"5m"}}),
        ("yf_15m_6mo", {"fn": fetch_from_yfinance, "kwargs": {"period":"6mo", "interval":"15m"}}),
        ("yf_1d_2y", {"fn": fetch_from_yfinance, "kwargs": {"period":"2y", "interval":"1d"}}),
    ]
    df = None
    source = None
    for name, cfg in attempts:
        fn = cfg["fn"]
        kw = cfg["kwargs"]
        print(f"Trying source {name} with params {kw}")
        if name.startswith("alphavantage"):
            df_res, info = fn(symbol, **kw)
            if df_res is not None and len(df_res) >= 50:
                df = df_res
                source = name
                print(f"AlphaVantage OK: {len(df)} rows ({info})")
                break
            else:
                print("AlphaVantage did not return usable data:", info)
        else:
            df_res = fn(symbol, **kw)
            if df_res is not None and len(df_res) >= 50:
                df = df_res
                source = name
                print(f"yfinance OK: {len(df)} rows ({name})")
                break
            else:
                print(f"yfinance attempt {name} returned {None if df_res is None else len(df_res)} rows")

    if df is None:
        print("All sources failed or returned insufficient data.")
        return {"success": False, "error": "no_data_from_sources"}

    # sanitize columns
    for c in ["open","high","low","close","volume"]:
        if c not in df.columns:
            print("Missing column", c, "from data source", source)
            return {"success": False, "error": f"missing_column_{c}"}
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna().copy()
    print(f"Training model with {len(df)} rows from {source} ...")
    res = ml_model.train_dummy(df)
    print("Train result:", res)
    # save metadata (best-effort)
    try:
        blob = {"source": source, "rows": len(df)}
        crud.save_model_metadata(filename="app/storage/rf_model.pkl", rows=len(df), metrics=blob, notes=f"trained {symbol} from {source}")
    except Exception:
        pass
    return {"success": True, "source": source, "rows": len(df), "ml": res}

if __name__ == "__main__":
    print("Running train_reliance with robust fallbacks...")
    out = prepare_and_train("RELIANCE.NS")
    print("Final:", out)








