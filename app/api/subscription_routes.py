
# -----------------------------------------------------------
# app/api/subscription_routes.py
# FINAL, CLEAN, FULLY COMPATIBLE WITH NEW CRUD + FRONTEND
# Proper session handling to ensure subscriptions persist
# -----------------------------------------------------------

from typing import Optional, Dict, Any, List
import os
import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app import crud

logger = logging.getLogger("app.subscription_routes")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

router = APIRouter(prefix="", tags=["subscriptions"])

# JWT Settings
JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "super_secret_key"))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")
# /api/subscriptions

# --------------------------------------------------------
# Decode JWT + fetch user
# --------------------------------------------------------
def _fetch_user(sub: Optional[str], uid_claim: Optional[int]):
    session = SessionLocal()
    try:
        if uid_claim:
            row = session.execute(
                "SELECT id, email, full_name, is_active, is_superuser FROM users WHERE id=:id LIMIT 1",
                {"id": uid_claim}
            ).first()
            if row:
                return row
        if sub:
            row = session.execute(
                "SELECT id, email, full_name, is_active, is_superuser FROM users WHERE email=:e LIMIT 1",
                {"e": sub}
            ).first()
            if row:
                return row
        return None
    finally:
        session.close()


# def get_current_user_row(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
#     try:
#         payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
#     except JWTError:
#         raise HTTPException(401, "Invalid token")

#     row = _fetch_user(payload.get("sub"), payload.get("uid"))
#     if not row:
#         raise HTTPException(401, "User not found")
#     try:
#         return dict(row._mapping)
#     except Exception:
#         try:
#             return dict(row)
#         except Exception:
#             raise HTTPException(500, "Failed to read user row")


def get_current_user_row(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    print("\n🔥 Incoming Token From Header:", token)
    print ("JWT_SECRET",JWT_SECRET)

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        print("Decoded Payload:", payload)
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")

    sub = payload.get("sub")
    uid = payload.get("uid")

    if not sub or not uid:
        raise HTTPException(401, "Invalid token payload")

    row = _fetch_user(sub, uid)
    if not row:
        raise HTTPException(401, "User not found")

    # Normalize row -> dict
    try:
        return dict(row._mapping)
    except:
        try:
            return dict(row)
        except:
            try:
                return row.__dict__
            except:
                raise HTTPException(500, "Failed to read user row")
# --------------------------------------------------------
# Request Models
# --------------------------------------------------------
class PurchaseRequest(BaseModel):
    plan_id: int
    billing_cycle: str  # monthly | yearly
    meta: Optional[Dict[str, Any]] = None


class CompleteRequest(BaseModel):
    subscription_id: int
    payment_id: str
    provider: Optional[str] = "razorpay"
    provider_payload: Optional[Dict[str, Any]] = None


# --------------------------------------------------------
# Helper to normalize rows -> dict
# --------------------------------------------------------
def _row_to_dict(r):
    if r is None:
        return None
    if isinstance(r, dict):
        return r
    if hasattr(r, "_mapping"):
        return dict(r._mapping)
    if hasattr(r, "__dict__") and hasattr(r, "id"):
        return {k: v for k, v in vars(r).items() if not k.startswith("_")}
    try:
        return dict(r)
    except Exception:
        return {"value": str(r)}


# -----------------------------
# USER ENDPOINTS
# -----------------------------
@router.get("/me")
def my_subscriptions(user=Depends(get_current_user_row)):
    db = SessionLocal()
    try:
        subs = crud.get_all_subscriptions(user_id=user["id"], db=db)
        return [_row_to_dict(s) for s in subs]
    finally:
        db.close()


@router.post("/purchase")
def purchase_subscription(payload: PurchaseRequest, user=Depends(get_current_user_row)):
    db = SessionLocal()
    try:
        billing = payload.billing_cycle.lower()
        if billing not in ("monthly", "yearly"):
            raise HTTPException(400, "Billing must be monthly or yearly")

        # Create pending subscription with proper commit
        sub = crud.create_pending_subscription(
            user_id=user["id"],
            plan_id=payload.plan_id,
            billing_cycle=billing,
            meta=payload.meta or {},
            db=db
        )
        db.commit()
        db.refresh(sub)
        return {"subscription_id": sub.id, "message": "pending", "status": "pending"}
    except Exception as e:
        db.rollback()
        logger.exception("Failed to create pending subscription for user=%s: %s", user.get("id"), e)
        raise HTTPException(500, "Failed to create pending subscription")
    finally:
        db.close()


@router.post("/complete")
def complete_subscription(payload: CompleteRequest, user=Depends(get_current_user_row)):
    db = SessionLocal()
    try:
        activated = crud.activate_subscription(
            subscription_id=payload.subscription_id,
            payment_id=payload.payment_id,
            provider=payload.provider,
            provider_payload=payload.provider_payload,
            db=db
        )
        if not activated:
            raise HTTPException(400, "Activation failed")
        db.commit()
        db.refresh(activated)
        return _row_to_dict(activated)
    except Exception as e:
        db.rollback()
        logger.exception("Activation error for sub=%s user=%s: %s", payload.subscription_id, user.get("id"), e)
        raise HTTPException(500, "Activation failed")
    finally:
        db.close()


# -----------------------------
# ADMIN ENDPOINTS
# -----------------------------
@router.get("/admin/all")
def admin_list(status: Optional[str] = None, user=Depends(get_current_user_row)):
    if not user.get("is_superuser"):
        raise HTTPException(403, "Admins only")
    db = SessionLocal()
    try:
        subs = crud.admin_list_subscriptions(status=status, db=db)
        return [_row_to_dict(s) for s in subs]
    finally:
        db.close()


@router.post("/admin/cancel/{subscription_id}")
def admin_cancel(subscription_id: int, note: Optional[str] = None, user=Depends(get_current_user_row)):
    if not user.get("is_superuser"):
        raise HTTPException(403, "Admins only")
    db = SessionLocal()
    try:
        sub = crud.cancel_subscription(subscription_id, admin_note=note, db=db)
        if not sub:
            raise HTTPException(404, "Subscription not found")
        db.commit()
        db.refresh(sub)
        return _row_to_dict(sub)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()







