# # app/models/wallet_utils.py
# from typing import Optional, Dict, Any, List
# from decimal import Decimal, ROUND_HALF_UP
# from datetime import datetime
# import logging

# from sqlalchemy.orm import Session
# from sqlalchemy import select, update

# from app.models.wallet_model import WalletBalance, WalletTransaction
# # if you used RefundRequest, you can import it too:
# # from app.models.wallet_model import RefundRequest

# log = logging.getLogger(__name__)


# def _to_two_decimals(value: float) -> float:
#     """Normalize floats to 2 decimal places (money)."""
#     return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# def get_or_create_balance(db: Session, user_email: str) -> WalletBalance:
#     """
#     Return WalletBalance for user_email, creating the row if missing.
#     Commits the new row so caller can immediately use it.
#     """
#     bal = db.execute(select(WalletBalance).where(WalletBalance.user_email == user_email)).scalar_one_or_none()
#     if bal is None:
#         bal = WalletBalance(user_email=user_email, balance=0.0, updated_at=datetime.utcnow())
#         db.add(bal)
#         db.commit()
#         db.refresh(bal)
#     return bal


# def get_balance(db: Session, user_email: str) -> float:
#     """Return current balance (float)."""
#     bal = db.execute(select(WalletBalance).where(WalletBalance.user_email == user_email)).scalar_one_or_none()
#     return _to_two_decimals(bal.balance) if bal else 0.0


# def create_transaction(
#     db: Session,
#     user_email: str,
#     order_id: str,
#     amount: float,
#     currency: str = "INR",
#     provider: str = "razorpay",
#     note: Optional[str] = None,
#     status: str = "pending",
# ) -> WalletTransaction:
#     """
#     Create a WalletTransaction row (pending by default).
#     Returns the created WalletTransaction instance.
#     """
#     txn = WalletTransaction(
#         user_email=user_email,
#         order_id=order_id,
#         payment_id=None,
#         amount=_to_two_decimals(amount),
#         currency=currency,
#         status=status,
#         provider=provider,
#         note=note,
#         created_at=datetime.utcnow(),
#         updated_at=datetime.utcnow(),
#     )
#     db.add(txn)
#     db.commit()
#     db.refresh(txn)
#     return txn


# def mark_transaction_success(db: Session, order_id: str, payment_id: Optional[str] = None, amount: Optional[float] = None) -> Optional[WalletTransaction]:
#     """
#     Mark a transaction as success and credit the user's wallet balance.
#     Returns the updated transaction or None if not found.
#     This function commits changes.
#     """
#     txn = db.execute(select(WalletTransaction).where(WalletTransaction.order_id == order_id)).scalar_one_or_none()
#     if not txn:
#         log.warning("mark_transaction_success: txn not found for order_id=%s", order_id)
#         return None

#     try:
#         # update txn
#         txn.status = "success"
#         if payment_id:
#             txn.payment_id = payment_id
#         if amount is not None:
#             txn.amount = _to_two_decimals(amount)
#         txn.updated_at = datetime.utcnow()
#         db.add(txn)

#         # credit wallet
#         bal = get_or_create_balance(db, txn.user_email)
#         bal.balance = _to_two_decimals((bal.balance or 0.0) + float(txn.amount))
#         bal.updated_at = datetime.utcnow()
#         db.add(bal)

#         db.commit()
#         db.refresh(txn)
#         return txn
#     except Exception:
#         db.rollback()
#         log.exception("Failed to mark transaction success for order_id=%s", order_id)
#         raise


# def mark_transaction_failed(db: Session, order_id: str, payment_id: Optional[str] = None, reason: Optional[str] = None) -> Optional[WalletTransaction]:
#     """
#     Mark a transaction as failed. Commits the change.
#     """
#     txn = db.execute(select(WalletTransaction).where(WalletTransaction.order_id == order_id)).scalar_one_or_none()
#     if not txn:
#         log.warning("mark_transaction_failed: txn not found for order_id=%s", order_id)
#         return None

#     try:
#         txn.status = "failed"
#         if payment_id:
#             txn.payment_id = payment_id
#         if reason:
#             txn.note = (txn.note or "") + f"\nFailure reason: {reason}"
#         txn.updated_at = datetime.utcnow()
#         db.add(txn)
#         db.commit()
#         db.refresh(txn)
#         return txn
#     except Exception:
#         db.rollback()
#         log.exception("Failed to mark transaction failed for order_id=%s", order_id)
#         raise


