

# app/strategy.py
"""
StrategyEngine: central decision engine for manual vs auto trading.

✅ Updated behavior:
 - Manual / Auto mode toggle supported.
 - Auto mode: places BUY when price predicted to go UP (low → high).
 - Auto mode: places SELL when price predicted to go DOWN (high → low).
 - Manual mode: only sends signals to frontend, no automatic orders.
 - User can set trade amount and duration (via frontend settings).
"""

import os
import time
import logging
from threading import Lock
from datetime import datetime, timedelta

from .crud import get_latest_sentiment
from .order_manager import OrderManager
from .indicators import compute_signals
from . import ml_model
from . import ws_broadcast
from .models import Instrument

log = logging.getLogger(__name__)

# === Configurable thresholds ===
PROB_THRESHOLD = float(os.getenv("STRAT_PROB_THRESHOLD", "0.6"))
SENTIMENT_THRESHOLD = float(os.getenv("STRAT_SENTIMENT_THRESHOLD", "-0.1"))
MIN_VOLUME = int(os.getenv("STRAT_MIN_VOLUME", "0"))
COOLDOWN_SECS = int(os.getenv("STRAT_COOLDOWN_SECS", "10"))
USE_INDICATOR_CONFIRM = os.getenv("STRAT_USE_INDICATOR_CONFIRM", "true").lower() in ("1","true","yes")


