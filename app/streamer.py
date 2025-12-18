


# app/streamer.py
"""
Robust streamer: Kite Ticker -> FastAPI WebSocket clients

Notes:
- Call set_event_loop(asyncio.get_event_loop()) from FastAPI startup BEFORE starting the kite websocket.
- Use start_websocket(api_key, access_token) to initialize connection.
- Use stop_websocket() on shutdown (main should await the shutdown coroutine if needed).
- This module keeps thread-safe structures and schedules sends on FastAPI loop via run_coroutine_threadsafe.
"""

import json
import logging
import time
import asyncio
from typing import List, Dict, Any, Optional
from threading import Lock

# kiteconnect import (external dependency)
try:
    from kiteconnect import KiteTicker  # type: ignore
except Exception:
    KiteTicker = None  # allow import on dev machines without kiteconnect

# FastAPI WebSocket type for typing only
try:
    from fastapi import WebSocket
    from starlette.websockets import WebSocketDisconnect
except Exception:
    WebSocket = Any  # fallback for static checkers if fastapi not available
    WebSocketDisconnect = Exception

logger = logging.getLogger("app.streamer")

# -------------------------
# Module state
# -------------------------
kite_ticker: Optional["KiteTicker"] = None
_connected = False

# thread-safe shared state
_subscribed_tokens: List[int] = []
_lock = Lock()
_latest_ticks: Dict[int, Dict[str, Any]] = {}  # token -> latest tick dict

# candle buffers per token
_candle_buffers: Dict[int, List[Dict[str, Any]]] = {}
# current building candle per token
_current_candle: Dict[int, Dict[str, Any]] = {}

# frontend WebSocket clients (these are starlette fastapi WebSocket objects;
# we schedule send_text on the FastAPI loop using run_coroutine_threadsafe)
frontend_clients: List["WebSocket"] = []
frontend_lock = Lock()

# candle aggregation params (seconds)
CANDLE_INTERVAL_SECONDS = 60  # 1-minute buckets by default
CANDLE_HISTORY_LENGTH = 240  # keep last N candles per token

# reference to FastAPI event loop for scheduling coroutine calls from Kite thread
_app_event_loop: Optional["asyncio.AbstractEventLoop"] = None

# -------------------------
# Public helpers (lifecycle)
# -------------------------
def set_event_loop(loop: "asyncio.AbstractEventLoop"):
    """
    Must be called at FastAPI startup with the running loop:
        import asyncio
        from app.streamer import set_event_loop
        set_event_loop(asyncio.get_event_loop())
    """
    global _app_event_loop
    _app_event_loop = loop
    logger.info("Streamer: event loop set for thread->async scheduling")

async def _async_remove_frontend(ws: "WebSocket"):
    """
    Remove a websocket from clients list from the event loop (safe).
    """
    remove_frontend_client(ws)

def is_connected() -> bool:
    return bool(kite_ticker and _connected)

# -------------------------
# Internal send helpers
# -------------------------
def _on_send_done(fut, ws):
    """
    Callback for completed run_coroutine_threadsafe futures.
    If exception found, remove client.
    """
    try:
        fut.result()
    except Exception as e:
        # Could be WebSocketDisconnect or connection reset; remove client
        try:
            logger.debug("Send to client failed; removing client. err=%s", e)
            remove_frontend_client(ws)
        except Exception:
            logger.exception("Failed to remove failing client")

def _schedule_send_text(ws: "WebSocket", text: str):
    """
    Schedule ws.send_text on the provided FastAPI event loop.
    Called from non-async threads (KiteTicker callbacks).
    Uses run_coroutine_threadsafe and attaches a done callback.
    """
    global _app_event_loop
    if not _app_event_loop:
        # fallback: try best-effort non-loop scheduling (rare)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(ws.send_text(text))
                return
        except Exception:
            pass
        logger.debug("No event loop set; skipping send")
        return

    try:
        fut = asyncio.run_coroutine_threadsafe(ws.send_text(text), _app_event_loop)
        fut.add_done_callback(lambda f: _on_send_done(f, ws))
    except Exception as e:
        logger.exception("run_coroutine_threadsafe failed when scheduling ws.send_text: %s", e)
        # best-effort removal if scheduling failed
        try:
            remove_frontend_client(ws)
        except Exception:
            pass

