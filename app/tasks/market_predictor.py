# app/tasks/market_predictor.py
import asyncio
import logging
import random
import datetime
from typing import Dict, Any

from app import ml_model
from app.ws_manager import publish_signal   # << FIXED IMPORT

log = logging.getLogger("app.tasks.market_predictor")


def get_predicted_price(current_price: float, sentiment_score: float) -> float:
    base_change = random.uniform(-0.02, 0.02)
    sentiment_influence = sentiment_score * 0.01
    final_change = base_change + sentiment_influence
    return round(current_price * (1 + final_change), 2)


def get_sentiment_score() -> float:
    return round(random.uniform(-1, 1), 3)


async def run_market_prediction():
    log.info("🤖 ML market predictor started.")
    current_price = 100.0

    while True:
        try:
            sentiment = get_sentiment_score()
            predicted_price = get_predicted_price(current_price, sentiment)

            price_change_pct = (predicted_price - current_price) / current_price
            hybrid_strength = (0.7 * price_change_pct) + (0.3 * sentiment * 0.01)

            if hybrid_strength > 0.01:
                signal = "SELL"
                reason = "Predicted price rising; sentiment bullish — good time to SELL."
            elif hybrid_strength < -0.01:
                signal = "BUY"
                reason = "Predicted price dropping; sentiment bearish — good time to BUY."
            else:
                signal = "HOLD"
                reason = "No clear trend; market stable."

            payload: Dict[str, Any] = {
                "id": int(datetime.datetime.utcnow().timestamp() * 1000),
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "current_price": current_price,
                "predicted_price": predicted_price,
                "price_change_pct": round(price_change_pct * 100, 2),
                "sentiment": sentiment,
                "signal": signal,
                "reason": reason,
            }

            log.info(
                f"📊 Market prediction — {signal}: {reason} "
                f"(Δ={payload['price_change_pct']}%, Sentiment={sentiment})"
            )

            ml_model.last_prediction = payload

            # 🔥 FIX: websocket broadcast
            asyncio.create_task(publish_signal(payload))

            current_price = predicted_price

        except Exception as e:
            log.exception(f"Prediction loop error: {e}")

        # run every 7 minutes
        await asyncio.sleep(7 * 60)
