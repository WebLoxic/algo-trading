# app/api/admin_routes.py
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
import os

from app import models  # models aggregate from app/models/__init__.py
from app.schemas import (
    UserOut, SubscriptionOut, PaymentTransactionOut, CredentialHistoryOut, PaginatedResponse
)

# Try to import get_db & get_current_active_superuser from app.deps
try:
    from app.deps import get_db, get_current_active_superuser
except Exception:
    # fallback if not present - define a simple get_db stub (you should replace with your real one)
    from fastapi import Depends

    def get_db():
        raise RuntimeError("get_db dependency not found. Please provide app.deps.get_db")

    def get_current_active_superuser():
        # if you don't have superuser logic yet, raise or return None.
        raise RuntimeError("get_current_active_superuser not found; protect admin endpoints in production.")

router = APIRouter(prefix="/admin", tags=["admin"])


# Helper: generic pagination
def _paginate_query(q, db: Session, skip: int, limit: int):
    total = q.order_by(None).count()
    items = q.offset(skip).limit(limit).all()
    return total, items


# ----------------
# Users endpoints
# ----------------
@router.get("/users", response_model=PaginatedResponse)
def admin_list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=500),
    q: Optional[str] = Query(None, description="search by name or email"),
    db: Session = Depends(get_db),
    _admin = Depends(get_current_active_superuser),
):
    query = db.query(models.User)
    if q:
        like_q = f"%{q}%"
        query = query.filter(or_(models.User.full_name.ilike(like_q), models.User.email.ilike(like_q)))
    query = query.order_by(desc(models.User.created_at))
    total, items = _paginate_query(query, db, skip, limit)
    return {"total": total, "skip": skip, "limit": limit, "items": items}


@router.get("/users/{user_id}", response_model=UserOut)
def admin_get_user(user_id: int, db: Session = Depends(get_db), _admin = Depends(get_current_active_superuser)):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(404, "user not found")
    return u


# ----------------
# Subscriptions
# ----------------
@router.get("/subscriptions", response_model=PaginatedResponse)
def admin_list_subscriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=500),
    user_id: Optional[int] = None,
    active: Optional[bool] = None,
    db: Session = Depends(get_db),
    _admin = Depends(get_current_active_superuser),
):
    q = db.query(models.Subscription)
    if user_id:
        q = q.filter(models.Subscription.user_id == user_id)
    if active is not None:
        q = q.filter(models.Subscription.is_active == active)
    q = q.order_by(desc(models.Subscription.created_at))
    total, items = _paginate_query(q, db, skip, limit)
    return {"total": total, "skip": skip, "limit": limit, "items": items}


# ----------------
# Payments
# ----------------
@router.get("/payments", response_model=PaginatedResponse)
def admin_list_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=500),
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin = Depends(get_current_active_superuser),
):
    q = db.query(models.PaymentTransaction)
    if user_id:
        q = q.filter(models.PaymentTransaction.user_id == user_id)
    if status:
        q = q.filter(models.PaymentTransaction.status.ilike(f"%{status}%"))
    q = q.order_by(desc(models.PaymentTransaction.created_at))
    total, items = _paginate_query(q, db, skip, limit)
    return {"total": total, "skip": skip, "limit": limit, "items": items}


# ----------------
# Credential history
# ----------------
@router.get("/credentials/history", response_model=PaginatedResponse)
def admin_credential_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=1000),
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin = Depends(get_current_active_superuser),
):
    q = db.query(models.CredentialHistory)
    if user_id:
        q = q.filter(models.CredentialHistory.user_id == user_id)
    if action:
        q = q.filter(models.CredentialHistory.action.ilike(f"%{action}%"))
    q = q.order_by(desc(models.CredentialHistory.created_at))
    total, items = _paginate_query(q, db, skip, limit)
    return {"total": total, "skip": skip, "limit": limit, "items": items}


# ----------------
# Quick stats
# ----------------
@router.get("/stats")
def admin_stats(db: Session = Depends(get_db), _admin = Depends(get_current_active_superuser)):
    users_count = db.query(func.count(models.User.id)).scalar()
    active_subs = db.query(func.count(models.Subscription.id)).filter(models.Subscription.is_active == True).scalar()
    total_payments = db.query(func.sum(models.PaymentTransaction.amount)).scalar() or 0
    recent_activities = db.query(models.CredentialHistory).order_by(desc(models.CredentialHistory.created_at)).limit(10).all()
    return {
        "users_count": users_count,
        "active_subscriptions": active_subs,
        "total_payments_amount": float(total_payments),
        "recent_credential_history": recent_activities,
    }
