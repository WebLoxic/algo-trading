


from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import List
from sqlalchemy import text

from app.db import SessionLocal
from app.schemas import OrderCreate, OrderResponse
from app.main import get_current_user_row
from app.services.trading_engine import process_fill

router = APIRouter(prefix="/trades", tags=["Trades"])

@router.post("/zerodha/place")
def place_zerodha_order(
    payload: OrderCreate,
    user=Depends(get_current_user_row),
):
    if not user.get("zerodha_access_token"):
        raise HTTPException(400, "Zerodha not connected")

    order_id = execute_order(
        user_id=user["id"],
        symbol=payload.symbol,
        side=payload.side,
        qty=payload.quantity,
        access_token=user["zerodha_access_token"],
    )

    return {"ok": True, "order_id": order_id}

@router.post("/place", response_model=OrderResponse)
def place_order(
    payload: OrderCreate,
    user=Depends(get_current_user_row),
):
    """
    Place BUY / SELL order (production-ready, paper/broker agnostic)
    """
    db = SessionLocal()
    try:
        # 1️⃣ Create order
        result = db.execute(
            text("""
                INSERT INTO orders
                (user_id, symbol, quantity, price, side, order_type, status, created_at)
                VALUES
                (:uid, :symbol, :qty, :price, :side, :otype, 'FILLED', :ts)
                RETURNING id
            """),
            {
                "uid": user["id"],
                "symbol": payload.symbol,
                "qty": payload.quantity,
                "price": payload.price or 0,
                "side": payload.side.upper(),
                "otype": payload.order_type.upper(),
                "ts": datetime.utcnow(),
            },
        ).first()

        # 2️⃣ Update filled info (IMPORTANT)
        db.execute(
            text("""
                UPDATE orders
                SET filled_qty = :qty,
                    avg_price = :price
                WHERE id = :oid
            """),
            {
                "qty": payload.quantity,
                "price": payload.price or 0,
                "oid": result.id,
            },
        )

        db.commit()

        # 3️⃣ Trading engine (fills → positions → pnl)
        process_fill(
            user_id=user["id"],
            order_id=result.id,
            symbol=payload.symbol,
            side=payload.side.upper(),
            fill_qty=payload.quantity,
            fill_price=float(payload.price or 0),
        )

        return OrderResponse(
            id=result.id,
            user_id=user["id"],
            symbol=payload.symbol,
            quantity=payload.quantity,
            price=payload.price,
            order_type=payload.order_type,
            side=payload.side.upper(),
            status="FILLED",
            created_at=datetime.utcnow(),
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Order failed: {e}")

    finally:
        db.close()


@router.get("/history", response_model=List[OrderResponse])
def order_history(user=Depends(get_current_user_row)):
    """
    Full order history (latest first)
    """
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT
                    id,
                    user_id,
                    symbol,
                    quantity,
                    price,
                    order_type,
                    side,
                    status,
                    created_at
                FROM orders
                WHERE user_id = :uid
                ORDER BY id DESC
            """),
            {"uid": user["id"]},
        ).fetchall()

        return [OrderResponse(**dict(r._mapping)) for r in rows]

    finally:
        db.close()
