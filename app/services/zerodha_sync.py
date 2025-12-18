from sqlalchemy import text
from app.db import SessionLocal
from app.brokers.zerodha.client import ZerodhaClient

def sync_positions(user_id: int, access_token: str):
    db = SessionLocal()
    try:
        broker = ZerodhaClient(access_token)
        positions = broker.positions()

        for p in positions:
            db.execute(text("""
                INSERT INTO positions
                (user_id, symbol, quantity, avg_price, ltp, pnl)
                VALUES
                (:uid, :sym, :qty, :avg, :ltp, :pnl)
                ON CONFLICT (user_id, symbol)
                DO UPDATE SET
                    quantity = EXCLUDED.quantity,
                    avg_price = EXCLUDED.avg_price,
                    ltp = EXCLUDED.ltp,
                    pnl = EXCLUDED.pnl,
                    last_updated = NOW()
            """), {
                "uid": user_id,
                "sym": p["tradingsymbol"],
                "qty": p["quantity"],
                "avg": p["average_price"],
                "ltp": p["last_price"],
                "pnl": p["pnl"],
            })

        db.commit()

    finally:
        db.close()
