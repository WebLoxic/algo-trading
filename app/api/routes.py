
# # app/api/routes.py
# from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Query, Depends
# from fastapi.responses import RedirectResponse
# from pathlib import Path
# import logging
# import os
# import asyncio
# from typing import List, Optional, Dict, Any
# from pydantic import BaseModel
# from datetime import datetime, timedelta
# import pandas as pd
# import numpy as np

# # internal imports (unchanged)
# from ..kite_client import kite_client
# from ..config import KITE_API_KEY, KITE_API_SECRET
# from ..streamer import start_websocket, get_latest_ticks, subscribe as streamer_subscribe, kite_ticker
# from ..strategy import StrategyEngine
# from ..order_manager import OrderManager
# from ..indicators import compute_signals
# from ..crud import get_latest_model, get_latest_sentiment
# from .. import ml_model
# from ..scheduler import retrain_job

# # Payment / wallet routers / broker routes (must expose `router`)
# from app.api import payment_routes, wallet_routes, broker_routes

# # Admin deps (get_db should return SQLAlchemy Session; require_admin checks admin)
# from app.deps import get_db, require_admin  # adjust if naming differs

# # Try to import ORM models (optional — fallback to raw SQL if not present)
# try:
#     from app.models import User, Subscription, WalletTransaction, CredentialHistory
# except Exception:
#     User = None
#     Subscription = None
#     WalletTransaction = None
#     CredentialHistory = None

# from sqlalchemy.orm import Session
# from sqlalchemy import text

# # Single API router (do NOT redefine later)
# api_router = APIRouter()
# api_router.include_router(payment_routes.router)
# api_router.include_router(wallet_routes.router)
# api_router.include_router(broker_routes.router)

# # Export name expected by main.py
# router = api_router

# log = logging.getLogger(__name__)
# log.setLevel(os.getenv("LOG_LEVEL", "INFO"))

# STORAGE_DIR = Path("app") / "storage"
# STORAGE_DIR.mkdir(parents=True, exist_ok=True)


# # -------------------------
# # Request / small Models
# # -------------------------
# class SubscribeRequest(BaseModel):
#     tokens: List[int]


# class PlaceOrderRequest(BaseModel):
#     tradingsymbol: Optional[str] = None
#     instrument_token: Optional[int] = None
#     transaction_type: str
#     quantity: Optional[int] = None
#     amount: Optional[float] = None
#     product: str = "MIS"
#     order_type: str = "MARKET"
#     price: Optional[float] = None
#     exchange: str = "NSE"


# # Log instruments count on import if available (helps detect empty load)
# try:
#     _count = len(getattr(kite_client, "instruments", []) or [])
#     log.info("KiteClient instruments loaded: %d", _count)
# except Exception:
#     log.debug("Could not determine instruments count on startup")


# # -------------------------
# # Basic endpoints
# # -------------------------
# @router.get("/get_zerodha_api_key")
# def get_zerodha_api_key():
#     if not KITE_API_KEY:
#         raise HTTPException(status_code=500, detail="KITE_API_KEY not configured")
#     return {"apiKey": KITE_API_KEY}


# @router.get("/login_url")
# def login_url():
#     redirect = os.getenv("ZERODHA_REDIRECT_URL", "http://localhost:8000/api/auth_callback")
#     url = f"https://kite.zerodha.com/connect/login?v=3&api_key={KITE_API_KEY}&redirect_url={redirect}"
#     return {"login_url": url}


# @router.get("/login_status")
# def login_status():
#     token_present = bool(getattr(kite_client, "access_token", None))
#     return {"kite_loaded": token_present, "access_token_present": token_present}


# # -------------------------
# # Auth callback
# # -------------------------
# @router.get("/auth_callback")
# async def auth_callback(request: Request):
#     request_token = request.query_params.get("request_token")
#     if not request_token:
#         raise HTTPException(status_code=400, detail="request_token missing")

#     if getattr(kite_client, "access_token", None):
#         frontend_url = os.getenv("FRONTEND_REDIRECT_AFTER_LOGIN", "http://localhost:5173/dashboard?login=success")
#         return RedirectResponse(url=frontend_url)

#     try:
#         data = kite_client.kite.generate_session(request_token, KITE_API_SECRET)
#         kite_client.save_token(data)
#         try:
#             start_websocket(kite_client.kite.api_key, kite_client.access_token)
#         except Exception:
#             log.exception("Failed to start websocket after auth callback")
#         frontend_url = os.getenv("FRONTEND_REDIRECT_AFTER_LOGIN", "http://localhost:5173/dashboard?login=success")
#         return RedirectResponse(url=frontend_url)
#     except Exception as e:
#         log.exception("auth_callback exchange failed")
#         raise HTTPException(status_code=500, detail=str(e))


# # -------------------------
# # Subscribe ticker
# # -------------------------
# @router.post("/subscribe")
# async def api_subscribe(payload: SubscribeRequest):
#     tokens = payload.tokens or []
#     if not tokens:
#         raise HTTPException(status_code=400, detail="No tokens provided")
#     streamer_subscribe(tokens)
#     return {"subscribed": tokens}


# # -------------------------
# # Strategy / Signals / Mode
# # -------------------------
# @router.get("/signals/{token}")
# def get_signals(token: int):
#     sig = compute_signals(token)
#     om = OrderManager.instance()
#     last_reg = om.get_signals().get(token) if om else None
#     return {"signals": sig, "last_registered": last_reg}


# @router.get("/last_signals")
# def last_signals():
#     om = OrderManager.instance()
#     return om.get_signals()


# @router.get("/mode")
# def get_mode():
#     return {"mode": StrategyEngine.instance().mode}


# @router.post("/mode")
# def set_mode(payload: Dict[str, Any]):
#     mode = payload.get("mode")
#     if mode not in ("manual", "auto"):
#         raise HTTPException(status_code=400, detail="mode must be 'manual' or 'auto'")
#     StrategyEngine.instance().set_mode(mode)
#     log.info("Trading mode changed to: %s", mode.upper())
#     return {"mode": mode, "status": "updated"}


# # -------------------------
# # Models metadata listing
# # -------------------------
# @router.get("/models")
# def list_models():
#     files = sorted([f.name for f in STORAGE_DIR.iterdir() if f.suffix == ".pkl"], reverse=True)
#     return {"models": files}


# @router.get("/models/latest")
# def latest_model_meta():
#     m = get_latest_model()
#     if not m:
#         raise HTTPException(status_code=404, detail="No model found")
#     return {
#         "filename": getattr(m, "filename", None),
#         "created_at": getattr(m, "created_at", None).isoformat() if getattr(m, "created_at", None) else None,
#         "rows": getattr(m, "rows", None),
#         "metrics": getattr(m, "metrics", None),
#         "active": getattr(m, "active", None),
#     }


# @router.post("/models/activate")
# def activate_model(payload: Dict[str, Any]):
#     fn = payload.get("filename")
#     latest = payload.get("latest", False)
#     if latest or not fn:
#         m = ml_model.load_latest()
#         return {"status": "ok", "loaded": getattr(ml_model, "model_path", None)}
#     candidate = (STORAGE_DIR / fn).resolve()
#     ml_model.load(str(candidate))
#     return {"status": "ok", "loaded": getattr(ml_model, "model_path", None)}


# @router.post("/retrain_manual")
# def retrain_manual(background_tasks: BackgroundTasks):
#     background_tasks.add_task(retrain_job)
#     return {"status": "retrain started"}


# # -------------------------
# # Sentiment
# # -------------------------
# @router.get("/sentiment/{ticker}")
# def get_sentiment(ticker: str):
#     s = get_latest_sentiment(ticker)
#     if not s:
#         raise HTTPException(status_code=404, detail="no sentiment found")
#     return {"ticker": s.ticker, "score": s.score, "fetched_at": s.fetched_at.isoformat()}


# # -------------------------
# # Candles (historical endpoint used by frontend)
# # -------------------------
# @router.get("/candles")
# def get_candles(symbol: str = Query(..., description="tradingsymbol or instrument token"),
#                 interval: str = Query("1minute", description="interval like 1minute, 5minute, day"),
#                 limit: int = Query(500, ge=1, le=2000)):
#     """
#     Returns an array of candles for frontend:
#     [{ "t": <ms epoch>, "o":<float>, "h":<float>, "l":<float>, "c":<float>, "v":<float> }, ...]
#     """
#     try:
#         instrument_token = None
#         # if symbol is an integer token
#         try:
#             if str(symbol).isdigit():
#                 instrument_token = int(symbol)
#             else:
#                 try:
#                     instrument_token = kite_client.get_instrument_token(symbol)
#                 except Exception:
#                     instrument_token = None
#         except Exception:
#             instrument_token = None

#         candles = []
#         if instrument_token:
#             try:
#                 # map interval aliases if needed (simple mapping; expand as required)
#                 kite_interval = interval
#                 if interval in ("1m", "1minute", "minute"):
#                     kite_interval = "minute"
#                 elif interval in ("5m", "5minute"):
#                     kite_interval = "5minute"
#                 elif interval in ("day", "1d"):
#                     kite_interval = "day"
#                 # fetch last 7 days as default (adjust as needed)
#                 candles = kite_client.kite.historical_data(instrument_token, datetime.utcnow() - timedelta(days=7), datetime.utcnow(), interval=kite_interval) or []
#                 log.info("Fetched %d historical candles for %s", len(candles), symbol)
#             except Exception as e:
#                 log.warning("Failed to fetch kite historical for %s: %s", symbol, e)
#                 candles = []

#         if not candles:
#             # fallback synthetic data
#             now = datetime.utcnow()
#             size = min(limit, 500)
#             times = [now - timedelta(minutes=1 * i) for i in range(size)][::-1]
#             vals = (np.cumsum(np.random.randn(size)) + 1000).tolist()
#             candles = []
#             for dt, v in zip(times, vals):
#                 o = v + np.random.rand() * 2 - 1
#                 h = max(v, o) + np.random.rand() * 1.5
#                 l = min(v, o) - np.random.rand() * 1.5
#                 c = v + np.random.rand() * 2 - 1
#                 candles.append({"date": dt, "open": o, "high": h, "low": l, "close": c, "volume": float(np.random.randint(1, 1000))})

#         # Normalize and return ms timestamps
#         out = []
#         for c in candles[-limit:]:
#             dt = None
#             if isinstance(c.get("date"), (str, datetime)):
#                 dt = pd.to_datetime(c.get("date"))
#             elif "timestamp" in c:
#                 try:
#                     ts = int(c.get("timestamp"))
#                     dt = datetime.utcfromtimestamp(ts // 1000) if ts > 1_000_000_000_000 else datetime.utcfromtimestamp(ts)
#                 except Exception:
#                     dt = None
#             if dt is None:
#                 dt = datetime.utcnow()

