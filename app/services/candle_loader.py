from sqlalchemy import text
from app.db import SessionLocal


def load_candles(symbol, interval, start, end):
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT open, high, low, close, ts
                FROM market_candles
                WHERE symbol = :sym
                  AND interval = :intv
                  AND ts BETWEEN :f AND :t
                ORDER BY ts ASC
            """),
            {
                "sym": symbol,
                "intv": interval,
                "f": start,
                "t": end,
            },
        ).fetchall()

        # fallback demo candles
        if not rows:
            price = 2400
            rows = []
            for i in range(300):
                o = price
                c = o + (2 if i % 3 else -1)
                rows.append({
                    "open": o,
                    "high": max(o, c) + 2,
                    "low": min(o, c) - 2,
                    "close": c,
                    "ts": i
                })
                price = c

        return rows
    finally:
        db.close()
