# app/order_manager.py
import logging
from threading import Lock
from datetime import datetime

from .kite_client import kite_client

log = logging.getLogger(__name__)

# ---- Optional Redis hooks (best-effort) ----
_HAS_REDIS = False
_redis_set_last_signal = None
_redis_publish = None
try:
    # prefer explicit helpers if your redis_client provides them
    from .redis_client import set_last_signal as _set_last_signal  # (key, payload, expire_seconds)
    _redis_set_last_signal = _set_last_signal
    try:
        # your project earlier used publish_channel(name, payload)
        from .redis_client import publish_channel as _publish_channel
        def _pub(payload: dict):
            # publish to a standard channel for UI/backends
            try:
                _publish_channel("signal_updates", payload)
            except Exception:
                # fallback channel name
                _publish_channel("signals", payload)
        _redis_publish = _pub
    except Exception:
        # if there's publish_signal(payload) helper
        from .redis_client import publish_signal as _publish_signal
        _redis_publish = _publish_signal
    _HAS_REDIS = True
except Exception:
    _HAS_REDIS = False

# ---- Optional WebSocket broadcaster (best-effort) ----
_ws_publish = None
try:
    from .ws_broadcast import publish_signal as _ws_pub
    _ws_publish = _ws_pub
except Exception:
    _ws_publish = None

# ---- Optional CRUD helpers (best-effort) ----
_HAS_CRUD_SAVE_SIGNAL = False
_save_signal_fn = None
try:
    from .crud import save_signal as _crud_save_signal
    _save_signal_fn = _crud_save_signal
    _HAS_CRUD_SAVE_SIGNAL = True
except Exception:
    _HAS_CRUD_SAVE_SIGNAL = False

_save_order_fn = None
try:
    from .crud import save_order as _crud_save_order
    _save_order_fn = _crud_save_order
except Exception:
    _save_order_fn = None


class OrderManager:
    """
    Singleton OrderManager
    - In-memory last_signals (fast lookup)
    - Redis cache + pub/sub (if redis_client available)
    - WebSocket broadcast to all connected clients (if ws_broadcast available)
    - Optional DB persistence (crud.save_signal, crud.save_order)
    - Thread-safe order placement via kite_client
    """
    _instance = None

    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.lock = Lock()
        # token (str) -> signal dict
        self.last_signals = {}

    # ---------------------------
    # Signal registration / lookup
    # ---------------------------
    def register_signal(self, token, data):
        """
        Register a new signal for instrument token.

        token: int/str instrument token
        data: dict with fields e.g.
              {
                "action": "BUY"/"SELL"/"HOLD",
                "prob_up": 0.73,
                "score": 0.65,
                "sentiment": 0.21,
                "tradingsymbol": "RELIANCE",
                "details": {...},
                "ts": "iso8601"   # optional
              }
        Effects:
         - update in-memory dict
         - write into Redis (set+expire) & publish on pubsub (best-effort)
         - broadcast to WebSocket clients (best-effort)
         - persist to DB via crud.save_signal (best-effort)
        """
        token_key = str(token)
        payload = dict(data) if isinstance(data, dict) else {"action": str(data)}
        if "ts" not in payload:
            payload["ts"] = datetime.utcnow().isoformat()
        if "instrument_token" not in payload:
            payload["instrument_token"] = token_key

        # update in-memory
        self.last_signals[token_key] = payload

        # Redis: set + publish (best-effort)
        if _HAS_REDIS:
            try:
                if _redis_set_last_signal:
                    _redis_set_last_signal(token_key, payload, expire_seconds=600)
            except Exception:
                log.exception("Redis set_last_signal failed for %s", token_key)
            try:
                if _redis_publish:
                    _redis_publish(payload)
            except Exception:
                log.exception("Redis publish failed for %s", token_key)

        # WebSocket broadcast to connected UIs (best-effort)
        try:
            if _ws_publish:
                _ws_publish({"type": "signal", "token": token_key, "signal": payload})
        except Exception:
            log.debug("WS publish failed (non-fatal) for %s", token_key)

        # Persist to DB (best-effort) — compatible with your current crud.save_signal(signal_dict)
        if _HAS_CRUD_SAVE_SIGNAL and _save_signal_fn:
            try:
                # Your crud.save_signal(signal_dict) signature:
                # it expects a dict and stores fields internally.
                _save_signal_fn(payload)
            except TypeError:
                # If another signature exists (kwargs), try mapping
                try:
                    _save_signal_fn(
                        instrument_token=token_key,
                        tradingsymbol=payload.get("tradingsymbol"),
                        ts=payload.get("ts"),
                        score=payload.get("score"),
                        prob_up=payload.get("prob_up"),
                        sentiment=payload.get("sentiment"),
                        details=payload.get("details") or payload
                    )
                except Exception:
                    log.exception("Failed to persist signal with kwargs for %s", token_key)
            except Exception:
                log.exception("Failed to persist signal for %s", token_key)

        log.info("Registered signal for %s: %s", token_key, payload)
        return payload

    def get_signals(self):
        # return a shallow copy to avoid external mutation
        return dict(self.last_signals)

    def get_signal_for_token(self, token):
        return self.last_signals.get(str(token))

    def clear_signal(self, token):
        token_key = str(token)
        if token_key in self.last_signals:
            del self.last_signals[token_key]
        # best-effort redis clear
        if _HAS_REDIS and _redis_set_last_signal:
            try:
                _redis_set_last_signal(token_key, {}, expire_seconds=1)
            except Exception:
                log.exception("Failed to clear last_signal in Redis for %s", token_key)

    # ---------------------------
    # Order placement wrapper
    # ---------------------------
    def place_market_order(
        self,
        instrument_token,
        side,
        quantity,
        exchange="NSE",
        tradingsymbol=None,
        product="MIS",
        order_type="MARKET",
        record=True,
    ):
        """
        Place an order through kite_client (thread-safe).

        Returns:
          - broker response dict on success,
          - {"success": False, "error": "..."} on failure.
        """
        with self.lock:
            try:
                tx = "BUY" if str(side).upper() == "BUY" else "SELL"
                symbol = tradingsymbol or str(instrument_token)
                params = dict(
                    variety="regular",
                    exchange=exchange,
                    tradingsymbol=symbol,
                    transaction_type=tx,
                    quantity=int(quantity),
                    product=product,
                    order_type=order_type,
                )
                log.info("Placing order: %s", params)
                res = kite_client.place_order(**params)

                # Optional: persist order (best-effort)
                if record and _save_order_fn:
                    try:
                        # Let your save_order accept raw 'res' first
                        _save_order_fn(res)
                    except Exception:
                        # Minimal mapping
                        try:
                            _save_order_fn({
                                "order_id": (res.get("order_id") if isinstance(res, dict) else None),
                                "tradingsymbol": symbol,
                                "transaction_type": tx,
                                "quantity": int(quantity),
                                "product": product,
                                "order_type": order_type,
                                "raw": res
                            })
                        except Exception:
                            log.debug("save_order failed; ignoring")

                # Also broadcast order info to WS (best-effort)
                try:
                    if _ws_publish:
                        _ws_publish({"type": "order", "token": str(instrument_token), "order": res})
                except Exception:
                    pass

                return res
            except Exception as e:
                log.exception("place_market_order failed for %s: %s", instrument_token, e)
                return {"success": False, "error": str(e)}


# module-level alias (backwards compatibility)
OrderManager = OrderManager
