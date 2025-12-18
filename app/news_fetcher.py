# app/news_fetcher.py
"""
Fetch headlines for a given ticker using NewsAPI.
Returns headlines (list of strings) and aggregated sentiment (using VADER in sentiment_analyzer).
Polygon news removed (India use-case).
"""
import os
import requests
from typing import List, Dict
from .sentiment_analyzer import sentiment

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

# Simple ticker -> query map. Extend for your universe.
TICKER_QUERY_MAP = {
    "RELIANCE": "Reliance Industries OR RELIANCE OR RIL",
    "TCS": "Tata Consultancy Services OR TCS",
    "INFY": "Infosys OR INFY",
    # add your tickers here...
}

def _newsapi_fetch(query: str, page_size: int = 50) -> List[Dict]:
    if not NEWSAPI_KEY:
        return []
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "pageSize": page_size,
        "language": "en",
        "sortBy": "publishedAt",
        "apiKey": NEWSAPI_KEY
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("articles", [])
    except Exception:
        return []

def fetch_headlines_for_ticker(ticker: str, page_size: int = 50) -> List[str]:
    """
    Return a list of headline strings for the given ticker.
    """
    q = TICKER_QUERY_MAP.get(ticker.upper(), ticker)
    headlines = []

    # NewsAPI
    articles = _newsapi_fetch(q, page_size=page_size)
    for a in articles:
        t = a.get("title")
        if t:
            headlines.append(t)

    return headlines

def aggregate_sentiment_for_ticker(ticker: str, window: int = 20) -> float:
    """
    Fetch latest headlines and return aggregated VADER compound score in [-1,1].
    Weighted by recency (newer headlines have higher weight).
    """
    headlines = fetch_headlines_for_ticker(ticker, page_size=window)
    if not headlines:
        return 0.0
    scores = []
    for h in headlines:
        try:
            s = sentiment.score(h)
            scores.append(s.get("compound", 0.0))
        except Exception:
            continue
    if not scores:
        return 0.0
    # weighted recency: weight = 1/(index+1)
    weights = [1 / (i + 1) for i in range(len(scores))]
    total_weight = sum(weights)
    weighted_avg = sum(sc * w for sc, w in zip(scores, weights)) / total_weight
    return float(weighted_avg)
