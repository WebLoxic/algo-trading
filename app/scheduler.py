# app/scheduler.py
"""
Scheduler:
  - news_fetch_job: Fetch headlines using NewsAPI, compute VADER sentiment, save to DB, publish to Redis.
  - retrain_job: Retrain ML model periodically.
  - refresh_kite_token_job: Clears old Kite token daily (so user re-logs for a fresh token before market open).

Config via .env:
  NEWSAPI_KEY, ML_TICKERS, NEWS_INTERVAL_MIN (default 10)
  RETRAIN_INTERVAL_MIN (default 10)
  KITE_API_KEY, KITE_API_SECRET, TOKEN_FILE (for kite)
"""

import os
import logging
import subprocess
import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import pytz

from .sentiment_analyzer import sentiment
from . import crud

# --- optional redis client hooks
try:
    from .redis_client import set_last_sentiment, publish_channel
    _have_redis = True
except Exception:
    _have_redis = False

# --- kite token refresh imports
try:
    from .kite_client import kite_client
except Exception:
    kite_client = None

# -------------------------
# Logging setup
# -------------------------
log = logging.getLogger(__name__)
log.setLevel(os.getenv("SCHEDULER_LOG_LEVEL", "INFO"))

# -------------------------
# Env/config
# -------------------------
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
ML_TICKERS = [t.strip() for t in os.getenv("ML_TICKERS", "RELIANCE.NS").split(",") if t.strip()]
try:
    NEWS_INTERVAL_MIN = int(os.getenv("NEWS_INTERVAL_MIN", "10"))
except Exception:
    NEWS_INTERVAL_MIN = 10

try:
    RETRAIN_INTERVAL_MIN = int(os.getenv("RETRAIN_INTERVAL_MIN", os.getenv("RETRAIN_HOUR", "").strip() or "10"))
except Exception:
    RETRAIN_INTERVAL_MIN = 10

PRIMARY_TICKER = os.getenv("PRIMARY_TICKER", ML_TICKERS[0] if ML_TICKERS else "RELIANCE.NS")

NEWSAPI_ENDPOINT = "https://newsapi.org/v2/everything"
_scheduler = None
_NEWS_JOB_ID = "news_fetch_job_v1"
_RETRAIN_JOB_ID = "retrain_job_v1"
_REFRESH_JOB_ID = "refresh_kite_token_job_v1"

IST = pytz.timezone("Asia/Kolkata")

# -------------------------
# News job
# -------------------------
def _fetch_headlines_for_query(query, page_size=25):
    if not NEWSAPI_KEY:
        raise RuntimeError("NEWSAPI_KEY not set in environment")
    params = {
        "q": query,
        "language": "en",
        "pageSize": page_size,
        "apiKey": NEWSAPI_KEY,
        "sortBy": "publishedAt"
    }
    r = requests.get(NEWSAPI_ENDPOINT, params=params, timeout=30)
    if r.status_code != 200:
        log.warning("NewsAPI returned %s for query=%s: %s", r.status_code, query, (r.text or "")[:200])
        return []
    data = r.json()
    articles = data.get("articles", []) or []
    headlines = [(a.get("title") or "") + " " + (a.get("description") or "") for a in articles]
    return [h.strip() for h in headlines if h.strip()]

def news_fetch_job():
    """Fetch headlines per ticker, compute VADER mean compound, save to DB, publish to Redis."""
    now = datetime.utcnow().isoformat()
    if not NEWSAPI_KEY:
        log.error("[%s] NEWSAPI_KEY not configured; news_fetch_job aborted.", now)
        return {"success": False, "error": "no_newsapi_key"}

    results = []
    for t in ML_TICKERS:
        query = t.split(".")[0] if "." in t else t
        log.info("[%s][news] Fetching for %s", now, query)
        try:
            headlines = _fetch_headlines_for_query(query, page_size=25)
            if not headlines:
                results.append({"ticker": t, "n_headlines": 0})
                continue

            scores = [sentiment.score(h).get("compound", 0.0) for h in headlines]
            scores = [float(s) for s in scores if isinstance(s, (int, float))]
            if not scores:
                continue

            avg_score = float(sum(scores) / len(scores))
            crud.save_sentiment(t, avg_score)
            log.info("[%s][news] %s: avg_compound=%.4f", now, t, avg_score)

            if _have_redis:
                payload = {"ticker": t, "score": avg_score, "fetched_at": datetime.utcnow().isoformat()}
                set_last_sentiment(t, payload)
                publish_channel("sentiment_updates", payload)

            results.append({"ticker": t, "score": avg_score})
        except Exception as e:
            log.exception("news_fetch_job failed for %s: %s", t, e)
            results.append({"ticker": t, "error": str(e)})
    return {"success": True, "fetched": results, "when": datetime.utcnow().isoformat()}