#             t_ms = int(dt.timestamp() * 1000)
#             o = float(c.get("open") or c.get("o") or c.get("open_price") or 0)
#             h = float(c.get("high") or c.get("h") or c.get("high_price") or o)
#             l = float(c.get("low") or c.get("l") or c.get("low_price") or o)
#             cc = float(c.get("close") or c.get("c") or c.get("close_price") or o)
#             v = float(c.get("volume") or c.get("v") or c.get("vol") or 0)
#             out.append({"t": t_ms, "o": o, "h": h, "l": l, "c": cc, "v": v})

#         return {"ok": True, "candles": out}
#     except Exception as e:
#         log.exception("get_candles failed")
#         raise HTTPException(status_code=500, detail=str(e))


# # -------------------------
# # Indicators
# # -------------------------
# @router.get("/indicators")
# def indicators_for_symbol(symbol: str = Query(..., description="tradingsymbol or instrument token")):
#     """
#     Returns multiple indicator series for a symbol.
#     - Attempts to resolve instrument token; if not available, tries to use symbol as-is.
#     - Always returns timestamps as UNIX seconds.
#     """
#     try:
#         from_date = datetime.now() - timedelta(days=3)
#         to_date = datetime.now()
#         instrument_token = None

#         try:
#             instrument_token = kite_client.get_instrument_token(symbol)
#             log.debug("Resolved instrument_token for %s -> %s", symbol, instrument_token)
#         except Exception:
#             log.warning("Could not resolve instrument token for %s (will try as symbol).", symbol)

#         candles = []
#         if instrument_token:
#             try:
#                 candles = kite_client.kite.historical_data(instrument_token, from_date, to_date, interval="5minute") or []
#                 log.info("Fetched %d historical candles for %s", len(candles), symbol)
#             except Exception as e:
#                 log.warning("Failed to fetch historical data for %s: %s", symbol, e)

#         if not candles:
#             now = datetime.now()
#             timestamps = [now - timedelta(minutes=5 * i) for i in range(100)][::-1]
#             close_prices = np.cumsum(np.random.randn(100)) + 2500
#             df = pd.DataFrame({"date": timestamps, "close": close_prices})
#         else:
#             df = pd.DataFrame(candles)
#             if "date" in df.columns:
#                 df["date"] = pd.to_datetime(df["date"])
#             elif "timestamp" in df.columns:
#                 df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
#             elif "tradetime" in df.columns:
#                 df["date"] = pd.to_datetime(df["tradetime"], unit="ms")
#             else:
#                 df["date"] = pd.date_range(end=datetime.now(), periods=len(df), freq="5T")

#             if "close" not in df.columns and "close_price" in df.columns:
#                 df["close"] = df["close_price"]

#         df = df.reset_index(drop=True)
#         df["sma"] = df["close"].rolling(window=14, min_periods=1).mean()
#         df["ema"] = df["close"].ewm(span=14, adjust=False).mean()
#         delta = df["close"].diff()
#         gain = delta.where(delta > 0, 0)
#         loss = -delta.where(delta < 0, 0)
#         avg_gain = gain.rolling(window=14, min_periods=1).mean()
#         avg_loss = loss.rolling(window=14, min_periods=1).mean()
#         rs = avg_gain / avg_loss.replace(0, np.nan)
#         df["rsi"] = 100 - (100 / (1 + rs.fillna(0)))
#         short_ema = df["close"].ewm(span=12, adjust=False).mean()
#         long_ema = df["close"].ewm(span=26, adjust=False).mean()
#         df["macd"] = short_ema - long_ema
#         df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

#         data = {
#             "sma": [{"time": int(row.date.timestamp()), "value": float(row.sma)} for _, row in df.iterrows() if not np.isnan(row.sma)],
#             "ema": [{"time": int(row.date.timestamp()), "value": float(row.ema)} for _, row in df.iterrows() if not np.isnan(row.ema)],
#             "rsi": [{"time": int(row.date.timestamp()), "value": float(row.rsi)} for _, row in df.iterrows() if not np.isnan(row.rsi)],
#             "macd": [{"time": int(row.date.timestamp()), "macd": float(row.macd), "signal": float(row.macd_signal)} for _, row in df.iterrows() if not np.isnan(row.macd)],
#         }

#         return {"ok": True, "data": data}
#     except Exception as e:
#         log.exception("indicators compute failed")
#         raise HTTPException(status_code=500, detail=f"indicators compute failed: {e}")


# # -------------------------
# # Predict (ML)
# # -------------------------
# @router.get("/predict/{ticker}")
# def predict_ticker(ticker: str):
#     try:
#         if not hasattr(ml_model, "predict"):
#             raise HTTPException(status_code=404, detail="ML model predict function not available")
#         pred = ml_model.predict(ticker)
#         return {"ok": True, "prediction": pred}
#     except HTTPException:
#         raise
#     except Exception as e:
#         log.exception("predict failed")
#         raise HTTPException(status_code=500, detail=f"predict failed: {e}")


# # -------------------------
# # Order Execution
# # -------------------------
# @router.post("/order/manual")
# def place_order_api(payload: PlaceOrderRequest):
#     try:
#         quantity_to_place = payload.quantity or 1
#         if not payload.tradingsymbol:
#             raise HTTPException(status_code=400, detail="tradingsymbol required")

#         params = dict(
#             variety="regular",
#             exchange=payload.exchange,
#             tradingsymbol=payload.tradingsymbol,
#             transaction_type=payload.transaction_type,
#             quantity=int(quantity_to_place),
#             product=payload.product,
#             order_type=payload.order_type,
#         )
#         if payload.price is not None:
#             params["price"] = float(payload.price)

#         res = kite_client.place_order(**params)
#         return {"status": "success", "order_response": res}
#     except HTTPException:
#         raise
#     except Exception as e:
#         log.exception("Place order failed")
#         raise HTTPException(status_code=500, detail=f"Place order failed: {e}")


# @router.post("/place-order")
# def place_order_frontend(payload: PlaceOrderRequest):
#     return place_order_api(payload)


# # -------------------------
# # Positions / Holdings
# # -------------------------
# @router.get("/orders")
# def list_orders():
#     try:
#         return kite_client.orders()
#     except Exception as e:
#         log.exception("Failed to list orders")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/positions")
# def positions():
#     try:
#         return kite_client.positions()
#     except Exception as e:
#         log.exception("Failed to fetch positions")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/holdings")
# def holdings():
#     try:
#         return kite_client.holdings()
#     except Exception as e:
#         log.exception("Failed to fetch holdings")
#         raise HTTPException(status_code=500, detail=str(e))


# # -------------------------
# # Session info
# # -------------------------
# @router.get("/session-info")
# async def session_info(symbol: str):
#     """
#     Returns API keys/tokens and resolved instrument token if available.
#     If instrument token cannot be resolved we return instrumentToken=None (frontend should handle).
#     """
#     try:
#         token_data = getattr(kite_client, "session_data", None) or {}
#         access_token = token_data.get("access_token") or getattr(kite_client, "access_token", None)
#         if not access_token:
#             log.warning("session-info: access token missing")
#             raise HTTPException(status_code=401, detail="Access token not found. Please login again.")

#         instrument_token = None
#         try:
#             instrument_token = kite_client.get_instrument_token(symbol)
#         except Exception as e:
#             log.warning("session-info: could not resolve instrument token for %s: %s", symbol, e)
#             return {"apiKey": KITE_API_KEY, "accessToken": access_token, "instrumentToken": None, "initialCandles": []}

#         return {"apiKey": KITE_API_KEY, "accessToken": access_token, "instrumentToken": instrument_token, "initialCandles": []}
#     except HTTPException:
#         raise
#     except Exception as e:
#         log.exception("Session-info failed")
#         raise HTTPException(status_code=500, detail=str(e))


# # -------------------------
# # Health / config
# # -------------------------
# @router.get("/health")
# def health():
#     return {"status": "ok"}


# @router.get("/config")
# def config():
#     loaded = getattr(ml_model, "model", None) is not None
#     return {
#         "kite_loaded": bool(getattr(kite_client, "access_token", None)),
#         "model_loaded": loaded,
#         "model_path": getattr(ml_model, "model_path", None),
#         "storage_dir": str(STORAGE_DIR),
#     }


# # -------------------------
# # Kite socket status
# # -------------------------
# @router.get("/kite/status")
# def kite_status():
#     try:
#         if kite_ticker and kite_ticker.is_connected():
#             return {"connected": True, "message": "Kite WebSocket active"}
#         else:
#             return {"connected": False, "message": "Kite WebSocket not connected"}
#     except Exception as e:
#         log.exception("kite status check failed")
#         return {"connected": False, "error": str(e)}


# # -------------------------
# # Notifications / market prediction endpoints
# # -------------------------
# @router.get("/notifications/latest")
# def notifications_latest(limit: int = 10, symbol: Optional[str] = None):
#     om = OrderManager.instance()
#     signals = om.get_signals() if om else {}

#     ml_last = None
#     try:
#         ml_last = getattr(ml_model, "last_prediction", None)
#     except Exception:
#         ml_last = None

#     sentiment = None
#     if symbol:
#         try:
#             s = get_latest_sentiment(symbol)
#             if s:
#                 sentiment = {"ticker": s.ticker, "score": s.score, "fetched_at": s.fetched_at.isoformat()}
#         except Exception:
#             sentiment = None

#     recent_signals = {}
#     try:
#         items = []
#         for k, v in signals.items():
#             ts = v.get("ts") if isinstance(v, dict) else None
#             items.append((k, v, ts))
#         items_sorted = sorted(items, key=lambda x: x[2] or "", reverse=True)
#         for k, v, _ in items_sorted[:limit]:
#             recent_signals[k] = v
#     except Exception:
#         recent_signals = signals

#     return {"ok": True, "signals": recent_signals, "ml_last": ml_last, "sentiment": sentiment}


# @router.get("/market-prediction/latest")
# def market_prediction_latest():
#     try:
#         last = getattr(ml_model, "last_prediction", None)
#         if not last:
#             return {"ok": False, "message": "No prediction available yet"}
#         return {"ok": True, "prediction": last}
#     except Exception as e:
#         log.exception("market_prediction_latest failed")
#         raise HTTPException(status_code=500, detail=f"market_prediction_latest failed: {e}")


