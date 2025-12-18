from sqlalchemy import text
from app.db import SessionLocal
from app.brokers.zerodha.client import ZerodhaClient


# =====================================================
# 1️⃣ CORE ENGINE (FILLS → POSITIONS → PnL)
# =====================================================
def process_fill(
    *,
    user_id: int,
    order_id: int,
    symbol: str,
    side: str,
    fill_qty: int,
    fill_price: float,
):
    """
    🔥 CORE TRADING ENGINE
    Handles:
    - order_fills
    - positions update
    - realized PnL
    - position_history
    """
    db = SessionLocal()
    try:
        # ---- record fill ----
        db.execute(
            text("""
                INSERT INTO order_fills (order_id, quantity, price)
                VALUES (:oid, :q, :p)
            """),
            {"oid": order_id, "q": fill_qty, "p": fill_price},
        )

        # ---- lock position ----
        pos = db.execute(
            text("""
                SELECT *
                FROM positions
                WHERE user_id=:uid AND symbol=:sym
                FOR UPDATE
            """),
            {"uid": user_id, "sym": symbol},
        ).fetchone()

        # ---- NO POSITION YET ----
        if not pos:
            if side == "BUY":
                db.execute(
                    text("""
                        INSERT INTO positions
                        (user_id, symbol, quantity, avg_price)
                        VALUES (:uid, :sym, :q, :p)
                    """),
                    {
                        "uid": user_id,
                        "sym": symbol,
                        "q": fill_qty,
                        "p": fill_price,
                    },
                )

        # ---- EXISTING POSITION ----
        else:
            old_qty = int(pos.quantity)
            old_avg = float(pos.avg_price)

            # BUY → ADD POSITION
            if side == "BUY":
                new_qty = old_qty + fill_qty
                new_avg = ((old_qty * old_avg) + (fill_qty * fill_price)) / new_qty

                db.execute(
                    text("""
                        UPDATE positions
                        SET quantity=:q,
                            avg_price=:a,
                            last_updated=NOW()
                        WHERE id=:id
                    """),
                    {
                        "q": new_qty,
                        "a": new_avg,
                        "id": pos.id,
                    },
                )

            # SELL → REDUCE / CLOSE
            else:
                sell_qty = min(old_qty, fill_qty)
                realized = (fill_price - old_avg) * sell_qty
                new_qty = old_qty - sell_qty

                # FULL EXIT
                if new_qty == 0:
                    db.execute(
                        text("""
                            INSERT INTO position_history
                            (user_id, symbol,
                             buy_qty, sell_qty,
                             buy_avg, sell_avg,
                             realized_pnl,
                             opened_at)
                            VALUES
                            (:uid, :sym,
                             :bq, :sq,
                             :ba, :sa,
                             :pnl,
                             :opened)
                        """),
                        {
                            "uid": user_id,
                            "sym": symbol,
                            "bq": old_qty,
                            "sq": sell_qty,
                            "ba": old_avg,
                            "sa": fill_price,
                            "pnl": realized,
                            "opened": pos.last_updated,
                        },
                    )

                    db.execute(
                        text("DELETE FROM positions WHERE id=:id"),
                        {"id": pos.id},
                    )

                # PARTIAL EXIT
                else:
                    db.execute(
                        text("""
                            UPDATE positions
                            SET quantity=:q,
                                last_updated=NOW()
                            WHERE id=:id
                        """),
                        {
                            "q": new_qty,
                            "id": pos.id,
                        },
                    )

        db.commit()

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# =====================================================
# 2️⃣ ZERODHA EXECUTION LAYER
# =====================================================
def execute_zerodha_order(
    *,
    user_id: int,
    symbol: str,
    side: str,
    qty: int,
    access_token: str,
):
    """
    🚀 REAL Zerodha execution
    - Places order at broker
    - Stores broker_order_id
    """
    db = SessionLocal()
    try:
        broker = ZerodhaClient(access_token)

        # ---- place order ----
        res = broker.place_order(
            symbol=symbol,
            side=side,
            qty=qty,
        )

        broker_order_id = res["order_id"]

        # ---- store order ----
        row = db.execute(
            text("""
                INSERT INTO orders
                (user_id, broker, broker_order_id,
                 symbol, side, quantity, status)
                VALUES
                (:uid, 'zerodha', :boid,
                 :sym, :side, :qty, 'OPEN')
                RETURNING id
            """),
            {
                "uid": user_id,
                "boid": broker_order_id,
                "sym": symbol,
                "side": side,
                "qty": qty,
            },
        ).first()

        db.commit()
        return row.id

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# =====================================================
# 3️⃣ UNIFIED ORDER EXECUTION (🔥 REQUIRED)
# =====================================================
def execute_order(
    *,
    user_id: int,
    symbol: str,
    side: str,
    quantity: int,
    broker: str = "zerodha",
    access_token: str | None = None,
):
    """
    ✅ SINGLE ENTRY POINT FOR ALL ORDER EXECUTION

    Used by:
    - portfolio_executor
    - auto_order executor
    - trade routes

    Flow:
    execute_order → broker-specific executor → DB
    """

    side = side.upper()
    if side not in ("BUY", "SELL"):
        raise ValueError("Invalid side, must be BUY or SELL")

    if broker == "zerodha":
        if not access_token:
            raise ValueError("Zerodha access_token required")

        return execute_zerodha_order(
            user_id=user_id,
            symbol=symbol,
            side=side,
            qty=quantity,
            access_token=access_token,
        )

    raise NotImplementedError(f"Broker not supported: {broker}")
