import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.db import SessionLocal
from sqlalchemy import text

router = APIRouter()

connected_clients = set()

@router.websocket("/ws/auto-orders")
async def auto_order_ws(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            db = SessionLocal()
            try:
                rows = db.execute(
                    text("SELECT * FROM auto_order_audit ORDER BY executed_at DESC LIMIT 10")
                ).fetchall()

                data = [
                    {
                        "user_id": r.user_id,
                        "symbol": r.symbol,
                        "side": r.side,
                        "qty": r.quantity,
                        "price": float(r.price),
                        "sl": float(r.sl or 0),
                        "tp": float(r.tp or 0),
                        "status": r.status,
                        "executed_at": str(r.executed_at)
                    }
                    for r in rows
                ]

                await websocket.send_json({"type": "auto_order_update", "data": data})

            finally:
                db.close()

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        connected_clients.discard(websocket)