def _safe_send_to_frontends(payload: Dict[str, Any]):
    """
    Broadcast JSON payload to all connected frontend WebSocket clients.
    Safe to call from KiteTicker thread. Uses scheduling helper to send on proper loop.
    """
    text = json.dumps(payload, default=str)
    with frontend_lock:
        clients = list(frontend_clients)
    if not clients:
        logger.debug("No frontend clients to broadcast payload.")
        return

    logger.debug("Broadcasting payload to %d clients: token=%s time=%s", len(clients), payload.get("token"), payload.get("tick", {}).get("timestamp"))
    for ws in clients:
        try:
            _schedule_send_text(ws, text)
        except Exception as e:
            logger.warning("Failed to schedule send to a client: %s", e)
            try:
                remove_frontend_client(ws)
            except Exception:
                pass

# -------------------------
# Candle helpers
# -------------------------
def _bucket_for_timestamp(ts: int) -> int:
    return ts - (ts % CANDLE_INTERVAL_SECONDS)

def _ingest_tick_into_candle(token: int, price: float, ts_seconds: int):
    bucket = _bucket_for_timestamp(ts_seconds)
    current = _current_candle.get(token)
    if current is None or current.get("bucket") != bucket:
        # finalize previous candle
        if current:
            buf = _candle_buffers.setdefault(token, [])
            c = {
                "time": int(current["bucket"]),
                "open": float(current["open"]),
                "high": float(current["high"]),
                "low": float(current["low"]),
                "close": float(current["close"]),
                "volume": float(current.get("volume", 0)),
            }
            buf.append(c)
            if len(buf) > CANDLE_HISTORY_LENGTH:
                del buf[0 : len(buf) - CANDLE_HISTORY_LENGTH]
            logger.debug("Finalized candle for token %s at bucket %s (history len=%d)", token, current["bucket"], len(buf))
        _current_candle[token] = {"bucket": bucket, "open": price, "high": price, "low": price, "close": price, "volume": 0}
        logger.debug("Started new candle for token %s bucket=%s open=%s", token, bucket, price)
        return _current_candle[token]
    else:
        cur = current
        cur["high"] = max(cur["high"], price)
        cur["low"] = min(cur["low"], price)
        cur["close"] = price
        return cur

# -------------------------
# Tick processing callback (KiteTicker)
# -------------------------
def on_connect(ws, response):
    global _connected
    _connected = True
    logger.info("Kite WebSocket connected.")
    with _lock:
        try:
            if _subscribed_tokens:
                kite_ticker.subscribe(_subscribed_tokens)
                kite_ticker.set_mode(kite_ticker.MODE_FULL, _subscribed_tokens)
                logger.info("Resubscribed tokens on connect: %s", _subscribed_tokens)
        except Exception:
            logger.exception("Failed to resubscribe tokens on connect")

def on_close(ws, code, reason):
    global _connected
    _connected = False
    logger.info("Kite WebSocket closed. Code=%s Reason=%s", code, reason)

def on_tick(ws, ticks: List[Dict[str, Any]]):
    """
    Called by KiteTicker when ticks arrive.
    Robust parsing of token, price, timestamp.
    """
    try:
        if not ticks:
            logger.debug("on_tick called with empty ticks list.")
            return

        for raw in ticks:
            try:
                logger.debug("RAW_TICK: %s", raw)

                # token detection
                token = None
                for key in ("instrument_token", "instrumentToken", "instrument", "instrumentId", "instrument_id"):
                    if raw.get(key) is not None:
                        token = raw.get(key)
                        break
                try:
                    token = int(token) if token is not None else None
                except Exception:
                    token = None

                # price detection
                price = None
                for key in ("last_price", "lastPrice", "ltp", "last_traded_price", "lastTradedPrice", "price", "last_trade_price", "closePrice"):
                    if raw.get(key) is not None:
                        try:
                            price = float(raw.get(key))
                            break
                        except Exception:
                            continue

                # timestamp detection
                ts = None
                tval = raw.get("timestamp") or raw.get("time") or raw.get("exchange_timestamp") or raw.get("exchangeTime") or raw.get("exchange_time")
                if tval is not None:
                    try:
                        if isinstance(tval, str):
                            try:
                                import dateutil.parser as _dp
                                dt = _dp.parse(tval)
                                ts = int(dt.timestamp())
                            except Exception:
                                ival = float(tval)
                                ts = int(ival / 1000) if ival > 1_000_000_000_000 else int(ival)
                        elif isinstance(tval, (int, float)):
                            tnum = int(tval)
                            ts = int(tnum / 1000) if tnum > 1_000_000_000_000 else int(tnum)
                    except Exception:
                        ts = None

                if ts is None:
                    ts = int(time.time())

                if token is None or price is None:
                    logger.debug("Ignored tick (missing token or price). token=%s price=%s keys=%s", token, price, list(raw.keys()))
                    continue

                with _lock:
                    _latest_ticks[token] = {"instrument_token": token, "last_price": price, "timestamp": ts, "raw": raw}
                    current = _ingest_tick_into_candle(token, price, ts)
                    payload = {
                        "ok": True,
                        "token": token,
                        "tick": {"instrument_token": token, "price": price, "timestamp": ts},
                        "candle": {
                            "time": int(current["bucket"]),
                            "open": float(current["open"]),
                            "high": float(current["high"]),
                            "low": float(current["low"]),
                            "close": float(current["close"]),
                            "volume": float(current.get("volume", 0)),
                        },
                        "candles": _candle_buffers.get(token, [])[-100:],
                    }

                _safe_send_to_frontends(payload)
            except Exception:
                logger.exception("Error processing raw tick element")
    except Exception:
        logger.exception("Exception in on_tick")

# -------------------------
# Kite websocket control (idempotent + safe)
# -------------------------
async def _async_stop_kite():
    """
    Async helper to close kite_ticker when FastAPI loop is active.
    """
    global kite_ticker, _connected
    try:
        if kite_ticker:
            try:
                kite_ticker.close()
                logger.info("kite_ticker.close() called")
            except Exception:
                logger.exception("kite_ticker.close() raised")
    finally:
        _connected = False
        logger.info("Kite websocket stopped (async)")

def start_websocket(api_key: str, access_token: str):
    """
    Initialize KiteTicker and start connect (threaded) if not already started.
    This function is synchronous and safe to call from FastAPI request handlers or startup.
    """
    global kite_ticker, _connected
    if KiteTicker is None:
        logger.error("KiteTicker class not importable (kiteconnect missing). Cannot start websocket.")
        return False

    if kite_ticker is not None:
        logger.info("start_websocket: already started (no-op).")
        return True

    try:
        kite_ticker = KiteTicker(api_key, access_token)
        kite_ticker.on_ticks = on_tick
        kite_ticker.on_connect = on_connect
        kite_ticker.on_close = on_close

        # connect in kiteconnect's internal thread (threaded=True) - this is non-blocking
        # kiteconnect will call our on_tick/on_connect/on_close callbacks from its own thread
        kite_ticker.connect(threaded=True)
        logger.info("Kite WebSocket connect(threaded=True) called.")
        return True
    except Exception as e:
        kite_ticker = None
        _connected = False
        logger.exception("Failed to start Kite WebSocket: %s", e)
        return False