# def list_transactions(db: Session, user_email: str, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
#     """
#     Return a list of transactions for a user (dicts).
#     """
#     q = db.query(WalletTransaction).filter(WalletTransaction.user_email == user_email).order_by(WalletTransaction.created_at.desc()).limit(limit).offset(offset)
#     out = []
#     for t in q.all():
#         out.append({
#             "id": t.id,
#             "order_id": t.order_id,
#             "payment_id": t.payment_id,
#             "amount": float(t.amount),
#             "currency": t.currency,
#             "status": t.status,
#             "provider": t.provider,
#             "note": t.note,
#             "created_at": t.created_at,
#             "updated_at": t.updated_at,
#         })
#     return out


# def debit_wallet(db: Session, user_email: str, amount: float, reason: Optional[str] = None) -> bool:
#     """
#     Debit user's wallet if sufficient funds exist. Atomic. Returns True on success.
#     If insufficient funds, returns False.
#     """
#     amount = _to_two_decimals(amount)
#     try:
#         bal = get_or_create_balance(db, user_email)
#         if (bal.balance or 0.0) < amount:
#             return False
#         bal.balance = _to_two_decimals(bal.balance - amount)
#         bal.updated_at = datetime.utcnow()
#         db.add(bal)
#         # Optionally create a debit transaction record (provider='internal')
#         txn = WalletTransaction(
#             user_email=user_email,
#             order_id=f"debit_internal_{int(datetime.utcnow().timestamp())}",
#             payment_id=None,
#             amount=-amount,
#             currency="INR",
#             status="success",
#             provider="internal",
#             note=reason,
#             created_at=datetime.utcnow(),
#             updated_at=datetime.utcnow(),
#         )
#         db.add(txn)
#         db.commit()
#         return True
#     except Exception:
#         db.rollback()
#         log.exception("Failed to debit wallet for %s", user_email)
#         raise









# app/models/wallet_utils.py
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import logging
import math

from sqlalchemy.orm import Session
from sqlalchemy import select, update, func

from app.models.wallet_model import WalletBalance, WalletTransaction, OpenPosition, TradeHistory
# kept RefundRequest if you want to use it elsewhere

log = logging.getLogger(__name__)


def _to_two_decimals(value: float) -> float:
    """Normalize floats to 2 decimal places (money)."""
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def get_or_create_balance(db: Session, user_email: str) -> WalletBalance:
    bal = db.execute(select(WalletBalance).where(WalletBalance.user_email == user_email)).scalar_one_or_none()
    if bal is None:
        bal = WalletBalance(user_email=user_email, balance=0.0, updated_at=datetime.utcnow())
        db.add(bal)
        db.commit()
        db.refresh(bal)
    return bal


def get_balance(db: Session, user_email: str) -> float:
    bal = db.execute(select(WalletBalance).where(WalletBalance.user_email == user_email)).scalar_one_or_none()
    return _to_two_decimals(bal.balance) if bal else 0.0