class StrategyEngine:
    _instance = None

    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.lock = Lock()
        self.mode = os.getenv("STRAT_MODE", "manual")  # default manual
        self._last_action_time = {}
        self._open_positions = {}
        self._last_signals = {}
        # frontend will set these dynamically
        self.trade_amount = float(os.getenv("STRAT_AUTO_AMOUNT", "1"))
        self.trade_duration = int(os.getenv("STRAT_AUTO_DURATION", "60"))
        log.info("StrategyEngine initialized (mode=%s)", self.mode)

    # ============ MODE CONTROL ============
    def set_mode(self, mode: str):
        if mode not in ("manual", "auto"):
            raise ValueError("mode must be 'manual' or 'auto'")
        with self.lock:
            self.mode = mode
        log.info("StrategyEngine mode set to %s", mode)

    def get_mode(self):
        return self.mode

    def update_auto_settings(self, amount: float, duration: int):
        """Frontend can update these before enabling auto mode."""
        self.trade_amount = amount
        self.trade_duration = duration
        log.info(f"Auto settings updated: amount={amount}, duration={duration}s")

    # ============ INTERNAL HELPERS ============
    def _can_place_auto(self, token: str):
        now = datetime.utcnow()
        last = self._last_action_time.get(token)
        if last and (now - last).total_seconds() < COOLDOWN_SECS:
            return False
        return True

    def _record_auto_action(self, token: str):
        self._last_action_time[token] = datetime.utcnow()

    def _compute_ml_prob(self, token: str, features: dict):
        try:
            model = getattr(ml_model, "model", None)
            if model is None and hasattr(ml_model, "predict_proba"):
                return ml_model.predict_proba(features)

            prepare = getattr(ml_model, "prepare_features", None)
            X = prepare(features) if prepare else features

            if hasattr(ml_model, "predict_proba"):
                res = ml_model.predict_proba(X)
                if isinstance(res, (list, tuple)):
                    try:
                        return float(res[0][1])
                    except Exception:
                        return float(res[1]) if len(res) == 2 else None
                return float(res)
            elif hasattr(ml_model, "predict"):
                p = ml_model.predict(X)
                return float(p[0]) if isinstance(p, (list, tuple)) else float(p)
            return None
        except Exception as e:
            log.debug("ML prob computation failed: %s", e)
            return None

    # ============ SIGNAL CREATION ============
    def _compose_signal(self, tick: dict):
        try:
            token = int(tick.get("instrument_token") or tick.get("instrumentToken") or tick.get("instrument") or 0)
            symbol = tick.get("tradingsymbol") or tick.get("symbol")
            ltp = tick.get("last_price") or tick.get("ltp") or tick.get("price")
            vol = tick.get("volume") or tick.get("totalBuyQuantity")

            # Compute indicators
            try:
                indicators = compute_signals(token)
            except Exception:
                indicators = {}

            # Sentiment score
            sentiment_score = None
            ticker_for_sent = symbol + ".NS" if symbol and not symbol.upper().endswith(".NS") else symbol
            try:
                sentiment_entry = get_latest_sentiment(ticker_for_sent)
                if sentiment_entry:
                    sentiment_score = float(getattr(sentiment_entry, "score", 0.0))
            except Exception:
                sentiment_score = None

            # ML prediction probability
            ml_prob = self._compute_ml_prob(token, indicators or tick)

            # Combine indicators, sentiment, ML
            score = 0.0
            weights = {"ml": 0.6, "sent": 0.2, "ind": 0.2}
            if ml_prob is not None:
                score += weights["ml"] * (ml_prob if 0 <= ml_prob <= 1 else 0.5)
            if sentiment_score is not None:
                score += weights["sent"] * ((sentiment_score + 1) / 2.0)

            ind_conf = 0.0
            if indicators:
                if indicators.get("ema_cross") == 1:
                    ind_conf = 1.0
                rsi = indicators.get("rsi14") or indicators.get("rsi")
                if rsi and float(rsi) < 35:
                    ind_conf = max(ind_conf, 0.6)
            score += weights["ind"] * ind_conf

            # ✅ Action logic:
            # - If model predicts UP (ml_prob >= threshold), BUY
            # - If model predicts DOWN (ml_prob < (1 - threshold)), SELL
            # - Otherwise HOLD
            action = "HOLD"
            if ml_prob is not None:
                if ml_prob >= PROB_THRESHOLD:
                    action = "BUY"
                elif ml_prob <= (1 - PROB_THRESHOLD):
                    action = "SELL"

            signal = {
                "token": token,
                "symbol": symbol,
                "ts": datetime.utcnow().isoformat(),
                "ltp": ltp,
                "volume": vol,
                "indicators": indicators,
                "sentiment": sentiment_score,
                "ml_prob": ml_prob,
                "score": score,
                "action": action
            }
            return signal
        except Exception as e:
            log.exception("compose_signal failed: %s", e)
            return None

    # ============ MAIN ENTRY ============
    def on_ticks(self, ticks):
        if not ticks:
            return

        for t in ticks:
            try:
                sig = self._compose_signal(t)
                if not sig:
                    continue
                token = sig["token"]
                self._last_signals[token] = sig

                # Register + broadcast to frontend
                try:
                    OrderManager.instance().register_signal(token, sig)
                    ws_broadcast.publish_signal({"type": "signal", "token": token, "signal": sig})
                except Exception:
                    pass

                if self.mode == "manual":
                    # ✅ manual mode: only show signal, user decides buy/sell
                    continue

                # ✅ auto mode logic
                if self.mode == "auto" and self._can_place_auto(token):
                    qty = int(self.trade_amount)
                    side = sig["action"]

                    if side not in ("BUY", "SELL"):
                        continue

                    # prevent repeat trade if same side already open
                    existing = self._open_positions.get(token)
                    if existing and existing["side"] == side:
                        continue

                    try:
                        res = OrderManager.instance().place_market_order(
                            instrument_token=token,
                            side=side,
                            quantity=qty,
                            exchange="NSE",
                            tradingsymbol=sig["symbol"],
                            product="MIS",
                            order_type="MARKET"
                        )
                        self._record_auto_action(token)
                        log.info(f"AUTO {side} ORDER placed for {sig['symbol']} qty={qty}")
                        self._open_positions[token] = {"side": side, "qty": qty, "ts": datetime.utcnow()}
                        ws_broadcast.publish_signal({"type":"order","token":token,"order":res})
                    except Exception as e:
                        log.error(f"Auto order failed for {sig['symbol']}: {e}")
                        continue
            except Exception:
                log.exception("on_ticks handler error (continue)")

    def get_last_signals(self):
        return self._last_signals
