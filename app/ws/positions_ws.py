import asyncio
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import jwt, JWTError
from sqlalchemy import text
import os

from app.db import SessionLocal

router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "super_secret_key"))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def get_user_id_from_token(token: str) -> int:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    uid = payload.get("uid")
    if not uid:
        raise ValueError("uid missing in token")
    return int(uid)


def fetch_positions(user_id: int):
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT symbol, quantity, avg_price, ltp, pnl
                FROM positions
                WHERE user_id = :uid
                ORDER BY symbol
            """),
            {"uid": user_id},
        ).fetchall()

        return [
            {
                "symbol": r.symbol,
                "qty": int(r.quantity),
                "avg_price": float(r.avg_price),
                "ltp": float(r.ltp),
                "pnl": float(r.pnl),
            }
            for r in rows
        ]
    finally:
        db.close()


@router.websocket("/ws/positions")
async def positions_ws(websocket: WebSocket):
    await websocket.accept()

    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    try:
        user_id = get_user_id_from_token(token)
    except (JWTError, Exception):
        await websocket.close(code=1008)
        return

    try:
        while True:
            data = fetch_positions(user_id)
            await websocket.send_json({
                "type": "positions",
                "time": int(time.time()),
                "data": data,
            })
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        pass