# @router.get("/latest-signal")
# def latest_signal():
#     try:
#         ml_last = None
#         try:
#             ml_last = getattr(ml_model, "last_prediction", None)
#         except Exception:
#             ml_last = None

#         om = OrderManager.instance()
#         signals = om.get_signals() if om else {}

#         return {"ok": True, "ml_last": ml_last, "signals": signals}
#     except Exception as e:
#         log.exception("latest_signal failed")
#         raise HTTPException(status_code=500, detail=f"latest_signal failed: {e}")


# # -------------------------
# # Live signals websocket
# # -------------------------
# @router.websocket("/ws/signals")
# async def ws_signals(websocket: WebSocket):
#     await websocket.accept()
#     log.info("📡 Frontend connected to /ws/signals")
#     try:
#         price_buffer = []
#         while True:
#             try:
#                 ticks = get_latest_ticks() or []
#                 if not ticks:
#                     await asyncio.sleep(1)
#                     continue

#                 tick = ticks[0]
#                 price = tick.get("last_price") or tick.get("last_trade_price") or tick.get("lastTradedPrice") or None
#                 timestamp = tick.get("timestamp") or tick.get("time") or None

#                 # Normalize timestamp -> UNIX seconds integer
#                 if timestamp is None:
#                     timestamp = int(datetime.utcnow().timestamp())
#                 else:
#                     if isinstance(timestamp, str):
#                         try:
#                             ts = datetime.fromisoformat(timestamp)
#                             timestamp = int(ts.timestamp())
#                         except Exception:
#                             try:
#                                 tsint = int(float(timestamp))
#                                 timestamp = int(tsint / 1000) if tsint > 1_000_000_000_000 else int(tsint)
#                             except Exception:
#                                 timestamp = int(datetime.utcnow().timestamp())
#                     elif isinstance(timestamp, (int, float)):
#                         tsval = int(timestamp)
#                         if tsval > 1_000_000_000_000:
#                             timestamp = int(tsval / 1000)
#                         else:
#                             timestamp = int(tsval)

#                 if price is not None and timestamp:
#                     price_buffer.append({"time": timestamp, "price": float(price)})

#                 price_buffer = price_buffer[-500:]
#                 df = pd.DataFrame(price_buffer)

#                 if len(df) > 0:
#                     try:
#                         if len(df) >= 3:
#                             df["sma"] = df["price"].rolling(window=5, min_periods=1).mean()
#                             df["ema"] = df["price"].ewm(span=5, adjust=False).mean()
#                             delta = df["price"].diff()
#                             gain = delta.where(delta > 0, 0)
#                             loss = -delta.where(delta < 0, 0)
#                             avg_gain = gain.rolling(window=5, min_periods=1).mean()
#                             avg_loss = loss.rolling(window=5, min_periods=1).mean()
#                             rs = avg_gain / avg_loss.replace(0, np.nan)
#                             df["rsi"] = 100 - (100 / (1 + rs.fillna(0)))
#                             short_ema = df["price"].ewm(span=12, adjust=False).mean()
#                             long_ema = df["price"].ewm(span=26, adjust=False).mean()
#                             df["macd"] = short_ema - long_ema
#                             df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

#                         data = {
#                             "candles": [{"time": int(row.time), "close": float(row.price)} for _, row in df.iterrows()],
#                             "sma": [{"time": int(row.time), "value": float(row.sma)} for _, row in df.iterrows() if not np.isnan(row.get("sma", np.nan))],
#                             "ema": [{"time": int(row.time), "value": float(row.ema)} for _, row in df.iterrows() if not np.isnan(row.get("ema", np.nan))],
#                             "rsi": [{"time": int(row.time), "value": float(row.rsi)} for _, row in df.iterrows() if not np.isnan(row.get("rsi", np.nan))],
#                             "macd": [{"time": int(row.time), "macd": float(row.macd), "signal": float(row.macd_signal)} for _, row in df.iterrows() if not np.isnan(row.get("macd", np.nan))],
#                         }

#                         await websocket.send_json(data)
#                     except Exception as inner_e:
#                         log.exception("Failed to compute/send ws signal: %s", inner_e)

#                 await asyncio.sleep(1)
#             except WebSocketDisconnect:
#                 log.info("⚠️ WebSocket client disconnected")
#                 break
#             except Exception as e:
#                 log.exception("Error in /ws/signals loop: %s", e)
#                 await asyncio.sleep(2)
#     finally:
#         try:
#             await websocket.close()
#         except Exception:
#             pass


# # -------------------------
# # ML market WS handler
# # -------------------------
# from app.ws_broadcast import ws_handler  # keep here for import ordering

# @router.websocket("/ws/market")
# async def ws_market(websocket: WebSocket):
#     await ws_handler(websocket)


# # -------------------------
# # Admin helpers & endpoints
# # -------------------------
# def _row_to_dict(row):
#     try:
#         return dict(row)
#     except Exception:
#         d = {}
#         for k in dir(row):
#             if k.startswith("_"):
#                 continue
#             try:
#                 v = getattr(row, k)
#                 if not callable(v):
#                     d[k] = v
#             except Exception:
#                 continue
#         return d


# @router.get("/admin/users", dependencies=[Depends(require_admin)])
# def admin_list_users(limit: int = 50, offset: int = 0, email: Optional[str] = None, db: Session = Depends(get_db)):
#     try:
#         if User is not None:
#             q = db.query(User)
#             if email and hasattr(User, "email"):
#                 q = q.filter(User.email.ilike(f"%{email}%"))
#             total = q.count()
#             rows = q.order_by(getattr(User, "created_at", getattr(User, "id")).desc()).limit(limit).offset(offset).all()
#             users = []
#             for u in rows:
#                 users.append({
#                     "id": getattr(u, "id", None),
#                     "email": getattr(u, "email", None),
#                     "name": getattr(u, "full_name", getattr(u, "name", None)),
#                     "created_at": getattr(u, "created_at", None),
#                     "is_active": getattr(u, "is_active", None),
#                     "raw": {k: getattr(u, k) for k in getattr(u, "__dict__", {}) if not k.startswith("_")}
#                 })
#             return {"ok": True, "total": total, "users": users}

#         sql = "SELECT id, email, COALESCE(full_name, name) as name, created_at, is_active FROM users WHERE 1=1 "
#         params = {}
#         if email:
#             sql += " AND email ILIKE :email "
#             params["email"] = f"%{email}%"
#         sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
#         params["limit"] = limit
#         params["offset"] = offset
#         res = db.execute(text(sql), params)
#         rows = [dict(r) for r in res.fetchall()]
#         return {"ok": True, "total": len(rows), "users": rows}
#     except Exception as e:
#         log.exception("admin_list_users failed")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/admin/subscriptions", dependencies=[Depends(require_admin)])
# def admin_list_subscriptions(limit: int = 50, offset: int = 0, email: Optional[str] = None, status: Optional[str] = None, plan_id: Optional[str] = None, db: Session = Depends(get_db)):
#     try:
#         if Subscription is not None:
#             q = db.query(Subscription)
#             if email and hasattr(Subscription, "email"):
#                 q = q.filter(Subscription.email.ilike(f"%{email}%"))
#             if status and hasattr(Subscription, "status"):
#                 q = q.filter(Subscription.status == status)
#             if plan_id and hasattr(Subscription, "plan_id"):
#                 q = q.filter(Subscription.plan_id == plan_id)
#             total = q.count()
#             rows = q.order_by(getattr(Subscription, "started", Subscription.id).desc()).limit(limit).offset(offset).all()
#             subs = []
#             for s in rows:
#                 subs.append({
#                     "id": getattr(s, "id", None),
#                     "email": getattr(s, "email", None),
#                     "plan": getattr(s, "plan_name", getattr(s, "plan", getattr(s, "plan_id", None))),
#                     "plan_id": getattr(s, "plan_id", None),
#                     "billing": getattr(s, "billing", None),
#                     "amount": getattr(s, "amount", None),
#                     "status": getattr(s, "status", None),
#                     "started": getattr(s, "started", None),
#                     "ends": getattr(s, "ends", None),
#                     "invoice": getattr(s, "invoice", None),
#                 })
#             return {"ok": True, "total": total, "subscriptions": subs}

#         sql = "SELECT id, email, plan_name AS plan, plan_id, billing, amount, status, started, ends, invoice FROM subscriptions WHERE 1=1 "
#         params = {}
#         if email:
#             sql += " AND email ILIKE :email "
#             params["email"] = f"%{email}%"
#         if status:
#             sql += " AND status = :status "
#             params["status"] = status
#         if plan_id:
#             sql += " AND plan_id = :plan_id "
#             params["plan_id"] = plan_id
#         sql += " ORDER BY started DESC LIMIT :limit OFFSET :offset"
#         params["limit"] = limit
#         params["offset"] = offset
#         res = db.execute(text(sql), params)
#         rows = [dict(r) for r in res.fetchall()]
#         return {"ok": True, "total": len(rows), "subscriptions": rows}
#     except Exception as e:
#         log.exception("admin_list_subscriptions failed")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/admin/payments", dependencies=[Depends(require_admin)])
# def admin_list_payments(limit: int = 50, offset: int = 0, email: Optional[str] = None, status: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None, db: Session = Depends(get_db)):
#     try:
#         if WalletTransaction is not None:
#             q = db.query(WalletTransaction)
#             if email and hasattr(WalletTransaction, "email"):
#                 q = q.filter(WalletTransaction.email.ilike(f"%{email}%"))
#             if status and hasattr(WalletTransaction, "status"):
#                 q = q.filter(WalletTransaction.status == status)
#             if date_from:
#                 try:
#                     df = datetime.fromisoformat(date_from)
#                     if hasattr(WalletTransaction, "created_at"):
#                         q = q.filter(WalletTransaction.created_at >= df)
#                 except Exception:
#                     pass
#             if date_to:
#                 try:
#                     dt = datetime.fromisoformat(date_to)
#                     if hasattr(WalletTransaction, "created_at"):
#                         q = q.filter(WalletTransaction.created_at <= dt)
#                 except Exception:
#                     pass
#             total = q.count()
#             rows = q.order_by(getattr(WalletTransaction, "created_at", WalletTransaction.id).desc()).limit(limit).offset(offset).all()
#             out = []
#             for t in rows:
#                 out.append({
#                     "id": getattr(t, "id", None),
#                     "email": getattr(t, "email", None),
#                     "amount": getattr(t, "amount", None),
#                     "status": getattr(t, "status", None),
#                     "note": getattr(t, "note", None),
#                     "created_at": getattr(t, "created_at", None),
#                     "payment_id": getattr(t, "payment_id", None),
#                     "order_id": getattr(t, "order_id", None),
#                 })
#             return {"ok": True, "total": total, "payments": out}

