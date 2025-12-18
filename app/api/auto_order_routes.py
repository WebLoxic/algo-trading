from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy import text
from app.db import SessionLocal
from app.main import get_current_user_row

router = APIRouter(prefix="/auto-order", tags=["AutoOrder"])

# ----------------------
# Pydantic Schemas
# ----------------------
class AutoOrderSettingsIn(BaseModel):
    enabled: bool
    default_sl_pct: float
    default_tp_pct: float
    slippage_pct: float
    transaction_cost: float

class AutoOrderSettingsOut(AutoOrderSettingsIn):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

class AutoOrderAuditOut(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: int
    price: float
    sl: Optional[float]
    tp: Optional[float]
    status: str
    executed_at: datetime


# ----------------------
# CRUD: Settings
# ----------------------
@router.get("/settings", response_model=AutoOrderSettingsOut)
def get_auto_order_settings(user=Depends(get_current_user_row)):
    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT * FROM auto_order_settings WHERE user_id=:uid"),
            {"uid": user["id"]}
        ).first()
        if row:
            return dict(row._mapping)
        else:
            # Default empty settings
            return {
                "id": 0,
                "user_id": user["id"],
                "enabled": False,
                "default_sl_pct": 1.0,
                "default_tp_pct": 2.0,
                "slippage_pct": 0.05,
                "transaction_cost": 0.1,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
    finally:
        db.close()


@router.post("/settings", response_model=AutoOrderSettingsOut)
def update_auto_order_settings(payload: AutoOrderSettingsIn, user=Depends(get_current_user_row)):
    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT * FROM auto_order_settings WHERE user_id=:uid"),
            {"uid": user["id"]}
        ).first()

        if row:
            db.execute(
                text("""
                    UPDATE auto_order_settings
                    SET enabled=:enabled,
                        default_sl_pct=:sl,
                        default_tp_pct=:tp,
                        slippage_pct=:slip,
                        transaction_cost=:tc,
                        updated_at=NOW()
                    WHERE user_id=:uid
                """),
                {
                    "enabled": payload.enabled,
                    "sl": payload.default_sl_pct,
                    "tp": payload.default_tp_pct,
                    "slip": payload.slippage_pct,
                    "tc": payload.transaction_cost,
                    "uid": user["id"]
                }
            )
        else:
            db.execute(
                text("""
                    INSERT INTO auto_order_settings
                    (user_id, enabled, default_sl_pct, default_tp_pct, slippage_pct, transaction_cost)
                    VALUES
                    (:uid, :enabled, :sl, :tp, :slip, :tc)
                """),
                {
                    "uid": user["id"],
                    "enabled": payload.enabled,
                    "sl": payload.default_sl_pct,
                    "tp": payload.default_tp_pct,
                    "slip": payload.slippage_pct,
                    "tc": payload.transaction_cost
                }
            )
        db.commit()
        return get_auto_order_settings(user)
    finally:
        db.close()


# ----------------------
# CRUD: Audit Logs
# ----------------------
@router.get("/audit", response_model=List[AutoOrderAuditOut])
def get_auto_order_audit(user=Depends(get_current_user_row)):
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT *
                FROM auto_order_audit
                WHERE user_id=:uid
                ORDER BY executed_at DESC
                LIMIT 100
            """),
            {"uid": user["id"]}
        ).fetchall()

        return [AutoOrderAuditOut(**dict(r._mapping)) for r in rows]
    finally:
        db.close()
