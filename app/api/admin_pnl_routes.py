from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from pydantic import BaseModel
from typing import List

from app.db import SessionLocal
from app.main import get_current_user_row

router = APIRouter(
    prefix="/admin/pnl",
    tags=["Admin-PnL"]
)

# =====================================================
# 🔐 ADMIN GUARD
# =====================================================
def admin_only(user: dict):
    if not user or not user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Admin access required")


# =====================================================
# 📦 RESPONSE SCHEMAS
# =====================================================
class PnlSummaryOut(BaseModel):
    realized_pnl: float
    unrealized_pnl: float
    net_pnl: float
    active_positions: int
    total_orders: int
    total_users: int


class UserPnlOut(BaseModel):
    user_id: int
    realized_pnl: float
    unrealized_pnl: float
    net_pnl: float


class SymbolPnlOut(BaseModel):
    symbol: str
    realized_pnl: float
    unrealized_pnl: float


# =====================================================
# 1️⃣ OVERALL PnL SUMMARY
# =====================================================
@router.get("/summary", response_model=PnlSummaryOut)
def pnl_summary(user=Depends(get_current_user_row)):
    admin_only(user)
    db = SessionLocal()
    try:
        realized = db.execute(text("""
            SELECT COALESCE(SUM(realized_pnl), 0)
            FROM position_history
        """)).scalar()

        unrealized = db.execute(text("""
            SELECT COALESCE(SUM(pnl), 0)
            FROM positions
        """)).scalar()

        total_users = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
        total_orders = db.execute(text("SELECT COUNT(*) FROM orders")).scalar()
        active_positions = db.execute(text("SELECT COUNT(*) FROM positions")).scalar()

        return {
            "realized_pnl": float(realized),
            "unrealized_pnl": float(unrealized),
            "net_pnl": float(realized + unrealized),
            "active_positions": int(active_positions),
            "total_orders": int(total_orders),
            "total_users": int(total_users),
        }
    finally:
        db.close()


# =====================================================
# 2️⃣ USER-WISE PnL
# =====================================================
@router.get("/users", response_model=List[UserPnlOut])
def pnl_by_users(user=Depends(get_current_user_row)):
    admin_only(user)
    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT
                u.id AS user_id,
                COALESCE(SUM(ph.realized_pnl), 0) AS realized,
                COALESCE(SUM(p.pnl), 0) AS unrealized
            FROM users u
            LEFT JOIN position_history ph ON ph.user_id = u.id
            LEFT JOIN positions p ON p.user_id = u.id
            GROUP BY u.id
            ORDER BY u.id
        """)).fetchall()

        return [
            {
                "user_id": r.user_id,
                "realized_pnl": float(r.realized),
                "unrealized_pnl": float(r.unrealized),
                "net_pnl": float(r.realized + r.unrealized),
            }
            for r in rows
        ]
    finally:
        db.close()


# =====================================================
# 3️⃣ SYMBOL-WISE PnL
# =====================================================
@router.get("/symbols", response_model=List[SymbolPnlOut])
def pnl_by_symbol(user=Depends(get_current_user_row)):
    admin_only(user)
    db = SessionLocal()
    try:
        realized_rows = db.execute(text("""
            SELECT symbol, COALESCE(SUM(realized_pnl), 0) AS realized
            FROM position_history
            GROUP BY symbol
        """)).fetchall()

        unrealized_rows = db.execute(text("""
            SELECT symbol, COALESCE(SUM(pnl), 0) AS unrealized
            FROM positions
            GROUP BY symbol
        """)).fetchall()

        unreal_map = {r.symbol: r.unrealized for r in unrealized_rows}

        symbols = set(unreal_map.keys()) | {r.symbol for r in realized_rows}

        realized_map = {r.symbol: r.realized for r in realized_rows}

        return [
            {
                "symbol": sym,
                "realized_pnl": float(realized_map.get(sym, 0)),
                "unrealized_pnl": float(unreal_map.get(sym, 0)),
            }
            for sym in sorted(symbols)
        ]
    finally:
        db.close()