#         sql = "SELECT id, email, amount, status, note, created_at, payment_id, order_id FROM wallet_transactions WHERE 1=1 "
#         params = {}
#         if email:
#             sql += " AND email ILIKE :email "
#             params["email"] = f"%{email}%"
#         if status:
#             sql += " AND status = :status "
#             params["status"] = status
#         if date_from:
#             sql += " AND created_at >= :date_from "
#             params["date_from"] = date_from
#         if date_to:
#             sql += " AND created_at <= :date_to "
#             params["date_to"] = date_to
#         sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
#         params["limit"] = limit
#         params["offset"] = offset
#         res = db.execute(text(sql), params)
#         rows = [dict(r) for r in res.fetchall()]
#         return {"ok": True, "total": len(rows), "payments": rows}
#     except Exception as e:
#         log.exception("admin_list_payments failed")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/admin/credentials", dependencies=[Depends(require_admin)])
# def admin_list_credentials(limit: int = 50, offset: int = 0, email: Optional[str] = None, db: Session = Depends(get_db)):
#     try:
#         if CredentialHistory is not None:
#             q = db.query(CredentialHistory)
#             if email and hasattr(CredentialHistory, "email"):
#                 q = q.filter(CredentialHistory.email.ilike(f"%{email}%"))
#             total = q.count()
#             rows = q.order_by(getattr(CredentialHistory, "created_at", CredentialHistory.id).desc()).limit(limit).offset(offset).all()
#             out = []
#             for r in rows:
#                 out.append({
#                     "id": getattr(r, "id", None),
#                     "email": getattr(r, "email", None),
#                     "event": getattr(r, "event", None),
#                     "meta": getattr(r, "meta", None),
#                     "created_at": getattr(r, "created_at", None),
#                 })
#             return {"ok": True, "total": total, "credentials": out}

#         sql = "SELECT id, email, event, meta, created_at FROM credential_history WHERE 1=1 "
#         params = {}
#         if email:
#             sql += " AND email ILIKE :email "
#             params["email"] = f"%{email}%"
#         sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
#         params["limit"] = limit
#         params["offset"] = offset
#         res = db.execute(text(sql), params)
#         rows = [dict(r) for r in res.fetchall()]
#         return {"ok": True, "total": len(rows), "credentials": rows}
#     except Exception as e:
#         log.exception("admin_list_credentials failed")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/admin/summary", dependencies=[Depends(require_admin)])
# def admin_summary(db: Session = Depends(get_db)):
#     try:
#         result = {}
#         if User is not None:
#             total_users = db.query(User).count()
#             recent_signups = 0
#             try:
#                 recent_signups = db.query(User).filter(getattr(User, "created_at", None) >= datetime.utcnow() - timedelta(days=7)).count()
#             except Exception:
#                 recent_signups = 0
#             result["total_users"] = total_users
#             result["recent_signups_7d"] = recent_signups
#         else:
#             r = db.execute(text("SELECT COUNT(1) as c FROM users"))
#             result["total_users"] = int(r.scalar() or 0)

#         if Subscription is not None:
#             try:
#                 active = db.query(Subscription).filter(getattr(Subscription, "status", None) == "active").count()
#             except Exception:
#                 active = 0
#             result["active_subscriptions"] = active
#         else:
#             r = db.execute(text("SELECT COUNT(1) FROM subscriptions WHERE status = 'active'"))
#             try:
#                 result["active_subscriptions"] = int(r.scalar() or 0)
#             except Exception:
#                 result["active_subscriptions"] = 0

#         try:
#             r = db.execute(text("SELECT COALESCE(SUM(amount),0) FROM wallet_transactions WHERE status='success' AND created_at >= :d"), {"d": (datetime.utcnow() - timedelta(days=30)).isoformat()})
#             total_rev = float(r.scalar() or 0)
#             result["revenue_30d"] = total_rev
#         except Exception:
#             result["revenue_30d"] = 0.0

#         return {"ok": True, "summary": result}
#     except Exception as e:
#         log.exception("admin_summary failed")
#         raise HTTPException(status_code=500, detail=str(e))

# # End of file














# # app/api/routes.py
# from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Query, Depends
# from fastapi.responses import RedirectResponse
# from pathlib import Path
# import logging
# import os
# import asyncio
# from typing import List, Optional, Dict, Any
# from pydantic import BaseModel
# from datetime import datetime, timedelta
# import pandas as pd
# import numpy as np

# log = logging.getLogger(__name__)
# log.setLevel(os.getenv("LOG_LEVEL", "INFO"))

# # storage dir
# STORAGE_DIR = Path("app") / "storage"
# STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# # try to import kite_client and helpers defensively
# try:
#     from ..kite_client import kite_client
# except Exception:
#     kite_client = None

# try:
#     from ..config import KITE_API_KEY, KITE_API_SECRET
# except Exception:
#     KITE_API_KEY = None
#     KITE_API_SECRET = None

# # streamer helpers (subscribe, start_websocket, get_latest_ticks, kite_ticker)
# try:
#     from ..streamer import subscribe as streamer_subscribe, start_websocket, get_latest_ticks, kite_ticker
# except Exception:
#     streamer_subscribe = None
#     start_websocket = None
#     get_latest_ticks = None
#     kite_ticker = None

# # other internal imports (defensive)
# try:
#     from ..strategy import StrategyEngine
# except Exception:
#     StrategyEngine = None

# try:
#     from ..order_manager import OrderManager
# except Exception:
#     OrderManager = None

# try:
#     from ..indicators import compute_signals
# except Exception:
#     compute_signals = None

# try:
#     from ..crud import get_latest_model, get_latest_sentiment
# except Exception:
#     get_latest_model = None
#     get_latest_sentiment = None

# try:
#     from .. import ml_model
# except Exception:
#     ml_model = None

# try:
#     from ..scheduler import retrain_job
# except Exception:
#     retrain_job = None

# # Payment / wallet routers / broker routes (must expose `router`)
# # we include them via top-level import - keep this safe
# try:
#     from app.api import payment_routes, wallet_routes, broker_routes
# except Exception:
#     payment_routes = wallet_routes = broker_routes = None

# # Admin deps (get_db should return SQLAlchemy Session; require_admin checks admin)
# try:
#     from app.deps import get_db, require_admin  # adjust if naming differs
# except Exception:
#     get_db = require_admin = None

# # Try to import ORM models (optional)
# try:
#     from app.models import User, Subscription, WalletTransaction, CredentialHistory
# except Exception:
#     User = None
#     Subscription = None
#     WalletTransaction = None
#     CredentialHistory = None

# from sqlalchemy.orm import Session
# from sqlalchemy import text

# # Router
# api_router = APIRouter()

# # include optional routers if present (defensive)
# try:
#     if payment_routes is not None and getattr(payment_routes, "router", None):
#         api_router.include_router(payment_routes.router)
# except Exception:
#     log.exception("Failed to include payment_routes")

# try:
#     if wallet_routes is not None and getattr(wallet_routes, "router", None):
#         api_router.include_router(wallet_routes.router)
# except Exception:
#     log.exception("Failed to include wallet_routes")

# try:
#     if broker_routes is not None and getattr(broker_routes, "router", None):
#         api_router.include_router(broker_routes.router)
# except Exception:
#     log.exception("Failed to include broker_routes")

# router = api_router  # export expected by main.py

# # -------------------------
# # Models
# # -------------------------
# class SubscribeRequest(BaseModel):
#     tokens: List[int]


# class PlaceOrderRequest(BaseModel):
#     tradingsymbol: Optional[str] = None
#     instrument_token: Optional[int] = None
#     transaction_type: str
#     quantity: Optional[int] = None
#     amount: Optional[float] = None
#     product: str = "MIS"
#     order_type: str = "MARKET"
#     price: Optional[float] = None
#     exchange: str = "NSE"

# # Log instruments count on import if available
# try:
#     _count = len(getattr(kite_client, "instruments", []) or [])
#     log.info("KiteClient instruments loaded: %d", _count)
# except Exception:
#     log.debug("Could not determine instruments count on startup")


# # -------------------------
# # Basic endpoints
# # -------------------------
# @router.get("/get_zerodha_api_key")
# def get_zerodha_api_key():
#     if not KITE_API_KEY:
#         raise HTTPException(status_code=500, detail="KITE_API_KEY not configured")
#     return {"apiKey": KITE_API_KEY}


# @router.get("/login_url")
# def login_url():
#     redirect = os.getenv("ZERODHA_REDIRECT_URL", "http://localhost:8000/api/auth_callback")
#     url = f"https://kite.zerodha.com/connect/login?v=3&api_key={KITE_API_KEY}&redirect_url={redirect}"
#     return {"login_url": url}


# @router.get("/login_status")
# def login_status():
#     token_present = bool(getattr(kite_client, "access_token", None))
#     return {"kite_loaded": token_present, "access_token_present": token_present}


# # -------------------------
# # Auth callback
# # -------------------------
# @router.get("/auth_callback")
# async def auth_callback(request: Request):
#     request_token = request.query_params.get("request_token")
#     if not request_token:
#         raise HTTPException(status_code=400, detail="request_token missing")

#     if getattr(kite_client, "access_token", None):
#         frontend_url = os.getenv("FRONTEND_REDIRECT_AFTER_LOGIN", "http://localhost:5173/dashboard?login=success")
#         return RedirectResponse(url=frontend_url)

#     try:
#         data = kite_client.kite.generate_session(request_token, KITE_API_SECRET)
#         kite_client.save_token(data)
#         try:
#             if start_websocket:
#                 start_websocket(kite_client.kite.api_key, kite_client.access_token)
#         except Exception:
#             log.exception("Failed to start websocket after auth callback")
#         frontend_url = os.getenv("FRONTEND_REDIRECT_AFTER_LOGIN", "http://localhost:5173/dashboard?login=success")
#         return RedirectResponse(url=frontend_url)
#     except Exception as e:
#         log.exception("auth_callback exchange failed")
#         raise HTTPException(status_code=500, detail=str(e))


# # -------------------------
# # Subscribe ticker (mounted at /api/streamer/subscribe)
# # -------------------------
# @router.post("/streamer/subscribe")
# async def api_subscribe(payload: SubscribeRequest):
#     tokens = payload.tokens or []
#     if not tokens:
#         raise HTTPException(status_code=400, detail="No tokens provided")
#     if streamer_subscribe is None:
#         raise HTTPException(status_code=500, detail="Streamer backend not available")
#     try:
#         streamer_subscribe(tokens)
#     except Exception as e:
#         log.exception("streamer.subscribe failed: %s", e)
#         raise HTTPException(status_code=500, detail="Subscription failed")
#     return {"subscribed": tokens}


