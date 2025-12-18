# app/indicators.py
"""
Indicators & TickBuffer.
- TickBuffer: in-memory deque storing recent ticks (token, ltp, volume, timestamp, raw)
- compute_signals(token): returns dict of indicator values (safe if not enough data)
- Designed to be robust to different tick payload shapes coming from Kite/yfinance/other.
"""

import collections
import pandas as pd
import numpy as np
from threading import Lock
from datetime import datetime

# ---- Tick buffer singleton ----
class TickBuffer:
    _instance = None

    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def __init__(self, maxlen=20_000):
        self.maxlen = maxlen
        self.buf = collections.deque(maxlen=maxlen)
        self.lock = Lock()

    def push(self, tick):
        """
        Accepts tick dicts from various sources (Kite, yfinance fallback, etc.)
        Normalizes into {token, ltp, volume, timestamp, raw}
        - tolerant: accepts 'last_price', 'ltp', 'price', 'last_trade_price'
        - volume tolerant keys: 'volume','last_quantity','tick_volume'
        - timestamp tolerant keys: 'timestamp','tick_timestamp','exchange_timestamp'
        """
        try:
            # unify instrument token / symbol
            instrument_token = tick.get("instrument_token") or tick.get("instrumentToken") or tick.get("instrument") or tick.get("token")
            try:
                token_key = str(instrument_token) if instrument_token is not None else None
            except Exception:
                token_key = None

            # price fields
            ltp = None
            for k in ("last_price", "ltp", "price", "lastTradePrice", "last_trade_price"):
                if k in tick and tick.get(k) is not None:
                    try:
                        ltp = float(tick.get(k))
                        break
                    except Exception:
                        continue

            # volume fields
            vol = None
            for k in ("volume", "last_quantity", "tick_volume", "totalBuyQuantity"):
                if k in tick and tick.get(k) is not None:
                    try:
                        vol = float(tick.get(k))
                        break
                    except Exception:
                        continue

            # timestamp
            ts_val = tick.get("timestamp") or tick.get("tick_timestamp") or tick.get("exchange_timestamp") or tick.get("time")
            if ts_val is None:
                ts = datetime.utcnow()
            else:
                # accept epoch numeric or ISO string
                try:
                    if isinstance(ts_val, (int, float)):
                        ts = pd.to_datetime(float(ts_val), unit="s", utc=True)
                    else:
                        ts = pd.to_datetime(ts_val, utc=True)
                except Exception:
                    ts = datetime.utcnow()

            # tradingsymbol if present
            tradingsymbol = tick.get("tradingsymbol") or tick.get("symbol") or tick.get("instrument_token") or None

            normalized = {
                "token": token_key,
                "ltp": ltp,
                "volume": vol,
                "timestamp": ts,
                "tradingsymbol": tradingsymbol,
                "raw": tick
            }
            with self.lock:
                self.buf.append(normalized)
        except Exception:
            # be forgiving: don't raise from push
            return

    def to_dataframe(self, token=None, window=500):
        """
        Return a DataFrame for the given token (or all tokens if token None).
        Index is timezone-aware timestamp.
        Resample to 1-second bars and forward/backfill missing prices.
        """
        with self.lock:
            rows = [r for r in list(self.buf) if (token is None or r["token"] == str(token))]
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        # ensure timestamp column and proper index
        if "timestamp" not in df.columns:
            return pd.DataFrame()
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        except Exception:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce").fillna(pd.Timestamp.utcnow())
        df = df.set_index("timestamp").sort_index()
        # keep only last `window` rows by index
        if window is not None:
            df = df.iloc[-window:]
        # resample to 1s (if the index is not already uniform) to compute indicator windows reliably
        try:
            df = df[["ltp", "volume", "token", "tradingsymbol", "raw"]].resample("1S").agg({
                "ltp": "last",
                "volume": "sum",
                "token": "last",
                "tradingsymbol": "last",
                "raw": "last"
            }).ffill().bfill()
        except Exception:
            # fallback: ensure ltp exists
            if "ltp" not in df.columns:
                return pd.DataFrame()
        return df

# ---- Indicator functions (return scalar last value) ----
def sma(series: pd.Series, period: int):
    if series is None or len(series) < period:
        return None
    return float(series.rolling(period).mean().iloc[-1])

def ema(series: pd.Series, period: int):
    if series is None or len(series) < 1:
        return None
    return float(series.ewm(span=period, adjust=False).mean().iloc[-1])

def rsi(series: pd.Series, period: int = 14):
    if series is None or len(series) < period + 2:
        return None
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / (loss + 1e-9)
    return float(100 - (100 / (1 + rs)).iloc[-1])

def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    if series is None or len(series) < slow:
        return None, None
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return float(macd_line.iloc[-1]), float(signal_line.iloc[-1])