# -------------------------
# Retrain job
# -------------------------
def _run_train_via_ml_module(symbol, period=None, interval=None):
    try:
        from . import ml_model
    except Exception as e:
        log.debug("ml_model import failed: %s", e)
        return None

    candidates = [
        ("train_from_sources", {"symbol": symbol, "prefer": "yf_5m_60d", "period": period, "interval": interval}),
        ("train_from_yfinance", {"symbol": symbol, "period": period, "interval": interval}),
        ("train", {"symbol": symbol, "period": period, "interval": interval}),
        ("train_model", {"symbol": symbol, "period": period, "interval": interval}),
    ]
    for fname, kwargs in candidates:
        fn = getattr(ml_model, fname, None)
        if fn and callable(fn):
            try:
                log.info("Calling ml_model.%s(...)", fname)
                return fn(**{k: v for k, v in kwargs.items() if v is not None})
            except Exception as e:
                log.exception("ml_model.%s failed: %s", fname, e)
                return {"success": False, "error": str(e)}
    return None

def _run_train_via_script(symbol):
    cmd = [os.sys.executable, "-m", "scripts.train_reliance"]
    env = os.environ.copy()
    env["PRIMARY_TICKER"] = symbol
    log.info("Starting external training subprocess: %s", " ".join(cmd))
    try:
        p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=3600)
        if p.returncode == 0:
            return {"success": True, "stdout": p.stdout}
        else:
            return {"success": False, "stderr": p.stderr, "returncode": p.returncode}
    except subprocess.TimeoutExpired as e:
        log.exception("Training subprocess timed out: %s", e)
        return {"success": False, "error": "timeout"}

def retrain_job():
    start = datetime.utcnow().isoformat()
    symbol = PRIMARY_TICKER
    log.info("[%s][retrain] start symbol=%s", start, symbol)

    period = os.getenv("TRAIN_PERIOD", None)
    interval = os.getenv("TRAIN_INTERVAL", None)
    res = _run_train_via_ml_module(symbol, period=period, interval=interval)
    if res is None:
        log.info("ml_model training not found; using script fallback.")
        res = _run_train_via_script(symbol)

    if not isinstance(res, dict):
        res = {"success": False, "result": str(res)}

    end = datetime.utcnow().isoformat()
    log.info("[%s][retrain] finished: %s", end, json.dumps(res)[:1000])
    return {"success": True, "when": end, "result": res}

# -------------------------
# Kite token refresh job
# -------------------------
def refresh_kite_token_job():
    """Daily job: clear stored Kite token (force fresh login)."""
    if not kite_client:
        log.warning("Kite client not initialized; skipping token refresh.")
        return {"success": False, "reason": "no_kite_client"}

    try:
        log.info("Running refresh_kite_token_job: clearing Kite token.")
        kite_client.clear_token()
        if _have_redis:
            publish_channel("kite_token_events", {"event": "token_cleared", "when": datetime.utcnow().isoformat()})
        return {"success": True, "cleared": True}
    except Exception as e:
        log.exception("refresh_kite_token_job failed: %s", e)
        return {"success": False, "error": str(e)}

# -------------------------
# Scheduler lifecycle
# -------------------------
def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        log.info("Scheduler already running.")
        return _scheduler

    _scheduler = BackgroundScheduler(timezone=IST)

    # Remove old jobs if any
    for job_id in (_NEWS_JOB_ID, _RETRAIN_JOB_ID, _REFRESH_JOB_ID):
        try:
            _scheduler.remove_job(job_id)
        except Exception:
            pass

    _scheduler.add_job(
        func=news_fetch_job,
        trigger=IntervalTrigger(minutes=NEWS_INTERVAL_MIN),
        id=_NEWS_JOB_ID,
        name="fetch news and sentiment",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.add_job(
        func=retrain_job,
        trigger=IntervalTrigger(minutes=RETRAIN_INTERVAL_MIN),
        id=_RETRAIN_JOB_ID,
        name="retrain ML model",
        replace_existing=True,
        max_instances=1,
    )

    # 🕗 Daily token refresh at 8:30 AM IST
    _scheduler.add_job(
        func=refresh_kite_token_job,
        trigger=CronTrigger(hour=8, minute=30, timezone=IST),
        id=_REFRESH_JOB_ID,
        name="clear Kite token daily (force re-login)",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.start()
    log.info(
        "Scheduler started: news every %d min, retrain every %d min, refresh token daily 08:30 IST. ML_TICKERS=%s",
        NEWS_INTERVAL_MIN, RETRAIN_INTERVAL_MIN, ML_TICKERS,
    )
    return _scheduler

def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("Scheduler stopped.")

def get_scheduler_status():
    status = {"running": False, "jobs": []}
    if _scheduler is None:
        return status
    status["running"] = True
    try:
        for job in _scheduler.get_jobs():
            status["jobs"].append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "max_instances": job.max_instances,
            })
    except Exception as e:
        log.debug("Error reading scheduler jobs: %s", e)
    return status