# # -------------------------
# # Strategy / Signals / Mode
# # -------------------------
# @router.get("/signals/{token}")
# def get_signals(token: int):
#     if compute_signals is None:
#         raise HTTPException(status_code=500, detail="Signals compute not available")
#     sig = compute_signals(token)
#     om = OrderManager.instance() if OrderManager else None
#     last_reg = om.get_signals().get(token) if (om and hasattr(om, "get_signals")) else None
#     return {"signals": sig, "last_registered": last_reg}


# @router.get("/last_signals")
# def last_signals():
#     om = OrderManager.instance() if OrderManager else None
#     return om.get_signals() if om and hasattr(om, "get_signals") else {}


# @router.get("/mode")
# def get_mode():
#     if StrategyEngine is None:
#         raise HTTPException(status_code=500, detail="Strategy engine not available")
#     return {"mode": StrategyEngine.instance().mode}


# @router.post("/mode")
# def set_mode(payload: Dict[str, Any]):
#     mode = payload.get("mode")
#     if mode not in ("manual", "auto"):
#         raise HTTPException(status_code=400, detail="mode must be 'manual' or 'auto'")
#     if StrategyEngine is None:
#         raise HTTPException(status_code=500, detail="Strategy engine not available")
#     StrategyEngine.instance().set_mode(mode)
#     log.info("Trading mode changed to: %s", mode.upper())
#     return {"mode": mode, "status": "updated"}


# # -------------------------
# # Models metadata listing
# # -------------------------
# @router.get("/models")
# def list_models():
#     files = sorted([f.name for f in STORAGE_DIR.iterdir() if f.suffix == ".pkl"], reverse=True)
#     return {"models": files}


# @router.get("/models/latest")
# def latest_model_meta():
#     m = get_latest_model() if get_latest_model else None
#     if not m:
#         raise HTTPException(status_code=404, detail="No model found")
#     return {
#         "filename": getattr(m, "filename", None),
#         "created_at": getattr(m, "created_at", None).isoformat() if getattr(m, "created_at", None) else None,
#         "rows": getattr(m, "rows", None),
#         "metrics": getattr(m, "metrics", None),
#         "active": getattr(m, "active", None),
#     }


# @router.post("/models/activate")
# def activate_model(payload: Dict[str, Any]):
#     fn = payload.get("filename")
#     latest = payload.get("latest", False)
#     if latest or not fn:
#         if hasattr(ml_model, "load_latest"):
#             m = ml_model.load_latest()
#             return {"status": "ok", "loaded": getattr(ml_model, "model_path", None)}
#         else:
#             raise HTTPException(status_code=500, detail="ML loader not available")
#     candidate = (STORAGE_DIR / fn).resolve()
#     if hasattr(ml_model, "load"):
#         ml_model.load(str(candidate))
#         return {"status": "ok", "loaded": getattr(ml_model, "model_path", None)}
#     raise HTTPException(status_code=500, detail="ML loader not available")


# @router.post("/retrain_manual")
# def retrain_manual(background_tasks: BackgroundTasks):
#     if retrain_job is None:
#         raise HTTPException(status_code=500, detail="Retrain job not available")
#     background_tasks.add_task(retrain_job)
#     return {"status": "retrain started"}


# # -------------------------
# # Sentiment
# # -------------------------
# @router.get("/sentiment/{ticker}")
# def get_sentiment(ticker: str):
#     if get_latest_sentiment is None:
#         raise HTTPException(status_code=500, detail="Sentiment backend not available")
#     s = get_latest_sentiment(ticker)
#     if not s:
#         raise HTTPException(status_code=404, detail="no sentiment found")
#     return {"ticker": s.ticker, "score": s.score, "fetched_at": s.fetched_at.isoformat()}


# # -------------------------
# # Candles (historical endpoint used by frontend)
# # -------------------------
# @router.get("/candles")
# def get_candles(symbol: str = Query(..., description="tradingsymbol or instrument token"),
#                 interval: str = Query("1minute", description="interval like 1minute, 5minute, day"),
#                 limit: int = Query(500, ge=1, le=2000)):
#     try:
#         instrument_token = None
#         try:
#             if str(symbol).isdigit():
#                 instrument_token = int(symbol)
#             else:
#                 if kite_client is not None:
#                     instrument_token = kite_client.get_instrument_token(symbol)
#         except Exception:
#             instrument_token = None

#         candles = []
#         if instrument_token and getattr(kite_client, "kite", None):
#             try:
#                 kite_interval = interval
#                 if interval in ("1m", "1minute", "minute"):
#                     kite_interval = "minute"
#                 elif interval in ("5m", "5minute"):
#                     kite_interval = "5minute"
#                 elif interval in ("day", "1d"):
#                     kite_interval = "day"
#                 candles = kite_client.kite.historical_data(instrument_token, datetime.utcnow() - timedelta(days=7), datetime.utcnow(), interval=kite_interval) or []
#                 log.info("Fetched %d historical candles for %s", len(candles), symbol)
#             except Exception as e:
#                 log.warning("Failed to fetch kite historical for %s: %s", symbol, e)
#                 candles = []

#         if not candles:
#             now = datetime.utcnow()
#             size = min(limit, 500)
#             times = [now - timedelta(minutes=1 * i) for i in range(size)][::-1]
#             vals = (np.cumsum(np.random.randn(size)) + 1000).tolist()
#             candles = []
#             for dt, v in zip(times, vals):
#                 o = v + np.random.rand() * 2 - 1
#                 h = max(v, o) + np.random.rand() * 1.5
#                 l = min(v, o) - np.random.rand() * 1.5
#                 c = v + np.random.rand() * 2 - 1
#                 candles.append({"date": dt, "open": o, "high": h, "low": l, "close": c, "volume": float(np.random.randint(1, 1000))})

#         out = []
#         for c in candles[-limit:]:
#             dt = None
#             if isinstance(c.get("date"), (str, datetime)):
#                 dt = pd.to_datetime(c.get("date"))
#             elif "timestamp" in c:
#                 try:
#                     ts = int(c.get("timestamp"))
#                     dt = datetime.utcfromtimestamp(ts // 1000) if ts > 1_000_000_000_000 else datetime.utcfromtimestamp(ts)
#                 except Exception:
#                     dt = None
#             if dt is None:
#                 dt = datetime.utcnow()

#             t_ms = int(dt.timestamp() * 1000)
#             o = float(c.get("open") or c.get("o") or c.get("open_price") or 0)
#             h = float(c.get("high") or c.get("h") or c.get("high_price") or o)
#             l = float(c.get("low") or c.get("l") or c.get("low_price") or o)
#             cc = float(c.get("close") or c.get("c") or c.get("close_price") or o)
#             v = float(c.get("volume") or c.get("v") or c.get("vol") or 0)
#             out.append({"t": t_ms, "o": o, "h": h, "l": l, "c": cc, "v": v})

#         return {"ok": True, "candles": out}
#     except Exception as e:
#         log.exception("get_candles failed")
#         raise HTTPException(status_code=500, detail=str(e))


# # -------------------------
# # Indicators
# # -------------------------
# @router.get("/indicators")
# def indicators_for_symbol(symbol: str = Query(..., description="tradingsymbol or instrument token")):
#     try:
#         from_date = datetime.now() - timedelta(days=3)
#         to_date = datetime.now()
#         instrument_token = None

#         try:
#             if kite_client is not None:
#                 instrument_token = kite_client.get_instrument_token(symbol)
#                 log.debug("Resolved instrument_token for %s -> %s", symbol, instrument_token)
#         except Exception:
#             log.warning("Could not resolve instrument token for %s (will try as symbol).", symbol)

#         candles = []
#         if instrument_token and getattr(kite_client, "kite", None):
#             try:
#                 candles = kite_client.kite.historical_data(instrument_token, from_date, to_date, interval="5minute") or []
#                 log.info("Fetched %d historical candles for %s", len(candles), symbol)
#             except Exception as e:
#                 log.warning("Failed to fetch historical data for %s: %s", symbol, e)

#         if not candles:
#             now = datetime.now()
#             timestamps = [now - timedelta(minutes=5 * i) for i in range(100)][::-1]
#             close_prices = np.cumsum(np.random.randn(100)) + 2500
#             df = pd.DataFrame({"date": timestamps, "close": close_prices})
#         else:
#             df = pd.DataFrame(candles)
#             if "date" in df.columns:
#                 df["date"] = pd.to_datetime(df["date"])
#             elif "timestamp" in df.columns:
#                 df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
#             elif "tradetime" in df.columns:
#                 df["date"] = pd.to_datetime(df["tradetime"], unit="ms")
#             else:
#                 df["date"] = pd.date_range(end=datetime.now(), periods=len(df), freq="5T")

#             if "close" not in df.columns and "close_price" in df.columns:
#                 df["close"] = df["close_price"]

#         df = df.reset_index(drop=True)
#         df["sma"] = df["close"].rolling(window=14, min_periods=1).mean()
#         df["ema"] = df["close"].ewm(span=14, adjust=False).mean()
#         delta = df["close"].diff()
#         gain = delta.where(delta > 0, 0)
#         loss = -delta.where(delta < 0, 0)
#         avg_gain = gain.rolling(window=14, min_periods=1).mean()
#         avg_loss = loss.rolling(window=14, min_periods=1).mean()
#         rs = avg_gain / avg_loss.replace(0, np.nan)
#         df["rsi"] = 100 - (100 / (1 + rs.fillna(0)))
#         short_ema = df["close"].ewm(span=12, adjust=False).mean()
#         long_ema = df["close"].ewm(span=26, adjust=False).mean()
#         df["macd"] = short_ema - long_ema
#         df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

#         data = {
#             "sma": [{"time": int(row.date.timestamp()), "value": float(row.sma)} for _, row in df.iterrows() if not np.isnan(row.sma)],
#             "ema": [{"time": int(row.date.timestamp()), "value": float(row.ema)} for _, row in df.iterrows() if not np.isnan(row.ema)],
#             "rsi": [{"time": int(row.date.timestamp()), "value": float(row.rsi)} for _, row in df.iterrows() if not np.isnan(row.rsi)],
#             "macd": [{"time": int(row.date.timestamp()), "macd": float(row.macd), "signal": float(row.macd_signal)} for _, row in df.iterrows() if not np.isnan(row.macd)],
#         }

#         return {"ok": True, "data": data}
#     except Exception as e:
#         log.exception("indicators compute failed")
#         raise HTTPException(status_code=500, detail=f"indicators compute failed: {e}")


# # -------------------------
# # Predict (ML)
# # -------------------------
# @router.get("/predict/{ticker}")
# def predict_ticker(ticker: str):
#     try:
#         if not hasattr(ml_model, "predict"):
#             raise HTTPException(status_code=404, detail="ML model predict function not available")
#         pred = ml_model.predict(ticker)
#         return {"ok": True, "prediction": pred}
#     except HTTPException:
#         raise
#     except Exception as e:
#         log.exception("predict failed")
#         raise HTTPException(status_code=500, detail=f"predict failed: {e}")


# # -------------------------
# # Order Execution
# # -------------------------
# @router.post("/order/manual")
# def place_order_api(payload: PlaceOrderRequest):
#     try:
#         quantity_to_place = payload.quantity or 1
#         if not payload.tradingsymbol:
#             raise HTTPException(status_code=400, detail="tradingsymbol required")

#         params = dict(
#             variety="regular",
#             exchange=payload.exchange,
#             tradingsymbol=payload.tradingsymbol,
#             transaction_type=payload.transaction_type,
#             quantity=int(quantity_to_place),
#             product=payload.product,
#             order_type=payload.order_type,
#         )
#         if payload.price is not None:
#             params["price"] = float(payload.price)

#         if kite_client is None:
#             raise HTTPException(status_code=500, detail="Broker client not available")

#         res = kite_client.place_order(**params)
#         return {"status": "success", "order_response": res}
#     except HTTPException:
#         raise
#     except Exception as e:
#         log.exception("Place order failed")
#         raise HTTPException(status_code=500, detail=f"Place order failed: {e}")


# @router.post("/place-order")
# def place_order_frontend(payload: PlaceOrderRequest):
#     return place_order_api(payload)


# # -------------------------
# # Positions / Holdings
# # -------------------------
# @router.get("/orders")
# def list_orders():
#     try:
#         if kite_client is None:
#             raise HTTPException(status_code=500, detail="Broker client not available")
#         return kite_client.orders()
#     except Exception as e:
#         log.exception("Failed to list orders")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/positions")
# def positions():
#     try:
#         if kite_client is None:
#             raise HTTPException(status_code=500, detail="Broker client not available")
#         return kite_client.positions()
#     except Exception as e:
#         log.exception("Failed to fetch positions")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/holdings")
# def holdings():
#     try:
#         if kite_client is None:
#             raise HTTPException(status_code=500, detail="Broker client not available")
#         return kite_client.holdings()
#     except Exception as e:
#         log.exception("Failed to fetch holdings")
#         raise HTTPException(status_code=500, detail=str(e))


# # -------------------------
# # Session info
# # -------------------------
# @router.get("/session-info")
# async def session_info(symbol: str):
#     try:
#         token_data = getattr(kite_client, "session_data", None) or {}
#         access_token = token_data.get("access_token") or getattr(kite_client, "access_token", None)
#         if not access_token:
#             log.warning("session-info: access token missing")
#             raise HTTPException(status_code=401, detail="Access token not found. Please login again.")

#         instrument_token = None
#         try:
#             if kite_client is not None:
#                 instrument_token = kite_client.get_instrument_token(symbol)
#         except Exception as e:
#             log.warning("session-info: could not resolve instrument token for %s: %s", symbol, e)
#             return {"apiKey": KITE_API_KEY, "accessToken": access_token, "instrumentToken": None, "initialCandles": []}

#         return {"apiKey": KITE_API_KEY, "accessToken": access_token, "instrumentToken": instrument_token, "initialCandles": []}
#     except HTTPException:
#         raise
#     except Exception as e:
#         log.exception("Session-info failed")
#         raise HTTPException(status_code=500, detail=str(e))


# # -------------------------
# # Health / config
# # -------------------------
# @router.get("/health")
# def health():
#     return {"status": "ok"}


# @router.get("/config")
# def config():
#     loaded = getattr(ml_model, "model", None) is not None
#     return {
#         "kite_loaded": bool(getattr(kite_client, "access_token", None)),
#         "model_loaded": loaded,
#         "model_path": getattr(ml_model, "model_path", None),
#         "storage_dir": str(STORAGE_DIR),
#     }


# # -------------------------
# # Kite socket status
# # -------------------------
# @router.get("/kite/status")
# def kite_status():
#     try:
#         if kite_ticker and getattr(kite_ticker, "is_connected", None) and kite_ticker.is_connected():
#             return {"connected": True, "message": "Kite WebSocket active"}
#         else:
#             return {"connected": False, "message": "Kite WebSocket not connected"}
#     except Exception as e:
#         log.exception("kite status check failed")
#         return {"connected": False, "error": str(e)}


# # -------------------------
# # Notifications / market prediction endpoints
# # -------------------------
# @router.get("/notifications/latest")
# def notifications_latest(limit: int = 10, symbol: Optional[str] = None):
#     om = OrderManager.instance() if OrderManager else None
#     signals = om.get_signals() if (om and hasattr(om, "get_signals")) else {}

#     ml_last = None
#     try:
#         ml_last = getattr(ml_model, "last_prediction", None)
#     except Exception:
#         ml_last = None

#     sentiment = None
#     if symbol:
#         try:
#             if get_latest_sentiment:
#                 s = get_latest_sentiment(symbol)
#                 if s:
#                     sentiment = {"ticker": s.ticker, "score": s.score, "fetched_at": s.fetched_at.isoformat()}
#         except Exception:
#             sentiment = None

#     recent_signals = {}
#     try:
#         items = []
#         for k, v in signals.items():
#             ts = v.get("ts") if isinstance(v, dict) else None
#             items.append((k, v, ts))
#         items_sorted = sorted(items, key=lambda x: x[2] or "", reverse=True)
#         for k, v, _ in items_sorted[:limit]:
#             recent_signals[k] = v
#     except Exception:
#         recent_signals = signals

#     return {"ok": True, "signals": recent_signals, "ml_last": ml_last, "sentiment": sentiment}


# @router.get("/market-prediction/latest")
# def market_prediction_latest():
#     try:
#         last = getattr(ml_model, "last_prediction", None)
#         if not last:
#             return {"ok": False, "message": "No prediction available yet"}
#         return {"ok": True, "prediction": last}
#     except Exception as e:
#         log.exception("market_prediction_latest failed")
#         raise HTTPException(status_code=500, detail=f"market_prediction_latest failed: {e}")


# @router.get("/latest-signal")
# def latest_signal():
#     try:
#         ml_last = None
#         try:
#             ml_last = getattr(ml_model, "last_prediction", None)
#         except Exception:
#             ml_last = None

#         om = OrderManager.instance() if OrderManager else None
#         signals = om.get_signals() if (om and hasattr(om, "get_signals")) else {}

#         return {"ok": True, "ml_last": ml_last, "signals": signals}
#     except Exception as e:
#         log.exception("latest_signal failed")
#         raise HTTPException(status_code=500, detail=f"latest_signal failed: {e}")

# # End of file








# app/api/routes.py
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Query, Depends
from fastapi.responses import RedirectResponse
from pathlib import Path
import logging
import os
import asyncio
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

log = logging.getLogger(__name__)
log.setLevel(os.getenv("LOG_LEVEL", "INFO"))

# storage dir
STORAGE_DIR = Path("app") / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# try to import kite_client and helpers defensively
try:
    from ..kite_client import kite_client
except Exception:
    kite_client = None

try:
    from ..config import KITE_API_KEY, KITE_API_SECRET
except Exception:
    KITE_API_KEY = None
    KITE_API_SECRET = None

# streamer helpers (subscribe, start_websocket, get_latest_ticks, kite_ticker)
try:
    from ..streamer import subscribe as streamer_subscribe, start_websocket, get_latest_ticks, kite_ticker
except Exception:
    streamer_subscribe = None
    start_websocket = None
    get_latest_ticks = None
    kite_ticker = None

# other internal imports (defensive)
try:
    from ..strategy import StrategyEngine
except Exception:
    StrategyEngine = None

try:
    from ..order_manager import OrderManager
except Exception:
    OrderManager = None

try:
    from ..indicators import compute_signals
except Exception:
    compute_signals = None

try:
    from ..crud import get_latest_model, get_latest_sentiment
except Exception:
    get_latest_model = None
    get_latest_sentiment = None

try:
    from .. import ml_model
except Exception:
    ml_model = None

try:
    from ..scheduler import retrain_job
except Exception:
    retrain_job = None

# Payment / wallet routers / broker routes (must expose `router`)
# we include them via top-level import - keep this safe
try:
    from app.api import payment_routes, wallet_routes, broker_routes
except Exception:
    payment_routes = wallet_routes = broker_routes = None

# Admin deps (get_db should return SQLAlchemy Session; require_admin checks admin)
try:
    from app.deps import get_db, require_admin  # adjust if naming differs
except Exception:
    get_db = require_admin = None

# Try to import ORM models (optional)
try:
    from app.models import User, Subscription, WalletTransaction, CredentialHistory
except Exception:
    User = None
    Subscription = None
    WalletTransaction = None
    CredentialHistory = None

from sqlalchemy.orm import Session
from sqlalchemy import text

# Router
api_router = APIRouter()

# include optional routers if present (defensive)
try:
    if payment_routes is not None and getattr(payment_routes, "router", None):
        api_router.include_router(payment_routes.router)
except Exception:
    log.exception("Failed to include payment_routes")

try:
    if wallet_routes is not None and getattr(wallet_routes, "router", None):
        api_router.include_router(wallet_routes.router)
except Exception:
    log.exception("Failed to include wallet_routes")

try:
    if broker_routes is not None and getattr(broker_routes, "router", None):
        api_router.include_router(broker_routes.router)
except Exception:
    log.exception("Failed to include broker_routes")

router = api_router  # export expected by main.py

# -------------------------
# Models
# -------------------------
class SubscribeRequest(BaseModel):
    tokens: List[int]


class PlaceOrderRequest(BaseModel):
    tradingsymbol: Optional[str] = None
    instrument_token: Optional[int] = None
    transaction_type: str
    quantity: Optional[int] = None
    amount: Optional[float] = None
    product: str = "MIS"
    order_type: str = "MARKET"
    price: Optional[float] = None
    exchange: str = "NSE"

