from sqlalchemy import text
from app.db import SessionLocal


def update_ltp(symbol: str, ltp: float):
    """
    Update LTP + unrealized PnL for all users holding this symbol.
    Called from broker / market tick stream.
    """
    db = SessionLocal()
    try:
        db.execute(
            text("""
                UPDATE positions
                SET
                    ltp = :ltp,
                    pnl = ( :ltp - avg_price ) * quantity,
                    last_updated = NOW()
                WHERE symbol = :sym
                  AND quantity != 0
            """),
            {
                "ltp": ltp,
                "sym": symbol,
            },
        )
        db.commit()
    finally:
        db.close()