def stop_websocket():
    """
    Synchronous stop helper. If FastAPI event loop was set, we schedule async close there to be extra safe.
    """
    global kite_ticker, _connected
    if not kite_ticker:
        logger.info("stop_websocket: kite_ticker not present (no-op).")
        _connected = False
        return

    try:
        # If we have a loop, schedule async stop to run in it so any websocket sends finish
        if _app_event_loop and _app_event_loop.is_running():
            fut = asyncio.run_coroutine_threadsafe(_async_stop_kite(), _app_event_loop)
            try:
                fut.result(timeout=5)
            except Exception:
                logger.debug("stop_websocket: async close did not finish quickly (continuing).")
        else:
            # best-effort direct close
            try:
                kite_ticker.close()
            except Exception:
                logger.exception("kite_ticker.close() raised in stop_websocket()")

    except Exception:
        logger.exception("Exception in stop_websocket")
    finally:
        kite_ticker = None
        _connected = False
        logger.info("Kite websocket stopped.")

# -------------------------
# Subscription helpers
# -------------------------
def subscribe(tokens: List[int]):
    global _subscribed_tokens
    if not tokens:
        return
    with _lock:
        try:
            new_set = set(_subscribed_tokens or []) | set(int(t) for t in tokens)
            _subscribed_tokens = sorted(list(new_set))
            logger.info("subscribe(): requested tokens -> %s", tokens)
        except Exception:
            logger.exception("subscribe(): token normalization failed")
            return

        try:
            if kite_ticker and _connected:
                kite_ticker.subscribe(_subscribed_tokens)
                kite_ticker.set_mode(kite_ticker.MODE_FULL, _subscribed_tokens)
                logger.info("Subscribed (live) to tokens: %s", _subscribed_tokens)
            else:
                logger.info("Kite not connected yet — stored tokens, will subscribe on connect: %s", _subscribed_tokens)
        except Exception:
            logger.exception("Failed to subscribe tokens on kite_ticker")

def unsubscribe(tokens: List[int]):
    global _subscribed_tokens
    if not tokens:
        return
    with _lock:
        try:
            remaining = set(_subscribed_tokens or []) - set(int(t) for t in tokens)
            _subscribed_tokens = sorted(list(remaining))
            logger.info("unsubscribe(): tokens requested -> %s; remaining -> %s", tokens, _subscribed_tokens)
        except Exception:
            logger.exception("unsubscribe(): token normalization failed")
            return

        try:
            if kite_ticker and _connected:
                if _subscribed_tokens:
                    kite_ticker.subscribe(_subscribed_tokens)
                    kite_ticker.set_mode(kite_ticker.MODE_FULL, _subscribed_tokens)
                else:
                    try:
                        kite_ticker.unsubscribe(tokens)
                    except Exception:
                        logger.debug("kite_ticker.unsubscribe failed when clearing all (non-fatal)")
                logger.info("Updated subscriptions on kite: %s", _subscribed_tokens)
        except Exception:
            logger.exception("Failed to update subscription on kite_ticker")

# -------------------------
# Query helpers
# -------------------------
def get_latest_ticks() -> List[Dict[str, Any]]:
    with _lock:
        return [dict(v) for v in _latest_ticks.values()]

def get_candle_history(token: int, limit: int = 100) -> List[Dict[str, Any]]:
    with _lock:
        buf = _candle_buffers.get(token, [])[-limit:]
        return [dict(c) for c in buf]

# -------------------------
# Frontend client management
# -------------------------
def add_frontend_client(ws: "WebSocket"):
    """
    Register a FastAPI WebSocket to receive broadcast messages.
    Caller must call await ws.accept() before registering.
    """
    with frontend_lock:
        if ws not in frontend_clients:
            frontend_clients.append(ws)
            logger.info("Frontend client added (count=%d)", len(frontend_clients))
        else:
            logger.debug("add_frontend_client: ws already registered (no-op)")

def remove_frontend_client(ws: "WebSocket"):
    with frontend_lock:
        try:
            if ws in frontend_clients:
                frontend_clients.remove(ws)
                logger.info("Frontend client removed (count=%d)", len(frontend_clients))
        except Exception:
            logger.exception("remove_frontend_client failed")

# END of file
