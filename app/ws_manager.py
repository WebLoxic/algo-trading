import json, logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)
        logger.info("WS client connected. total=%d", len(self.connections))

    async def disconnect(self, websocket: WebSocket):
        try: self.connections.remove(websocket)
        except ValueError: pass
        logger.info("WS client disconnected. total=%d", len(self.connections))

    async def broadcast_json(self, message: dict):
        for conn in list(self.connections):
            try:
                await conn.send_json(message)
                print("📡 SENT:", message)
            except:
                await self.disconnect(conn)

manager = ConnectionManager()


async def publish_signal(data: dict):
    """Send ML prediction to all WebSocket clients"""
    print("📡 PUBLISH:", data)
    await manager.broadcast_json(data)
