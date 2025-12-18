# # app/api/broker_zerodha.py
# import os
# import hashlib
# from datetime import datetime, timedelta
# from typing import Optional

# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel
# import httpx

# from app.db import SessionLocal  # your existing SQLAlchemy session factory
# from sqlalchemy import text

# router = APIRouter()

# KITE_API_KEY = os.getenv("KITE_API_KEY")
# KITE_API_SECRET = os.getenv("KITE_API_SECRET")
# KITE_SESSION_URL = os.getenv("KITE_SESSION_URL", "https://api.kite.trade/session/token")

# class ExchangeIn(BaseModel):
#     user_id: int
#     request_token: str

# class DisconnectIn(BaseModel):
#     user_id: int

# def upsert_connection_sync(session, user_id: int, access_token: str, refresh_token: str, expires_at: datetime):
#     """
#     Upsert into broker_connections using raw SQL to avoid model dependency.
#     """
#     sql = """
#     INSERT INTO broker_connections (user_id, broker, access_token, refresh_token, expires_at, connected, updated_at)
#     VALUES (:user_id, 'zerodha', :access_token, :refresh_token, :expires_at, true, now())
#     ON CONFLICT (user_id, broker)
#     DO UPDATE SET access_token = EXCLUDED.access_token,
#                   refresh_token = EXCLUDED.refresh_token,
#                   expires_at = EXCLUDED.expires_at,
#                   connected = true,
#                   updated_at = now();
#     """
#     session.execute(text(sql), {
#         "user_id": user_id,
#         "access_token": access_token,
#         "refresh_token": refresh_token,
#         "expires_at": expires_at,
#     })
#     session.commit()

# @router.post("/api/brokers/zerodha/exchange")
# async def exchange_token(payload: ExchangeIn):
#     if not payload.request_token:
#         raise HTTPException(status_code=400, detail="missing request_token")
#     if not KITE_API_KEY or not KITE_API_SECRET:
#         raise HTTPException(status_code=500, detail="Kite API keys not configured on server")

#     # compute checksum per Kite docs
#     checksum = hashlib.sha256((KITE_API_KEY + payload.request_token + KITE_API_SECRET).encode()).hexdigest()
#     data = {"api_key": KITE_API_KEY, "request_token": payload.request_token, "checksum": checksum}

#     async with httpx.AsyncClient(timeout=20.0) as client:
#         resp = await client.post(KITE_SESSION_URL, data=data)
#         if resp.status_code != 200:
#             raise HTTPException(status_code=500, detail=f"Kite exchange failed: {resp.status_code} {resp.text}")

#         j = resp.json()
#         data_obj = j.get("data") or j
#         access_token = data_obj.get("access_token")
#         refresh_token = data_obj.get("refresh_token") or data_obj.get("public_token")
#         expires_in = data_obj.get("expires_in") or 24 * 3600

#         if not access_token:
#             raise HTTPException(status_code=500, detail=f"Access token not present in Kite response: {j}")

#         expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))

#     # sync DB upsert using SQLAlchemy session
#     session = SessionLocal()
#     try:
#         upsert_connection_sync(session, payload.user_id, access_token, refresh_token, expires_at)
#     finally:
#         session.close()

#     return {"ok": True}

# @router.get("/api/brokers/zerodha/status")
# def status(user_id: int):
#     session = SessionLocal()
#     try:
#         row = session.execute(text("""
#             SELECT connected, expires_at FROM broker_connections
#             WHERE user_id = :user_id AND broker = 'zerodha'
#         """), {"user_id": user_id}).fetchone()
#         if not row:
#             return {"ok": True, "status": {"connected": False, "expires_at": None}}
#         connected = bool(row[0])
#         expires_at = row[1]
#         if expires_at and expires_at < datetime.utcnow():
#             session.execute(text("""
#                 UPDATE broker_connections
#                 SET connected = false, access_token = NULL, refresh_token = NULL, expires_at = NULL, updated_at = now()
#                 WHERE user_id = :user_id AND broker = 'zerodha'
#             """), {"user_id": user_id})
#             session.commit()
#             return {"ok": True, "status": {"connected": False, "expires_at": None}}
#         return {"ok": True, "status": {"connected": connected, "expires_at": expires_at.isoformat() if expires_at else None}}
#     finally:
#         session.close()

# @router.post("/api/brokers/zerodha/disconnect")
# def disconnect(body: DisconnectIn):
#     session = SessionLocal()
#     try:
#         session.execute(text("""
#             UPDATE broker_connections
#             SET connected = false, access_token = NULL, refresh_token = NULL, expires_at = NULL, updated_at = now()
#             WHERE user_id = :user_id AND broker = 'zerodha'
#         """), {"user_id": body.user_id})
#         session.commit()
#         return {"ok": True}
#     finally:
#         session.close()




# app/api/broker_zerodha.py
import os
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Any, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import httpx
from sqlalchemy import text

# adjust import to your project: SessionLocal should be SQLAlchemy session factory
from app.db import SessionLocal

log = logging.getLogger(__name__)
router = APIRouter()

# env / config
KITE_API_KEY = os.getenv("KITE_API_KEY")
KITE_API_SECRET = os.getenv("KITE_API_SECRET")
KITE_SESSION_URL = os.getenv("KITE_SESSION_URL", "https://api.kite.trade/session/token")
# optional: frontend redirect or your callback url (used only if kiteconnect lib used)
KITE_REDIRECT_URL = os.getenv("KITE_REDIRECT_URL")

# --- request models
class ExchangeIn(BaseModel):
    user_id: int
    request_token: str


class DisconnectIn(BaseModel):
    user_id: int


# --- helper: upsert connection (sync using raw SQL to avoid model dependency)
def upsert_connection_sync(session, user_id: int, access_token: str, refresh_token: Optional[str], expires_at: Optional[datetime]):
    """
    Insert or update broker_connections row for given user.
    Adjust SQL to match your actual schema (column names, table name).
    """
    sql = """
    INSERT INTO broker_connections (user_id, broker, access_token, refresh_token, expires_at, connected, updated_at)
    VALUES (:user_id, 'zerodha', :access_token, :refresh_token, :expires_at, true, now())
    ON CONFLICT (user_id, broker)
    DO UPDATE SET access_token = EXCLUDED.access_token,
                  refresh_token = EXCLUDED.refresh_token,
                  expires_at = EXCLUDED.expires_at,
                  connected = true,
                  updated_at = now();
    """
    session.execute(
        text(sql),
        {"user_id": user_id, "access_token": access_token, "refresh_token": refresh_token, "expires_at": expires_at},
    )
    session.commit()


# --- optional: start endpoint to return Kite login url (requires kiteconnect library and KITE_API_KEY)
try:
    from kiteconnect import KiteConnect  # type: ignore

    _kite_lib_available = True
except Exception:
    _kite_lib_available = False


@router.get("/api/brokers/zerodha/start")
def start_login_url(redirect: Optional[str] = None):
    """
    Optional endpoint: returns Kite login URL for popup.
    Only available if kiteconnect is installed and KITE_API_KEY is configured.
    Frontend can open returned `url` in a popup.
    """
    if not _kite_lib_available or not KITE_API_KEY:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not available (KiteConnect not configured).")
    try:
        kite = KiteConnect(api_key=KITE_API_KEY)
        url = kite.login_url(redirect_url=redirect or KITE_REDIRECT_URL)
        return {"ok": True, "url": url}
    except Exception as e:
        log.exception("start_login_url failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/brokers/zerodha/exchange")
async def exchange_token(payload: ExchangeIn):
    """
    Exchange request_token (from frontend / callback) for access_token via Kite session API.
    - Expects payload: { user_id, request_token }
    - Computes checksum per Kite docs and POSTs to KITE_SESSION_URL
    - Upserts connection into broker_connections
    """
    if not payload.request_token:
        raise HTTPException(status_code=400, detail="missing request_token")
    if not KITE_API_KEY or not KITE_API_SECRET:
        raise HTTPException(status_code=500, detail="Kite API keys not configured on server")

    checksum_source = f"{KITE_API_KEY}{payload.request_token}{KITE_API_SECRET}"
    checksum = hashlib.sha256(checksum_source.encode("utf-8")).hexdigest()
    data = {"api_key": KITE_API_KEY, "request_token": payload.request_token, "checksum": checksum}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(KITE_SESSION_URL, data=data)
    except httpx.RequestError as exc:
        log.exception("HTTPX request error while exchanging token: %s", exc)
        raise HTTPException(status_code=502, detail="Network error contacting Kite session endpoint")

    if resp.status_code != 200:
        log.error("Kite exchange returned non-200: %s %s", resp.status_code, resp.text[:200])
        raise HTTPException(status_code=502, detail=f"Kite exchange failed: {resp.status_code}")

    try:
        j = resp.json()
    except Exception:
        log.exception("Failed to parse Kite response JSON")
        raise HTTPException(status_code=502, detail="Invalid response from Kite")

    # Kite may wrap data in {data: {...}} or return top-level keys
    data_obj: Dict[str, Any] = j.get("data") if isinstance(j, dict) and "data" in j else j

    access_token = data_obj.get("access_token") or data_obj.get("accessToken")
    refresh_token = data_obj.get("refresh_token") or data_obj.get("public_token") or data_obj.get("refreshToken")
    expires_in = data_obj.get("expires_in") or data_obj.get("expiry_in") or 24 * 3600

    if not access_token:
        log.error("Access token missing in Kite response: %s", j)
        raise HTTPException(status_code=502, detail="Access token not present in Kite response")

    try:
        expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
    except Exception:
        expires_at = datetime.utcnow() + timedelta(hours=24)

    # write to DB (synchronous session)
    session = SessionLocal()
    try:
        upsert_connection_sync(session, payload.user_id, access_token, refresh_token, expires_at)
    except Exception:
        log.exception("DB upsert failed for user_id=%s", payload.user_id)
        raise HTTPException(status_code=500, detail="Failed to persist connection")
    finally:
        session.close()

    return {"ok": True, "access_token_present": True, "expires_at": expires_at.isoformat()}


@router.get("/api/brokers/zerodha/status")
def status(user_id: int):
    """
    Return connection status for user_id.
    Query param: ?user_id=123
    """
    session = SessionLocal()
    try:
        row = session.execute(
            text(
                """
            SELECT connected, expires_at
            FROM broker_connections
            WHERE user_id = :user_id AND broker = 'zerodha'
            """
            ),
            {"user_id": user_id},
        ).fetchone()

        if not row:
            return {"ok": True, "status": {"connected": False, "expires_at": None}}

        connected = bool(row[0])
        expires_at = row[1]  # may be None or datetime

        if expires_at and expires_at < datetime.utcnow():
            # expire & clear tokens
            session.execute(
                text(
                    """
                UPDATE broker_connections
                SET connected = false, access_token = NULL, refresh_token = NULL, expires_at = NULL, updated_at = now()
                WHERE user_id = :user_id AND broker = 'zerodha'
                """
                ),
                {"user_id": user_id},
            )
            session.commit()
            return {"ok": True, "status": {"connected": False, "expires_at": None}}

        return {"ok": True, "status": {"connected": connected, "expires_at": expires_at.isoformat() if expires_at else None}}
    except Exception:
        log.exception("status endpoint error for user_id=%s", user_id)
        raise HTTPException(status_code=500, detail="Failed to read status")
    finally:
        session.close()


@router.post("/api/brokers/zerodha/disconnect")
def disconnect(body: DisconnectIn):
    """
    Disconnect broker for user (clears stored tokens).
    """
    session = SessionLocal()
    try:
        session.execute(
            text(
                """
            UPDATE broker_connections
            SET connected = false, access_token = NULL, refresh_token = NULL, expires_at = NULL, updated_at = now()
            WHERE user_id = :user_id AND broker = 'zerodha'
            """
            ),
            {"user_id": body.user_id},
        )
        session.commit()
        return {"ok": True}
    except Exception:
        log.exception("disconnect failed for user_id=%s", body.user_id)
        raise HTTPException(status_code=500, detail="Failed to disconnect")
    finally:
        session.close()
