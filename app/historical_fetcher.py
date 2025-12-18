# app/historical_fetcher.py
"""
Fetch historical OHLC data using yfinance primary and AlphaVantage as fallback.
Return pandas.DataFrame with columns: open, high, low, close, volume
"""
import os
import pandas as pd
from alpha_vantage.timeseries import TimeSeries
import yfinance as yf

ALPHAVANTAGE_KEY = os.getenv("ALPHAVANTAGE_KEY", "")

def fetch_yfinance_ohlc(symbol: str, period: str = "1mo", interval: str = "5m") -> pd.DataFrame:
    """
    symbol example: 'RELIANCE.NS' for NSE Reliance on Yahoo Finance.
    period e.g. '1mo','3mo','1y'
    interval e.g. '1m','5m','15m','1h','1d'
    """
    try:
        df = yf.download(tickers=symbol, period=period, interval=interval, progress=False, threads=False)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
    df = df[["open","high","low","close","volume"]]
    return df

def fetch_alphavantage_intraday(symbol: str, interval: str = "5min", outputsize: str = "compact") -> pd.DataFrame:
    """
    AlphaVantage intraday fetch. symbol should be AlphaVantage-compatible (e.g., 'RELIANCE.BSE' or global tickers).
    Note: AlphaVantage free tier has rate limits. Use as fallback.
    """
    if not ALPHAVANTAGE_KEY:
        return pd.DataFrame()
    try:
        ts = TimeSeries(key=ALPHAVANTAGE_KEY, output_format='pandas')
        data, meta = ts.get_intraday(symbol=symbol, interval=interval, outputsize=outputsize)
        # rename columns if they are numbered
        cols = []
        for c in data.columns:
            if ". " in c:
                cols.append(c.split(". ", 1)[1])
            else:
                cols.append(c)
        data.columns = cols
        data = data.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
        for c in ["open","high","low","close","volume"]:
            if c not in data.columns:
                data[c] = 0
        return data[["open","high","low","close","volume"]]
    except Exception:
        return pd.DataFrame()

def fetch_recent_ohlc(symbol: str, provider_preference: str = "yfinance", period: str = "7d", interval: str = "5m") -> pd.DataFrame:
    """
    High-level: try yfinance first, then AlphaVantage fallback.
    For NSE tickers use Yahoo symbol like 'RELIANCE.NS'
    """
    if provider_preference == "yfinance":
        df = fetch_yfinance_ohlc(symbol, period=period, interval=interval)
        if df is not None and not df.empty:
            return df

    # fallback: pick alpha interval mapping
    av_interval = "5min"
    if interval.endswith("m"):
        av_interval = interval.replace("m", "min")
    elif interval.endswith("min"):
        av_interval = interval
    try:
        df = fetch_alphavantage_intraday(symbol, interval=av_interval, outputsize="compact")
        if df is not None and not df.empty:
            return df
    except Exception:
        pass

    return pd.DataFrame()