# Log instruments count on import if available
try:
    _count = len(getattr(kite_client, "instruments", []) or [])
    log.info("KiteClient instruments loaded: %d", _count)
except Exception:
    log.debug("Could not determine instruments count on startup")


# -------------------------
# Basic endpoints
# -------------------------
@router.get("/get_zerodha_api_key")
def get_zerodha_api_key():
    if not KITE_API_KEY:
        raise HTTPException(status_code=500, detail="KITE_API_KEY not configured")
    return {"apiKey": KITE_API_KEY}


@router.get("/login_url")
def login_url():
    redirect = os.getenv("ZERODHA_REDIRECT_URL", "http://localhost:8000/api/auth_callback")
    url = f"https://kite.zerodha.com/connect/login?v=3&api_key={KITE_API_KEY}&redirect_url={redirect}"
    return {"login_url": url}


@router.get("/login_status")
def login_status():
    token_present = bool(getattr(kite_client, "access_token", None))
    return {"kite_loaded": token_present, "access_token_present": token_present}


# -------------------------
# Auth callback
# -------------------------
@router.get("/auth_callback")
async def auth_callback(request: Request):
    request_token = request.query_params.get("request_token")
    if not request_token:
        raise HTTPException(status_code=400, detail="request_token missing")

    if getattr(kite_client, "access_token", None):
        frontend_url = os.getenv("FRONTEND_REDIRECT_AFTER_LOGIN", "http://localhost:5173/dashboard?login=success")
        return RedirectResponse(url=frontend_url)

    try:
        data = kite_client.kite.generate_session(request_token, KITE_API_SECRET)
        kite_client.save_token(data)
        try:
            if start_websocket:
                start_websocket(kite_client.kite.api_key, kite_client.access_token)
        except Exception:
            log.exception("Failed to start websocket after auth callback")
        frontend_url = os.getenv("FRONTEND_REDIRECT_AFTER_LOGIN", "http://localhost:5173/dashboard?login=success")
        return RedirectResponse(url=frontend_url)
    except Exception as e:
        log.exception("auth_callback exchange failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------
# Subscribe ticker (mounted at /api/streamer/subscribe)
# -------------------------
@router.post("/streamer/subscribe")
async def api_subscribe(payload: SubscribeRequest):
    tokens = payload.tokens or []
    if not tokens:
        raise HTTPException(status_code=400, detail="No tokens provided")
    if streamer_subscribe is None:
        raise HTTPException(status_code=500, detail="Streamer backend not available")
    try:
        streamer_subscribe(tokens)
    except Exception as e:
        log.exception("streamer.subscribe failed: %s", e)
        raise HTTPException(status_code=500, detail="Subscription failed")
    return {"subscribed": tokens}


# -------------------------
# Strategy / Signals / Mode
# -------------------------
@router.get("/signals/{token}")
def get_signals(token: int):
    if compute_signals is None:
        raise HTTPException(status_code=500, detail="Signals compute not available")
    sig = compute_signals(token)
    om = OrderManager.instance() if OrderManager else None
    last_reg = om.get_signals().get(token) if (om and hasattr(om, "get_signals")) else None
    return {"signals": sig, "last_registered": last_reg}


@router.get("/last_signals")
def last_signals():
    om = OrderManager.instance() if OrderManager else None
    return om.get_signals() if om and hasattr(om, "get_signals") else {}


def _ensure_strategy_engine():
    """
    Try to dynamically import StrategyEngine if module-level import failed earlier.
    Returns StrategyEngine class/object or None.
    """
    global StrategyEngine
    if StrategyEngine is not None:
        return StrategyEngine
    try:
        # attempt to import lazily
        from app.strategy import StrategyEngine as _SE
        StrategyEngine = _SE
        log.info("Dynamically loaded StrategyEngine")
        return StrategyEngine
    except Exception as e:
        log.debug("Dynamic import of StrategyEngine failed: %s", e)
        StrategyEngine = None
        return None


@router.get("/mode")
def get_mode():
    SE = _ensure_strategy_engine()
    if SE is None:
        # fallback: return a safe default rather than always throwing 500,
        # but still indicate it's not controlled by strategy engine
        log.warning("/api/mode requested but StrategyEngine not available")
        return {"mode": "manual", "note": "strategy engine not available (fallback)"}
    try:
        return {"mode": SE.instance().mode}
    except Exception as e:
        log.exception("Failed to get StrategyEngine.mode: %s", e)
        raise HTTPException(status_code=500, detail="Failed to read strategy mode")


@router.post("/mode")
def set_mode(payload: Dict[str, Any]):
    mode = payload.get("mode")
    if mode not in ("manual", "auto"):
        raise HTTPException(status_code=400, detail="mode must be 'manual' or 'auto'")
    SE = _ensure_strategy_engine()
    if SE is None:
        raise HTTPException(status_code=500, detail="Strategy engine not available")
    try:
        SE.instance().set_mode(mode)
        log.info("Trading mode changed to: %s", mode.upper())
        return {"mode": mode, "status": "updated"}
    except Exception as e:
        log.exception("Failed to set StrategyEngine.mode: %s", e)
        raise HTTPException(status_code=500, detail="Failed to set strategy mode")


# -------------------------
# Models metadata listing
# -------------------------
@router.get("/models")
def list_models():
    files = sorted([f.name for f in STORAGE_DIR.iterdir() if f.suffix == ".pkl"], reverse=True)
    return {"models": files}


@router.get("/models/latest")
def latest_model_meta():
    m = get_latest_model() if get_latest_model else None
    if not m:
        raise HTTPException(status_code=404, detail="No model found")
    return {
        "filename": getattr(m, "filename", None),
        "created_at": getattr(m, "created_at", None).isoformat() if getattr(m, "created_at", None) else None,
        "rows": getattr(m, "rows", None),
        "metrics": getattr(m, "metrics", None),
        "active": getattr(m, "active", None),
    }


# -------------------------
# Instruments stub (prevents frontend 404)
# -------------------------
@router.get("/instruments")
def instruments_list(q: Optional[str] = None):
    """
    Minimal stub so frontend does not get 404.
    Replace with real DB/ Kite lookups later.
    """
    try:
        # If kite_client provides instruments, try to use it (best-effort)
        if kite_client is not None and getattr(kite_client, "instruments", None):
            try:
                # attempt to filter kite_client.instruments if it's a list of dict-like items
                raw = getattr(kite_client, "instruments") or []
                out = []
                for item in raw:
                    try:
                        # allow both dicts and objects with attributes
                        token = item.get("instrument_token") if isinstance(item, dict) else getattr(item, "instrument_token", None)
                        sym = item.get("tradingsymbol") if isinstance(item, dict) else getattr(item, "tradingsymbol", None)
                        exch = item.get("exchange") if isinstance(item, dict) else getattr(item, "exchange", None)
                        if sym:
                            out.append({"instrument_token": token, "tradingsymbol": sym, "exchange": exch})
                    except Exception:
                        continue
                if q:
                    q_up = q.upper()
                    out = [i for i in out if q_up in (i.get("tradingsymbol") or "").upper()]
                return {"ok": True, "instruments": out}
            except Exception:
                # fallthrough to static stub
                log.debug("kite_client.instruments read failed; falling back to static stub")

        # Example static stub for dev
        out = [
            {"instrument_token": 12345, "tradingsymbol": "RELIANCE", "exchange": "NSE"},
            {"instrument_token": 67890, "tradingsymbol": "TCS", "exchange": "NSE"},
            {"instrument_token": 11111, "tradingsymbol": "INFY", "exchange": "NSE"},
        ]
        if q:
            q_up = q.upper()
            out = [i for i in out if q_up in (i.get("tradingsymbol") or "").upper()]
        return {"ok": True, "instruments": out}
    except Exception as e:
        log.exception("instruments endpoint failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/activate")
def activate_model(payload: Dict[str, Any]):
    fn = payload.get("filename")
    latest = payload.get("latest", False)
    if latest or not fn:
        if hasattr(ml_model, "load_latest"):
            m = ml_model.load_latest()
            return {"status": "ok", "loaded": getattr(ml_model, "model_path", None)}
        else:
            raise HTTPException(status_code=500, detail="ML loader not available")
    candidate = (STORAGE_DIR / fn).resolve()
    if hasattr(ml_model, "load"):
        ml_model.load(str(candidate))
        return {"status": "ok", "loaded": getattr(ml_model, "model_path", None)}
    raise HTTPException(status_code=500, detail="ML loader not available")


@router.post("/retrain_manual")
def retrain_manual(background_tasks: BackgroundTasks):
    if retrain_job is None:
        raise HTTPException(status_code=500, detail="Retrain job not available")
    background_tasks.add_task(retrain_job)
    return {"status": "retrain started"}


# -------------------------
# Sentiment
# -------------------------
@router.get("/sentiment/{ticker}")
def get_sentiment(ticker: str):
    if get_latest_sentiment is None:
        raise HTTPException(status_code=500, detail="Sentiment backend not available")
    s = get_latest_sentiment(ticker)
    if not s:
        raise HTTPException(status_code=404, detail="no sentiment found")
    return {"ticker": s.ticker, "score": s.score, "fetched_at": s.fetched_at.isoformat()}


# -------------------------
# Candles (historical endpoint used by frontend)
# -------------------------
@router.get("/candles")
def get_candles(symbol: str = Query(..., description="tradingsymbol or instrument token"),
                interval: str = Query("1minute", description="interval like 1minute, 5minute, day"),
                limit: int = Query(500, ge=1, le=2000)):
    try:
        instrument_token = None
        try:
            if str(symbol).isdigit():
                instrument_token = int(symbol)
            else:
                if kite_client is not None:
                    instrument_token = kite_client.get_instrument_token(symbol)
        except Exception:
            instrument_token = None

        candles = []
        if instrument_token and getattr(kite_client, "kite", None):
            try:
                kite_interval = interval
                if interval in ("1m", "1minute", "minute"):
                    kite_interval = "minute"
                elif interval in ("5m", "5minute"):
                    kite_interval = "5minute"
                elif interval in ("day", "1d"):
                    kite_interval = "day"
                candles = kite_client.kite.historical_data(instrument_token, datetime.utcnow() - timedelta(days=7), datetime.utcnow(), interval=kite_interval) or []
                log.info("Fetched %d historical candles for %s", len(candles), symbol)
            except Exception as e:
                log.warning("Failed to fetch kite historical for %s: %s", symbol, e)
                candles = []

        if not candles:
            now = datetime.utcnow()
            size = min(limit, 500)
            times = [now - timedelta(minutes=1 * i) for i in range(size)][::-1]
            vals = (np.cumsum(np.random.randn(size)) + 1000).tolist()
            candles = []
            for dt, v in zip(times, vals):
                o = v + np.random.rand() * 2 - 1
                h = max(v, o) + np.random.rand() * 1.5
                l = min(v, o) - np.random.rand() * 1.5
                c = v + np.random.rand() * 2 - 1
                candles.append({"date": dt, "open": o, "high": h, "low": l, "close": c, "volume": float(np.random.randint(1, 1000))})

        out = []
        for c in candles[-limit:]:
            dt = None
            if isinstance(c.get("date"), (str, datetime)):
                dt = pd.to_datetime(c.get("date"))
            elif "timestamp" in c:
                try:
                    ts = int(c.get("timestamp"))
                    dt = datetime.utcfromtimestamp(ts // 1000) if ts > 1_000_000_000_000 else datetime.utcfromtimestamp(ts)
                except Exception:
                    dt = None
            if dt is None:
                dt = datetime.utcnow()

            t_ms = int(dt.timestamp() * 1000)
            o = float(c.get("open") or c.get("o") or c.get("open_price") or 0)
            h = float(c.get("high") or c.get("h") or c.get("high_price") or o)
            l = float(c.get("low") or c.get("l") or c.get("low_price") or o)
            cc = float(c.get("close") or c.get("c") or c.get("close_price") or o)
            v = float(c.get("volume") or c.get("v") or c.get("vol") or 0)
            out.append({"t": t_ms, "o": o, "h": h, "l": l, "c": cc, "v": v})

        return {"ok": True, "candles": out}
    except Exception as e:
        log.exception("get_candles failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------
# Indicators
# -------------------------
@router.get("/indicators")
def indicators_for_symbol(symbol: str = Query(..., description="tradingsymbol or instrument token")):
    try:
        from_date = datetime.now() - timedelta(days=3)
        to_date = datetime.now()
        instrument_token = None

        try:
            if kite_client is not None:
                instrument_token = kite_client.get_instrument_token(symbol)
                log.debug("Resolved instrument_token for %s -> %s", symbol, instrument_token)
        except Exception:
            log.warning("Could not resolve instrument token for %s (will try as symbol).", symbol)

        candles = []
        if instrument_token and getattr(kite_client, "kite", None):
            try:
                candles = kite_client.kite.historical_data(instrument_token, from_date, to_date, interval="5minute") or []
                log.info("Fetched %d historical candles for %s", len(candles), symbol)
            except Exception as e:
                log.warning("Failed to fetch historical data for %s: %s", symbol, e)

        if not candles:
            now = datetime.now()
            timestamps = [now - timedelta(minutes=5 * i) for i in range(100)][::-1]
            close_prices = np.cumsum(np.random.randn(100)) + 2500
            df = pd.DataFrame({"date": timestamps, "close": close_prices})
        else:
            df = pd.DataFrame(candles)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
            elif "timestamp" in df.columns:
                df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
            elif "tradetime" in df.columns:
                df["date"] = pd.to_datetime(df["tradetime"], unit="ms")
            else:
                df["date"] = pd.date_range(end=datetime.now(), periods=len(df), freq="5T")

            if "close" not in df.columns and "close_price" in df.columns:
                df["close"] = df["close_price"]

        df = df.reset_index(drop=True)
        df["sma"] = df["close"].rolling(window=14, min_periods=1).mean()
        df["ema"] = df["close"].ewm(span=14, adjust=False).mean()
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14, min_periods=1).mean()
        avg_loss = loss.rolling(window=14, min_periods=1).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs.fillna(0)))
        short_ema = df["close"].ewm(span=12, adjust=False).mean()
        long_ema = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = short_ema - long_ema
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

        data = {
            "sma": [{"time": int(row.date.timestamp()), "value": float(row.sma)} for _, row in df.iterrows() if not np.isnan(row.sma)],
            "ema": [{"time": int(row.date.timestamp()), "value": float(row.ema)} for _, row in df.iterrows() if not np.isnan(row.ema)],
            "rsi": [{"time": int(row.date.timestamp()), "value": float(row.rsi)} for _, row in df.iterrows() if not np.isnan(row.rsi)],
            "macd": [{"time": int(row.date.timestamp()), "macd": float(row.macd), "signal": float(row.macd_signal)} for _, row in df.iterrows() if not np.isnan(row.macd)],
        }

        return {"ok": True, "data": data}
    except Exception as e:
        log.exception("indicators compute failed")
        raise HTTPException(status_code=500, detail=f"indicators compute failed: {e}")


