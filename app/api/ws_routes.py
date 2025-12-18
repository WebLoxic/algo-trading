from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json

router = APIRouter()

@router.websocket("/ws/market")
async def ws_market(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json({"type": "market", "msg": "market data ok"})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("Market WS disconnected")
    except Exception as e:
        print("Market WS error:", e)


@router.websocket("/ws/signals")
async def ws_signals(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json({"type": "signal", "msg": "signal update"})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("Signals WS disconnected")
    except Exception as e:
        print("Signals WS error:", e)
