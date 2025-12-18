# # app/ws_broadcast.py
# import asyncio
# import logging
# from typing import Any, Dict, Set
# from fastapi import WebSocket, WebSocketDisconnect

# log = logging.getLogger("app.ws_broadcast")

# _active_ws: Set[WebSocket] = set()
# _lock = asyncio.Lock()

# _message_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)


# # --------------------------------------------------------
# # 1) CLIENT HANDLER
# # --------------------------------------------------------
# async def ws_handler(websocket: WebSocket):
#     await websocket.accept()

#     async with _lock:
#         _active_ws.add(websocket)

#     log.info(f"✅ Frontend WebSocket connected (total={len(_active_ws)})")

#     try:
#         while True:
#             try:
#                 await websocket.receive_text()
#             except WebSocketDisconnect:
#                 break
#             except Exception:
#                 await asyncio.sleep(0.1)

#     finally:
#         async with _lock:
#             _active_ws.discard(websocket)

#         log.info(f"❌ WebSocket disconnected (total={len(_active_ws)})")


# # --------------------------------------------------------
# # 2) BROADCAST ENGINE
# # --------------------------------------------------------
# async def _broadcast_engine():
#     log.info("🛰️ Broadcast engine started")

#     while True:
#         payload = await _message_queue.get()

#         if not payload:
#             _message_queue.task_done()
#             continue

#         if not _active_ws:
#             _message_queue.task_done()
#             await asyncio.sleep(0.05)
#             continue

#         dead_clients = []

#         for ws in list(_active_ws):
#             try:
#                 await ws.send_json(payload)
#             except Exception:
#                 dead_clients.append(ws)

#         if dead_clients:
#             async with _lock:
#                 for ws in dead_clients:
#                     _active_ws.discard(ws)

#         _message_queue.task_done()


# # --------------------------------------------------------
# # 3) ASYNC PUBLISH
# # --------------------------------------------------------
# async def publish_signal_async(payload: Dict[str, Any]):
#     """Async publish — can be awaited safely"""
#     try:
#         await _message_queue.put(payload)
#     except asyncio.QueueFull:
#         log.warning("⚠️ WebSocket queue full — dropping message")


# # --------------------------------------------------------
# # 4) SYNC-SAFE publish() WRAPPER
# # --------------------------------------------------------
# def publish_signal(payload: Dict[str, Any]):
#     """
#     This allows calling publish_signal() from NON-ASYNC code.
#     Works in background without await.
#     """
#     try:
#         loop = asyncio.get_running_loop()
#         loop.create_task(publish_signal_async(payload))
#     except RuntimeError:
#         asyncio.run(publish_signal_async(payload))


# # --------------------------------------------------------
# # 5) START LOOP ON APP STARTUP
# # --------------------------------------------------------
# async def start_ws_broadcast_loop():
#     asyncio.create_task(_broadcast_engine())
#     log.info("🚀 WS broadcast loop started")





# app/ws_broadcast.py
import asyncio
import logging
from typing import Any, Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

log = logging.getLogger("app.ws_broadcast")

_active_ws: Set[WebSocket] = set()
_lock = asyncio.Lock()

# Queue for outgoing messages
_message_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)


# --------------------------------------------------------
# 1) CLIENT HANDLER
# --------------------------------------------------------
async def ws_handler(websocket: WebSocket):
    await websocket.accept()

    async with _lock:
        _active_ws.add(websocket)

    log.info(f"✅ Frontend WebSocket connected (total={len(_active_ws)})")

    try:
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception:
                await asyncio.sleep(0.1)

    finally:
        async with _lock:
            _active_ws.discard(websocket)

        log.info(f"❌ WebSocket disconnected (total={len(_active_ws)})")


# --------------------------------------------------------
# 2) BROADCAST ENGINE
# --------------------------------------------------------
async def _broadcast_engine():
    log.info("🛰️ Broadcast engine started")

    while True:
        payload = await _message_queue.get()

        if not payload:
            _message_queue.task_done()
            continue

        dead_clients = []

        for ws in list(_active_ws):
            try:
                await ws.send_json(payload)
            except Exception:
                dead_clients.append(ws)

        # Clean dead clients
        if dead_clients:
            async with _lock:
                for ws in dead_clients:
                    _active_ws.discard(ws)

        _message_queue.task_done()


# --------------------------------------------------------
# 3) PUBLISH (async always)
# --------------------------------------------------------
async def publish_signal(payload: Dict[str, Any]):
    """ALWAYS ASYNC — must be awaited or create_task() used."""
    try:
        await _message_queue.put(payload)
    except asyncio.QueueFull:
        log.warning("⚠️ Queue full — dropping message")


# --------------------------------------------------------
# 4) START LOOP ON STARTUP
# --------------------------------------------------------
async def start_ws_broadcast_loop():
    asyncio.create_task(_broadcast_engine())
    log.info("🚀 WebSocket broadcast loop started")