# -------------------------
# Predict (ML)
# -------------------------
@router.get("/predict/{ticker}")
def predict_ticker(ticker: str):
    try:
        if not hasattr(ml_model, "predict"):
            raise HTTPException(status_code=404, detail="ML model predict function not available")
        pred = ml_model.predict(ticker)
        return {"ok": True, "prediction": pred}
    except HTTPException:
        raise
    except Exception as e:
        log.exception("predict failed")
        raise HTTPException(status_code=500, detail=f"predict failed: {e}")


# -------------------------
# Order Execution
# -------------------------
@router.post("/order/manual")
def place_order_api(payload: PlaceOrderRequest):
    try:
        quantity_to_place = payload.quantity or 1
        if not payload.tradingsymbol:
            raise HTTPException(status_code=400, detail="tradingsymbol required")

        params = dict(
            variety="regular",
            exchange=payload.exchange,
            tradingsymbol=payload.tradingsymbol,
            transaction_type=payload.transaction_type,
            quantity=int(quantity_to_place),
            product=payload.product,
            order_type=payload.order_type,
        )
        if payload.price is not None:
            params["price"] = float(payload.price)

        if kite_client is None:
            raise HTTPException(status_code=500, detail="Broker client not available")

        res = kite_client.place_order(**params)
        return {"status": "success", "order_response": res}
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Place order failed")
        raise HTTPException(status_code=500, detail=f"Place order failed: {e}")


@router.post("/place-order")
def place_order_frontend(payload: PlaceOrderRequest):
    return place_order_api(payload)


# -------------------------
# Positions / Holdings
# -------------------------
@router.get("/orders")
def list_orders():
    try:
        if kite_client is None:
            raise HTTPException(status_code=500, detail="Broker client not available")
        return kite_client.orders()
    except Exception as e:
        log.exception("Failed to list orders")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
def positions():
    try:
        if kite_client is None:
            raise HTTPException(status_code=500, detail="Broker client not available")
        return kite_client.positions()
    except Exception as e:
        log.exception("Failed to fetch positions")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/holdings")
def holdings():
    try:
        if kite_client is None:
            raise HTTPException(status_code=500, detail="Broker client not available")
        return kite_client.holdings()
    except Exception as e:
        log.exception("Failed to fetch holdings")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------
# Session info
# -------------------------
@router.get("/session-info")
async def session_info(symbol: str):
    try:
        token_data = getattr(kite_client, "session_data", None) or {}
        access_token = token_data.get("access_token") or getattr(kite_client, "access_token", None)
        if not access_token:
            log.warning("session-info: access token missing")
            raise HTTPException(status_code=401, detail="Access token not found. Please login again.")

        instrument_token = None
        try:
            if kite_client is not None:
                instrument_token = kite_client.get_instrument_token(symbol)
        except Exception as e:
            log.warning("session-info: could not resolve instrument token for %s: %s", symbol, e)
            return {"apiKey": KITE_API_KEY, "accessToken": access_token, "instrumentToken": None, "initialCandles": []}

        return {"apiKey": KITE_API_KEY, "accessToken": access_token, "instrumentToken": instrument_token, "initialCandles": []}
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Session-info failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------
# Health / config
# -------------------------
@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/config")
def config():
    loaded = getattr(ml_model, "model", None) is not None
    return {
        "kite_loaded": bool(getattr(kite_client, "access_token", None)),
        "model_loaded": loaded,
        "model_path": getattr(ml_model, "model_path", None),
        "storage_dir": str(STORAGE_DIR),
    }


# -------------------------
# Kite socket status
# -------------------------
@router.get("/kite/status")
def kite_status():
    try:
        if kite_ticker and getattr(kite_ticker, "is_connected", None) and kite_ticker.is_connected():
            return {"connected": True, "message": "Kite WebSocket active"}
        else:
            return {"connected": False, "message": "Kite WebSocket not connected"}
    except Exception as e:
        log.exception("kite status check failed")
        return {"connected": False, "error": str(e)}


# -------------------------
# Notifications / market prediction endpoints
# -------------------------
@router.get("/notifications/latest")
def notifications_latest(limit: int = 10, symbol: Optional[str] = None):
    om = OrderManager.instance() if OrderManager else None
    signals = om.get_signals() if (om and hasattr(om, "get_signals")) else {}

    ml_last = None
    try:
        ml_last = getattr(ml_model, "last_prediction", None)
    except Exception:
        ml_last = None

    sentiment = None
    if symbol:
        try:
            if get_latest_sentiment:
                s = get_latest_sentiment(symbol)
                if s:
                    sentiment = {"ticker": s.ticker, "score": s.score, "fetched_at": s.fetched_at.isoformat()}
        except Exception:
            sentiment = None

    recent_signals = {}
    try:
        items = []
        for k, v in signals.items():
            ts = v.get("ts") if isinstance(v, dict) else None
            items.append((k, v, ts))
        items_sorted = sorted(items, key=lambda x: x[2] or "", reverse=True)
        for k, v, _ in items_sorted[:limit]:
            recent_signals[k] = v
    except Exception:
        recent_signals = signals

    return {"ok": True, "signals": recent_signals, "ml_last": ml_last, "sentiment": sentiment}


@router.get("/market-prediction/latest")
def market_prediction_latest():
    try:
        last = getattr(ml_model, "last_prediction", None)
        if not last:
            return {"ok": False, "message": "No prediction available yet"}
        return {"ok": True, "prediction": last}
    except Exception as e:
        log.exception("market_prediction_latest failed")
        raise HTTPException(status_code=500, detail=f"market_prediction_latest failed: {e}")


@router.get("/latest-signal")
def latest_signal():
    try:
        ml_last = None
        try:
            ml_last = getattr(ml_model, "last_prediction", None)
        except Exception:
            ml_last = None

        om = OrderManager.instance() if OrderManager else None
        signals = om.get_signals() if (om and hasattr(om, "get_signals")) else {}

        return {"ok": True, "ml_last": ml_last, "signals": signals}
    except Exception as e:
        log.exception("latest_signal failed")
        raise HTTPException(status_code=500, detail=f"latest_signal failed: {e}")

# End of file
