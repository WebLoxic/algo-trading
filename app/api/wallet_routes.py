

# ================================================================
# app/api/wallet_routes.py  (UPDATED)
# ================================================================
import os
import json
import logging
import hmac
import hashlib
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.wallet_model import (
    WalletBalance,
    WalletTransaction,
    OpenPosition,
    TradeHistory,
)

# Broadcast helper from main (sync wrapper)
try:
    from app.main import broadcast_signal_sync
except Exception:
    # if import fails, define a no-op to avoid crashing — logs will show broadcast not available
    def broadcast_signal_sync(payload):
        logging.getLogger("wallet").debug("broadcast_signal_sync not available: %s", payload)
        return

log = logging.getLogger("wallet")
router = APIRouter(prefix="/wallet", tags=["wallet"])

# -------------------------------------------------------------------
# Razorpay setup
# -------------------------------------------------------------------
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
razorpay_client = None

if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    try:
        import razorpay
        razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        log.info("Razorpay initialized")
    except Exception as e:
        log.error("Razorpay init failed: %s", e)


# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------
def round2(v):
    try:
        return float(round(float(v), 2))
    except:
        return 0.0


def get_wallet(db: Session, email: str) -> WalletBalance:
    """
    Return WalletBalance object for email. If not exists, CREATE (but do not commit).
    Callers should commit the session when they want to persist.
    """
    w = db.query(WalletBalance).filter(WalletBalance.user_email == email).first()
    if not w:
        w = WalletBalance(user_email=email, balance=0.0, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        db.add(w)
        # flush so w.id is available without committing
        try:
            db.flush()
            db.refresh(w)
        except Exception:
            # if flush/refresh fails for some reason, continue and let caller handle commit/rollback
            log.exception("get_wallet: flush/refresh failed for %s", email)
    return w


# WalletTransaction safe insert (avoids missing columns)
def safe_txn(**kwargs):
    allowed = {c.name for c in WalletTransaction.__table__.columns}
    # ensure we always pass a currency if the model expects it
    out = {k: v for k, v in kwargs.items() if k in allowed}
    return out


# -------------------------------------------------------------------
# Pydantic Response Models
# -------------------------------------------------------------------
class TransactionOut(BaseModel):
    id: int
    user_email: Optional[str] = None
    amount: float
    status: str
    note: Optional[str] = None
    order_id: Optional[str] = None
    payment_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# -------------------------------------------------------------------
# WALLET BASIC API
# -------------------------------------------------------------------
@router.get("/balance/{email}")
def get_balance(email: str, db: Session = Depends(get_db)):
    w = get_wallet(db, email)
    # don't auto-commit here — just return current value
    return {"email": email, "balance": float(w.balance)}


@router.get("/transactions/{email}", response_model=List[TransactionOut])
def get_transactions(email: str, db: Session = Depends(get_db)):
    tx = (
        db.query(WalletTransaction)
        .filter(WalletTransaction.user_email == email)
        .order_by(WalletTransaction.id.desc())
        .limit(100)
        .all()
    )
    return tx


# -------------------------------------------------------------------
# Deposit / Add Funds
# -------------------------------------------------------------------
@router.post("/deposit")
def deposit_funds(payload: dict = Body(...), db: Session = Depends(get_db)):
    """
    Deposit funds into wallet.
    payload: {"email": "...", "amount": 50000, "note": "optional"}
    """
    email = payload.get("email")
    amount = payload.get("amount", 0)
    note = payload.get("note", None)

    if not email or amount is None:
        raise HTTPException(status_code=400, detail="email and amount required")

    try:
        amount = float(amount)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid amount")

    if amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be > 0")

    try:
        w = get_wallet(db, email)
        # credit wallet
        w.balance = round2(w.balance + amount)
        w.updated_at = datetime.utcnow()
        db.add(w)

        # Wallet transaction record (attach wallet_id if present)
        txn_data = safe_txn(
            user_email=email,
            wallet_id=getattr(w, "id", None),
            amount=round2(amount),
            status="success",
            provider="razorpay" if razorpay_client else "internal",
            currency="INR",
            order_id=f"deposit_{uuid.uuid4().hex[:10]}",
            note=note or f"Deposit via API at {datetime.utcnow().isoformat()}",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        txn = WalletTransaction(**txn_data)
        db.add(txn)

        db.commit()
        db.refresh(txn)

        # Broadcast wallet update so dashboards update in real-time
        try:
            broadcast_signal_sync({
                "type": "wallet_update",
                "email": email,
                "balance": float(w.balance),
                "timestamp": datetime.utcnow().isoformat(),
            })
            log.info("Broadcasted wallet_update for %s (deposit)", email)
        except Exception as e:
            log.exception("Failed to broadcast wallet_update (deposit): %s", e)

        return {"ok": True, "email": email, "balance": float(w.balance), "txn_id": txn.id}
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        log.exception("DEPOSIT ERROR: %s", e)
        raise HTTPException(status_code=500, detail="Deposit failed")


# -------------------------------------------------------------------
# Create order (Razorpay) - frontend calls this before opening checkout
# -------------------------------------------------------------------
@router.post("/create-order")
def create_order_handler(payload: dict = Body(...), db: Session = Depends(get_db)):
    """
    Create an order for Razorpay (or return a fallback fake order in dev).
    Expected payload: {"email": "...", "amount": 1000}
    Returns: {"ok": True, "order_id": "...", "amount": amount_in_paise, "currency":"INR", "razorpay_key": "..." }
    Also records a pending WalletTransaction so verify can find it later.
    """
    email = payload.get("email")
    amount = payload.get("amount")

    if not email or amount is None:
        raise HTTPException(status_code=400, detail="email and amount required")

    try:
        amt_float = float(amount)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid amount")

    if amt_float <= 0:
        raise HTTPException(status_code=400, detail="amount must be > 0")

    amount_paise = int(round(amt_float * 100))

    try:
        # Create real Razorpay order if client configured
        if razorpay_client:
            order_payload = {
                "amount": amount_paise,
                "currency": "INR",
                "receipt": f"rcpt_{uuid.uuid4().hex[:10]}",
                "payment_capture": 1,
            }
            order = razorpay_client.order.create(order_payload)
            order_id = order.get("id")
            order_amount = int(order.get("amount", amount_paise))
            currency = order.get("currency", "INR")
            log.info("Razorpay order created %s for %s", order_id, email)
        else:
            # Dev fallback
            order_id = f"dev_order_{uuid.uuid4().hex[:10]}"
            order_amount = amount_paise
            currency = "INR"
            log.info("Dev order created %s for %s", order_id, email)

        # Attempt to attach wallet_id if wallet exists (do NOT create wallet here)
        existing_wallet = db.query(WalletBalance).filter(WalletBalance.user_email == email).first()
        wallet_id = existing_wallet.id if existing_wallet else None

        # Record a pending transaction (amount stored in rupees)
        txn_data = safe_txn(
            user_email=email,
            wallet_id=wallet_id,
            amount=round2(amt_float),
            status="pending",
            provider="razorpay" if razorpay_client else "dev",
            currency="INR",
            order_id=order_id,
            note=f"Razorpay order created ({order_id})",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        txn = WalletTransaction(**txn_data)
        db.add(txn)
        db.commit()
        db.refresh(txn)

        return {
            "ok": True,
            "order_id": order_id,
            "amount": order_amount,  # paise
            "currency": currency,
            "razorpay_key": RAZORPAY_KEY_ID or "",
            "txn_id": txn.id,
        }
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        log.exception("create_order_handler failed: %s", e)
        raise HTTPException(status_code=500, detail="Order creation failed")


# -------------------------------------------------------------------
# Verify payment (called by frontend handler after Razorpay checkout)
# -------------------------------------------------------------------
@router.post("/verify")
def verify_payment(payload: dict = Body(...), db: Session = Depends(get_db)):
    """
    Verify razorpay signature and credit wallet.
    Expected payload: { "email": "...", "order_id": "...", "payment_id": "...", "signature": "..." }
    """
    email = payload.get("email")
    order_id = payload.get("order_id") or payload.get("razorpay_order_id")
    payment_id = payload.get("payment_id") or payload.get("razorpay_payment_id")
    signature = payload.get("signature") or payload.get("razorpay_signature")

    if not email or not order_id or not payment_id or not signature:
        raise HTTPException(status_code=400, detail="email, order_id, payment_id and signature required")

    # Try to find the pending tx created during create_order
    txn = db.query(WalletTransaction).filter(
        WalletTransaction.order_id == order_id,
        WalletTransaction.user_email == email,
        WalletTransaction.status == "pending"
    ).order_by(WalletTransaction.id.desc()).first()

    # If we have Razorpay secret, validate HMAC signature
    valid = False
    if RAZORPAY_KEY_SECRET:
        try:
            msg = f"{order_id}|{payment_id}".encode()
            expected = hmac.new(RAZORPAY_KEY_SECRET.encode(), msg, hashlib.sha256).hexdigest()
            valid = expected == signature
        except Exception as e:
            log.exception("Signature validate failed: %s", e)
            valid = False
    else:
        # no secret configured => in dev accept (but log)
        log.warning("RAZORPAY_KEY_SECRET not configured — skipping signature check (dev mode)")
        valid = True

    if not valid:
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        # Determine amount in rupees to credit
        amt_rupees = None
        if txn:
            amt_rupees = float(txn.amount)
        else:
            # fallback: try to fetch order from razorpay_client if configured, else fail
            if razorpay_client:
                try:
                    order = razorpay_client.order.fetch(order_id)
                    amt_rupees = float(order.get("amount", 0)) / 100.0
                except Exception as e:
                    log.exception("Failed fetching order from razorpay: %s", e)
                    amt_rupees = None
            else:
                # no txn and no razorpay_client -> cannot determine amount reliably
                log.warning("verify_payment: no pending txn found and no razorpay_client — cannot get amount; will fail")
                raise HTTPException(status_code=400, detail="No pending transaction found for order and cannot determine amount")

        if amt_rupees is None:
            raise HTTPException(status_code=400, detail="Amount determination failed")

        # If txn exists, mark success and attach payment_id
        if txn:
            txn.status = "success"
            txn.payment_id = payment_id
            txn.updated_at = datetime.utcnow()
            db.add(txn)
        else:
            # create a success transaction record
            txn_data = safe_txn(
                user_email=email,
                amount=round2(amt_rupees),
                status="success",
                provider="razorpay" if razorpay_client else "dev",
                currency="INR",
                order_id=order_id,
                payment_id=payment_id,
                note=f"Razorpay payment {payment_id} (verify fallback)",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            txn = WalletTransaction(**txn_data)
            db.add(txn)

        # Credit wallet
        w = get_wallet(db, email)
        w.balance = round2(w.balance + amt_rupees)
        w.updated_at = datetime.utcnow()
        db.add(w)

        db.commit()
        try:
            db.refresh(txn)
        except Exception:
            pass

        # Broadcast wallet update so frontends update
        try:
            broadcast_signal_sync({
                "type": "wallet_update",
                "email": email,
                "balance": float(w.balance),
                "timestamp": datetime.utcnow().isoformat(),
            })
            log.info("Broadcasted wallet_update for %s (verify)", email)
        except Exception as e:
            log.exception("Failed to broadcast wallet_update (verify): %s", e)

        return {"ok": True, "balance": float(w.balance), "txn_id": getattr(txn, "id", None)}
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        log.exception("verify_payment error: %s", e)
        raise HTTPException(status_code=500, detail="Payment verification failed")


# -------------------------------------------------------------------
# Trading Schemas / BUY / SELL flows (unchanged, minor safety)
# -------------------------------------------------------------------
class TradeBuyIn(BaseModel):
    email: str
    symbol: str
    amount: float
    executed_price: float
    note: Optional[str] = None


class TradeSellIn(BaseModel):
    email: str
    symbol: str
    sell_qty: Optional[float] = None
    sell_amount: Optional[float] = None
    executed_price: float
    require_full_quantity: Optional[bool] = True
    note: Optional[str] = None


@router.post("/trade/buy")
def trade_buy(data: TradeBuyIn, db: Session = Depends(get_db)):
    if data.amount <= 0 or data.executed_price <= 0:
        raise HTTPException(400, "Invalid amount or executed price")

    w = get_wallet(db, data.email)

    if w.balance < data.amount:
        raise HTTPException(status_code=400, detail=json.dumps({
            "error": "Insufficient wallet balance",
            "balance": float(w.balance),
            "required": float(data.amount)
        }))

    qty = round2(data.amount / data.executed_price)

    try:
        # Debit wallet
        w.balance = round2(w.balance - data.amount)
        w.updated_at = datetime.utcnow()
        db.add(w)

        # Wallet transaction
        txn_data = safe_txn(
            user_email=data.email,
            wallet_id=getattr(w, "id", None),
            amount=-abs(round2(data.amount)),
            status="success",
            provider="internal",
            currency="INR",
            order_id=f"buy_{uuid.uuid4().hex[:10]}",
            note=f"Buy {data.symbol} at {data.executed_price}",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        txn = WalletTransaction(**txn_data)
        db.add(txn)

        # Open Position
        pos = OpenPosition(
            user_email=data.email,
            symbol=data.symbol,
            qty=qty,
            remaining_qty=qty,
            entry_price=round2(data.executed_price),
            amount=round2(data.amount),
            status="open",
            note=data.note,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(pos)

        db.commit()
        db.refresh(txn)
        db.refresh(pos)

        # Broadcast wallet update so dashboards show new balance
        try:
            broadcast_signal_sync({
                "type": "wallet_update",
                "email": data.email,
                "balance": float(w.balance),
                "timestamp": datetime.utcnow().isoformat(),
            })
            log.info("Broadcasted wallet_update for %s (buy)", data.email)
        except Exception as e:
            log.exception("Failed to broadcast wallet_update (buy): %s", e)

        return {
            "ok": True,
            "position": {
                "id": pos.id,
                "symbol": pos.symbol,
                "qty": pos.qty,
                "entry_price": pos.entry_price,
            },
            "balance": float(w.balance),
        }

    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        log.exception("BUY ERROR: %s", e)
        raise HTTPException(500, "Buy order failed")


@router.post("/trade/sell")
def trade_sell(data: TradeSellIn, db: Session = Depends(get_db)):
    if data.executed_price <= 0:
        raise HTTPException(400, "Invalid executed_price")

    if data.sell_qty:
        sell_qty = float(data.sell_qty)
    elif data.sell_amount:
        sell_qty = float(data.sell_amount) / float(data.executed_price)
    else:
        raise HTTPException(400, "sell_qty or sell_amount required")

    if sell_qty <= 0:
        raise HTTPException(400, "sell_qty invalid")

    positions = (
        db.query(OpenPosition)
        .filter(
            OpenPosition.user_email == data.email,
            OpenPosition.symbol == data.symbol,
            OpenPosition.remaining_qty > 0,
        )
        .order_by(OpenPosition.created_at.asc())
        .all()
    )

    available_qty = sum(p.remaining_qty for p in positions)
    if available_qty == 0:
        raise HTTPException(400, "No open positions for this symbol")

    if sell_qty > available_qty and data.require_full_quantity:
        raise HTTPException(400, f"Trying to sell {sell_qty} but only {available_qty} available")

    qty_to_close = min(sell_qty, available_qty)

    total_cost = 0.0
    total_sell = 0.0
    close_details = []
    remaining = qty_to_close

    try:
        for p in positions:
            if remaining <= 0:
                break

            chunk = min(p.remaining_qty, remaining)

            cost = chunk * p.entry_price
            sell_val = chunk * data.executed_price

            total_cost += cost
            total_sell += sell_val

            close_details.append({
                "pos_id": p.id,
                "closed_qty": round2(chunk),
                "entry_price": round2(p.entry_price)
            })

            p.remaining_qty = round2(p.remaining_qty - chunk)
            p.status = "closed" if p.remaining_qty == 0 else "partial"
            p.updated_at = datetime.utcnow()
            db.add(p)

            remaining -= chunk

        pnl = round2(total_sell - total_cost)

        # Trade history
        th = TradeHistory(
            user_email=data.email,
            symbol=data.symbol,
            sell_qty=round2(qty_to_close),
            sell_price=round2(data.executed_price),
            gross_proceeds=round2(total_sell),
            cost_basis=round2(total_cost),
            realized_pnl=pnl,
            position_ids=close_details,
            note=data.note,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(th)

        # CREDIT wallet
        w = get_wallet(db, data.email)
        w.balance = round2(w.balance + total_sell)
        w.updated_at = datetime.utcnow()
        db.add(w)

        # Wallet credit transaction
        txn_data = safe_txn(
            user_email=data.email,
            wallet_id=getattr(w, "id", None),
            amount=round2(total_sell),
            status="success",
            provider="internal",
            currency="INR",
            order_id=f"sell_{uuid.uuid4().hex[:10]}",
            note=f"Sell {data.symbol} at {data.executed_price}",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        txn = WalletTransaction(**txn_data)
        db.add(txn)

        db.commit()
        db.refresh(th)
        db.refresh(txn)

        # Broadcast wallet update so dashboards show new balance
        try:
            broadcast_signal_sync({
                "type": "wallet_update",
                "email": data.email,
                "balance": float(w.balance),
                "timestamp": datetime.utcnow().isoformat(),
            })
            log.info("Broadcasted wallet_update for %s (sell)", data.email)
        except Exception as e:
            log.exception("Failed to broadcast wallet_update (sell): %s", e)

        return {
            "ok": True,
            "sell_qty": round2(qty_to_close),
            "gross_proceeds": round2(total_sell),
            "pnl": pnl,
            "balance": float(w.balance),
        }

    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        log.exception("SELL ERROR: %s", e)
        raise HTTPException(500, "Sell order failed")
