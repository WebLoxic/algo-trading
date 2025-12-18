
import os
import time
import uuid
import random
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from dotenv import load_dotenv
import uvicorn

# =====================================================
# ENV + LOGGING
# =====================================================
load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("app.main")

# =====================================================
# FASTAPI CORE
# =====================================================
from fastapi import (
    FastAPI, Depends, HTTPException,
    WebSocket, WebSocketDisconnect
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette.middleware.sessions import SessionMiddleware

from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel

from sqlalchemy import text
from app.db import SessionLocal, init_db

# =====================================================
# CREATE APP
# =====================================================
app = FastAPI(
    title="Algo Trader Backend",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =====================================================
# MIDDLEWARE
# =====================================================
SESSION_SECRET = os.getenv("SESSION_SECRET", "change_this")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
allowed_origins = [
    FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

if os.getenv("CORS_ALLOW_ALL", "false").lower() in ("1", "true", "yes"):
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# AUTH / JWT
# =====================================================
SECRET_KEY = os.getenv("JWT_SECRET", "super_secret_key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": email, "uid": user_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_current_user_row(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Invalid token")

    uid = payload.get("uid")
    if not uid:
        raise HTTPException(401, "Invalid token")

    db = SessionLocal()
    try:
        row = db.execute(
            text("""SELECT id,email,full_name,is_active,is_superuser,created_at FROM users WHERE id=:uid LIMIT 1"""),
            {"uid": uid},
        ).first()

        if not row:
            raise HTTPException(401, "User not found")

        return dict(row._mapping)
    finally:
        db.close()

# =====================================================
# AUTO LOAD ALL API ROUTES
# =====================================================
from app.api import router as api_router
from app.api import auto_register_routes

auto_register_routes()
app.include_router(api_router, prefix="/api")

# =====================================================
# SIGNAL BROADCASTER (WS)
# =====================================================
class SignalBroadcaster:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.latest = None

    async def push(self, signal: Dict[str, Any]):
        signal.setdefault("id", str(uuid.uuid4()))
        signal.setdefault("timestamp", datetime.utcnow().isoformat())
        self.latest = signal
        await self.queue.put(signal)

    async def get(self):
        return await self.queue.get()

broadcaster = SignalBroadcaster()

# =====================================================
# WEBSOCKETS
# =====================================================
@app.websocket("/ws/signals")
async def ws_signals(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            sig = await broadcaster.get()
            await ws.send_json(sig)
    except WebSocketDisconnect:
        pass

@app.websocket("/ws/market")
async def ws_market(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json({
                "symbol": "RELIANCE",
                "ltp": round(random.uniform(2300, 2450), 2),
                "timestamp": int(time.time()),
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass

# =====================================================
# TOKEN LOGIN
# =====================================================
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

@app.post("/token", response_model=Token)
def token_login(form: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT id,email,hashed_password FROM users WHERE email=:e"),
            {"e": form.username},
        ).first()

        if not row or not verify_password(form.password, row.hashed_password):
            raise HTTPException(401, "Invalid credentials")

        token = create_access_token(row.id, row.email)
        return {"access_token": token, "token_type": "bearer"}
    finally:
        db.close()

# =====================================================
# DEBUG: LIST ALL ROUTES
# =====================================================
@app.get("/__routes")
def list_all_routes():
    routes = []
    for r in app.router.routes:
        routes.append({
            "path": r.path,
            "methods": list(getattr(r, "methods", [])),
            "name": r.name,
            "type": r.__class__.__name__,
        })
    return {"count": len(routes), "routes": routes}

# =====================================================
# SELF TEST
# =====================================================
@app.get("/__selftest")
def self_test():
    return {
        "status": "ok",
        "routes": len(app.router.routes),
        "time": datetime.utcnow().isoformat(),
    }

# =====================================================
# HEALTH
# =====================================================
@app.get("/health")
def health():
    return {"ok": True, "time": int(time.time())}

# =====================================================
# STARTUP / SHUTDOWN
# =====================================================
@app.on_event("startup")
async def startup():
    init_db()
    log.info("✅ Algo Trader Backend Started")

@app.on_event("shutdown")
async def shutdown():
    log.info("🛑 Algo Trader Backend Stopped")

# =====================================================
# ENTRYPOINT
# =====================================================
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )
