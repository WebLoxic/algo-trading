# scripts/run_news_fetch_now.py
"""
Manual test runner to fetch headlines from NewsAPI,
analyze sentiment via VADER (app/sentiment_analyzer),
and save to the database (public.sentiments table).
"""

import json
from app.scheduler import news_fetch_job

if __name__ == "__main__":
    print("▶ Running NewsAPI sentiment fetch job manually...")
    res = news_fetch_job()
    print(json.dumps(res, indent=2))
