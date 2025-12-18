from app.db import SessionLocal
from sqlalchemy import text
from app.brokers.zerodha.client import ZerodhaClient

def execute_auto_order(user_id: int, symbol: str, side: str, qty: int, access_token: str, settings: dict):
    db = SessionLocal()
    try:
        broker = ZerodhaClient(access_token)
        res = broker.place_order(
            symbol=symbol,
            side=side,
            qty=qty,
            order_type="MARKET",
            product="MIS"
        )
        broker_order_id = res["order_id"]

        # Save audit
        db.execute(
            text("""
                INSERT INTO auto_order_audit
                (user_id, broker, broker_order_id, symbol, side, quantity, price, sl, tp, slippage, transaction_cost, status)
                VALUES
                (:uid, 'zerodha', :boid, :sym, :side, :qty, :price, :sl, :tp, :slip, :tc, 'FILLED')
            """),
            {
                "uid": user_id,
                "boid": broker_order_id,
                "sym": symbol,
                "side": side,
                "qty": qty,
                "price": 0,  # real-time LTP can be filled
                "sl": settings["default_sl_pct"],
                "tp": settings["default_tp_pct"],
                "slip": settings["slippage_pct"],
                "tc": settings["transaction_cost"],
            }
        )
        db.commit()
        return broker_order_id
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