def atr(df: pd.DataFrame, period: int = 14):
    """
    Basic ATR computed from ltp series; if high/low not present we approximate using ltp differences.
    """
    if df is None or len(df) < period + 1:
        return None
    # approximate true range as abs(diff(ltp))
    ltp = df["ltp"]
    tr = ltp.diff().abs().fillna(0)
    atr_val = tr.rolling(period).mean().iloc[-1]
    return float(atr_val) if not pd.isna(atr_val) else None

def bollinger(series: pd.Series, period: int = 20, n_std: float = 2.0):
    if series is None or len(series) < period:
        return None, None, None
    ma = series.rolling(period).mean()
    std = series.rolling(period).std()
    top = ma + n_std * std
    bot = ma - n_std * std
    return float(top.iloc[-1]), float(ma.iloc[-1]), float(bot.iloc[-1])

def vwap(df: pd.DataFrame):
    """
    Compute VWAP over the frame (requires 'ltp' and 'volume').
    """
    if df is None or "ltp" not in df.columns or "volume" not in df.columns:
        return None
    if df["volume"].sum() == 0:
        return None
    tp = df["ltp"] * df["volume"]
    return float(tp.sum() / (df["volume"].sum() + 1e-9))

# ---- Helper: 1-bar return ----
def one_bar_return(series: pd.Series):
    if series is None or len(series) < 2:
        return None
    return float(series.pct_change().iloc[-1])

# ---- High-level compute_signals API ----
def compute_signals(token, window=500):
    """
    Compute a set of indicators for the given instrument token.
    Returns dict with keys:
      - last, ma5, ma15, ema20, ema50, rsi14, macd, macd_signal, atr14,
        boll_up, boll_mid, boll_low, vwap, ret1, ema_cross (True/False)
      - compatibility keys: r1, r2, vol_norm (for older ML models)
    If not enough data for an indicator, its value is None.
    """
    tb = TickBuffer.instance()
    df = tb.to_dataframe(token=token, window=window)
    if df.empty or "ltp" not in df:
        return {}

    s = df["ltp"].dropna()
    vol = df["volume"].fillna(0)

    out = {}
    out["last"] = float(s.iloc[-1]) if not s.empty else None
    out["ma5"] = sma(s, 5)
    out["ma15"] = sma(s, 15)
    out["ma50"] = sma(s, 50)
    out["ma200"] = sma(s, 200)
    out["ema5"] = ema(s, 5)
    out["ema15"] = ema(s, 15)
    out["ema20"] = ema(s, 20)
    out["ema50"] = ema(s, 50)
    out["rsi14"] = rsi(s, 14)
    macd_val, macd_sig = macd(s)
    out["macd"] = macd_val
    out["macd_signal"] = macd_sig
    out["atr14"] = atr(df, 14)
    boll_up, boll_mid, boll_low = bollinger(s, 20, 2.0)
    out["boll_up"] = boll_up
    out["boll_mid"] = boll_mid
    out["boll_low"] = boll_low
    out["vwap"] = vwap(df)
    out["ret1"] = one_bar_return(s)

    # indicator confirmation examples
    try:
        # ema cross: fast ema(5) > ema(15)
        out["ema_cross"] = bool(out["ema5"] is not None and out["ema15"] is not None and out["ema5"] > out["ema15"])
    except Exception:
        out["ema_cross"] = None

    # volume normalization relative to recent average
    try:
        mean_vol = float(vol.replace(0, np.nan).rolling(50).mean().iloc[-1]) if len(vol) >= 10 else (float(vol.mean()) if len(vol)>0 else None)
        if mean_vol and mean_vol > 0:
            out["vol_norm"] = float((vol.iloc[-1]) / (mean_vol + 1e-9))
        else:
            out["vol_norm"] = None
    except Exception:
        out["vol_norm"] = None

    # Backwards compatibility: some pre-existing ML expected 'r1','r2' (simple returns)
    try:
        out["r1"] = float(s.pct_change().shift(0).iloc[-1]) if len(s) >= 2 else None
        out["r2"] = float(s.pct_change().shift(1).iloc[-1]) if len(s) >= 3 else None
    except Exception:
        out["r1"] = None
        out["r2"] = None

    # Add a simple "score" aggregator (optional)
    try:
        score = 0.0
        count = 0.0
        if out.get("ema_cross"):
            score += 1.0; count += 1.0
        if out.get("rsi14") is not None:
            # lower RSI = more buy-y; scale to 0..1
            score += (50 - min(max(out["rsi14"], 0), 100))/50.0
            count += 1.0
        if out.get("vol_norm") is not None:
            score += min(max(out["vol_norm"], 0), 3)/3.0
            count += 1.0
        out["score"] = (score / count) if count>0 else None
    except Exception:
        out["score"] = None

    # meta: symbol/tradingsymbol if available
    try:
        out["token"] = str(token)
        if "tradingsymbol" in df.columns:
            out["tradingsymbol"] = df["tradingsymbol"].dropna().iloc[-1] if not df["tradingsymbol"].dropna().empty else None
    except Exception:
        pass

    return out
