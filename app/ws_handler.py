# app/ws_handler.py
from fastapi import APIRouter, WebSocket
from app.ws_broadcast import ws_handler as broadcast_ws_handler

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await broadcast_ws_handler(websocket)

# add this alias route so /ws/market also works
@router.websocket("/ws/market")
async def websocket_market_endpoint(websocket: WebSocket):
    await broadcast_ws_handler(websocket)