def create_transaction(
    db: Session,
    user_email: str,
    order_id: Optional[str],
    amount: float,
    currency: str = "INR",
    provider: str = "razorpay",
    note: Optional[str] = None,
    status: str = "pending",
) -> WalletTransaction:
    txn = WalletTransaction(
        user_email=user_email,
        order_id=(order_id or ""),
        payment_id=None,
        amount=_to_two_decimals(amount),
        currency=currency,
        status=status,
        provider=provider,
        note=note,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def mark_transaction_success(db: Session, order_id: str, payment_id: Optional[str] = None, amount: Optional[float] = None) -> Optional[WalletTransaction]:
    txn = db.execute(select(WalletTransaction).where(WalletTransaction.order_id == order_id)).scalar_one_or_none()
    if not txn:
        log.warning("mark_transaction_success: txn not found for order_id=%s", order_id)
        return None

    try:
        txn.status = "success"
        if payment_id:
            txn.payment_id = payment_id
        if amount is not None:
            txn.amount = _to_two_decimals(amount)
        txn.updated_at = datetime.utcnow()
        db.add(txn)

        bal = get_or_create_balance(db, txn.user_email)
        bal.balance = _to_two_decimals((bal.balance or 0.0) + float(txn.amount))
        bal.updated_at = datetime.utcnow()
        db.add(bal)

        db.commit()
        db.refresh(txn)
        return txn
    except Exception:
        db.rollback()
        log.exception("Failed to mark transaction success for order_id=%s", order_id)
        raise


def mark_transaction_failed(db: Session, order_id: str, payment_id: Optional[str] = None, reason: Optional[str] = None) -> Optional[WalletTransaction]:
    txn = db.execute(select(WalletTransaction).where(WalletTransaction.order_id == order_id)).scalar_one_or_none()
    if not txn:
        log.warning("mark_transaction_failed: txn not found for order_id=%s", order_id)
        return None

    try:
        txn.status = "failed"
        if payment_id:
            txn.payment_id = payment_id
        if reason:
            txn.note = (txn.note or "") + f"\nFailure reason: {reason}"
        txn.updated_at = datetime.utcnow()
        db.add(txn)
        db.commit()
        db.refresh(txn)
        return txn
    except Exception:
        db.rollback()
        log.exception("Failed to mark transaction failed for order_id=%s", order_id)
        raise


def list_transactions(db: Session, user_email: str, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
    q = db.query(WalletTransaction).filter(WalletTransaction.user_email == user_email).order_by(WalletTransaction.created_at.desc()).limit(limit).offset(offset)
    out = []
    for t in q.all():
        out.append({
            "id": t.id,
            "order_id": t.order_id,
            "payment_id": t.payment_id,
            "amount": float(t.amount),
            "currency": t.currency,
            "status": t.status,
            "provider": t.provider,
            "note": t.note,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
        })
    return out


def debit_wallet(db: Session, user_email: str, amount: float, reason: Optional[str] = None) -> Tuple[bool, Optional[WalletTransaction]]:
    """
    Debit user's wallet if sufficient funds exist. Atomic.
    Returns (True, txn) on success, (False, None) on insufficient funds.
    """
    amount = _to_two_decimals(amount)
    try:
        bal = get_or_create_balance(db, user_email)
        if (bal.balance or 0.0) < amount:
            return False, None
        bal.balance = _to_two_decimals(bal.balance - amount)
        bal.updated_at = datetime.utcnow()
        db.add(bal)

        # create internal debit txn
        txn = WalletTransaction(
            user_email=user_email,
            order_id=f"debit_internal_{int(datetime.utcnow().timestamp())}",
            payment_id=None,
            amount=-amount,
            currency="INR",
            status="success",
            provider="internal",
            note=reason,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)
        return True, txn
    except Exception:
        db.rollback()
        log.exception("Failed to debit wallet for %s", user_email)
        raise


def credit_wallet(db: Session, user_email: str, amount: float, reason: Optional[str] = None) -> WalletTransaction:
    """
    Credit user's wallet and create a transaction. Commits.
    """
    amount = _to_two_decimals(amount)
    try:
        bal = get_or_create_balance(db, user_email)
        bal.balance = _to_two_decimals(bal.balance + amount)
        bal.updated_at = datetime.utcnow()
        db.add(bal)

        txn = WalletTransaction(
            user_email=user_email,
            order_id=f"credit_internal_{int(datetime.utcnow().timestamp())}",
            payment_id=None,
            amount=amount,
            currency="INR",
            status="success",
            provider="internal",
            note=reason,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)
        return txn
    except Exception:
        db.rollback()
        log.exception("Failed to credit wallet for %s", user_email)
        raise


# ----------------------------
# Trading helpers
# ----------------------------
def create_position_on_buy(
    db: Session,
    user_email: str,
    symbol: str,
    amount: float,
    executed_price: float,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create an open position for a buy:
    - debit wallet by amount
    - compute qty = amount / price
    - create OpenPosition
    Returns dict with position info and txn info.
    """
    amount = _to_two_decimals(amount)
    executed_price = float(executed_price)
    if executed_price <= 0:
        raise ValueError("Invalid executed_price")

    qty = amount / executed_price
    # normalize qty to reasonable precision (6 decimals)
    qty = float(Decimal(str(qty)).quantize(Decimal("0.000001")))

    # Debit wallet
    ok, txn = debit_wallet(db, user_email, amount, reason=f"Buy {symbol} amount reserved")
    if not ok:
        return {"ok": False, "error": "insufficient_funds"}

    try:
        pos = OpenPosition(
            user_email=user_email,
            symbol=symbol,
            amount=amount,
            qty=qty,
            entry_price=executed_price,
            remaining_qty=qty,
            status="open",
            note=note or "",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(pos)
        db.commit()
        db.refresh(pos)
    except Exception:
        db.rollback()
        # refund the debit if position creation fails
        credit_wallet(db, user_email, amount, reason="Refund failed buy (position creation error)")
        log.exception("create_position_on_buy failed to create OpenPosition")
        raise

    return {
        "ok": True,
        "position": {
            "id": pos.id,
            "symbol": pos.symbol,
            "amount": pos.amount,
            "qty": pos.qty,
            "entry_price": pos.entry_price,
            "remaining_qty": pos.remaining_qty,
            "status": pos.status,
        },
        "debit_txn_id": txn.id if txn else None
    }


def _fetch_open_positions_fifo(db: Session, user_email: str, symbol: str) -> List[OpenPosition]:
    """
    Returns list of open positions for user/symbol ordered by created_at (FIFO).
    """
    q = db.query(OpenPosition).filter(
        OpenPosition.user_email == user_email,
        OpenPosition.symbol == symbol,
        OpenPosition.remaining_qty > 0.0
    ).order_by(OpenPosition.created_at.asc())
    return q.all()


def close_positions_on_sell(
    db: Session,
    user_email: str,
    symbol: str,
    sell_qty: Optional[float],
    sell_price: float,
    sell_amount: Optional[float] = None,
    require_full_quantity: bool = True,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """
    Close open positions for user/symbol by selling sell_qty units (or compute qty from sell_amount).
    - Matches open positions FIFO (oldest buys closed first)
    - For each closed portion, compute proportionate cost basis and realized PnL
    - Credit wallet with (gross proceeds) and record TradeHistory entries
    Returns summary dict.
    If require_full_quantity and available_qty < sell_qty -> returns error.
    """
    sell_price = float(sell_price)
    if sell_price <= 0:
        raise ValueError("Invalid sell_price")

    # If sell_qty not provided but sell_amount provided, compute qty
    if (sell_qty is None or sell_qty == 0.0) and sell_amount:
        sell_qty = sell_amount / sell_price
    if sell_qty is None or sell_qty <= 0:
        raise ValueError("sell_qty required")

    # Normalize
    sell_qty = float(Decimal(str(sell_qty)).quantize(Decimal("0.000001")))

    open_positions = _fetch_open_positions_fifo(db, user_email, symbol)
    total_available = sum([p.remaining_qty for p in open_positions])
    if total_available <= 0:
        return {"ok": False, "error": "no_open_positions"}

    if require_full_quantity and total_available + 1e-9 < sell_qty:
        return {"ok": False, "error": "insufficient_open_quantity", "available_qty": total_available}

    qty_to_close = sell_qty
    closed_parts = []  # list of dicts for position closures
    total_cost_basis = 0.0
    total_proceeds = 0.0
    total_realized = 0.0

    try:
        for pos in open_positions:
            if qty_to_close <= 0:
                break
            closing_qty = min(pos.remaining_qty, qty_to_close)
            proportion = closing_qty / pos.qty if pos.qty > 0 else 0.0
            amount_closed = _to_two_decimals(pos.amount * proportion)  # portion of invested INR for closing_qty
            gross = _to_two_decimals(closing_qty * sell_price)
            realized = _to_two_decimals(gross - amount_closed)

            # update totals
            total_cost_basis += amount_closed
            total_proceeds += gross
            total_realized += realized

            # update pos.remaining_qty and status
            pos.remaining_qty = _to_two_decimals(pos.remaining_qty - closing_qty)
            if pos.remaining_qty <= 0:
                pos.status = "closed"
            else:
                pos.status = "partial"
            pos.updated_at = datetime.utcnow()
            db.add(pos)

            closed_parts.append({
                "position_id": pos.id,
                "closed_qty": closing_qty,
                "entry_price": pos.entry_price,
                "amount_closed": amount_closed,
            })

            qty_to_close = _to_two_decimals(qty_to_close - closing_qty)

        # commit position updates
        db.commit()

        # credit the wallet with proceeds (principal of closed part + realized PnL)
        # We'll credit total_proceeds (which includes principal + pnl). That is simplest and clear.
        # Optionally you might want to only credit principal and separately track PnL. Here we credit whole proceeds.
        credit_reason = f"Sell {symbol} qty={sell_qty} @ {sell_price}"
        credit_txn = credit_wallet(db, user_email, total_proceeds, reason=credit_reason)

        # record a trade history entry
        th = TradeHistory(
            user_email=user_email,
            symbol=symbol,
            sell_qty=sell_qty - qty_to_close,  # actual sold
            sell_price=sell_price,
            gross_proceeds=_to_two_decimals(total_proceeds),
            cost_basis=_to_two_decimals(total_cost_basis),
            realized_pnl=_to_two_decimals(total_realized),
            position_ids=closed_parts,
            note=note or "",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(th)
        db.commit()
        db.refresh(th)

        return {
            "ok": True,
            "sold_qty": _to_two_decimals(sell_qty - qty_to_close),
            "requested_qty": sell_qty,
            "total_proceeds": _to_two_decimals(total_proceeds),
            "cost_basis": _to_two_decimals(total_cost_basis),
            "realized_pnl": _to_two_decimals(total_realized),
            "positions_closed": closed_parts,
            "credit_txn_id": credit_txn.id if credit_txn else None,
            "trade_history_id": th.id,
        }

    except Exception:
        db.rollback()
        log.exception("Failed to close positions for user=%s symbol=%s", user_email, symbol)
        raise
