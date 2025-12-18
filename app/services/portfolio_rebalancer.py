from sqlalchemy import text
from app.db import SessionLocal

def rebalance_preview(user_id: int, capital: float, targets: list[dict]):
    """
    Returns BUY / SELL actions required to rebalance portfolio
    """
    db = SessionLocal()
    try:
        # fetch current positions
        rows = db.execute(text("""
            SELECT symbol, quantity, ltp
            FROM positions
            WHERE user_id = :uid
        """), {"uid": user_id}).fetchall()

        current = {
            r.symbol: {
                "qty": int(r.quantity),
                "ltp": float(r.ltp or 0),
                "value": int(r.quantity) * float(r.ltp or 0)
            }
            for r in rows
        }

        actions = []

        for t in targets:
            symbol = t["symbol"]
            weight = float(t["weight"]) / 100.0
            target_value = capital * weight

            ltp = current.get(symbol, {}).get("ltp", 0)
            if ltp <= 0:
                continue

            target_qty = int(target_value / ltp)
            curr_qty = current.get(symbol, {}).get("qty", 0)
            diff = target_qty - curr_qty

            if diff > 0:
                actions.append({
                    "symbol": symbol,
                    "side": "BUY",
                    "qty": diff,
                    "price": ltp
                })
            elif diff < 0:
                actions.append({
                    "symbol": symbol,
                    "side": "SELL",
                    "qty": abs(diff),
                    "price": ltp
                })

        return actions

    finally:
        db.close()
