from fastapi import APIRouter, WebSocket
import asyncio, random, time

router = APIRouter()

@router.websocket("/ws/market")
async def market_ws(ws: WebSocket):
    await ws.accept()

    try:
        while True:
            data = {
                "symbol": "RELIANCE",
                "ltp": round(random.uniform(2300, 2450), 2),
                "time": int(time.time())
            }
            await ws.send_json(data)
            await asyncio.sleep(1)
    except:
        await ws.close()
