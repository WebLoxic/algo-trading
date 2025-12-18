# # app/api/payment_routes.py
# import os
# import time
# import uuid
# import hmac
# import hashlib
# import logging
# import json
# from typing import Optional

# from fastapi import APIRouter, HTTPException, Request, Depends, status
# from fastapi.responses import JSONResponse
# from sqlalchemy.orm import Session
# from sqlalchemy import text

# from app.db import get_db
# from app import crud
# from app.models.wallet_model import WalletTransaction as ORMWalletTransaction, WalletBalance as ORMWalletBalance

# log = logging.getLogger("app.payment_routes")
# log.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

# # Razorpay credentials
# RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
# RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# # Initialize Razorpay client if keys exist
# razorpay_client = None
# if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
#     try:
#         import razorpay
#         razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
#         log.info("✅ Razorpay client initialized")
#     except Exception as e:
#         log.warning("⚠️ Razorpay client could not be initialized: %s", e)

# router = APIRouter(prefix="/payment", tags=["payment"])


# # ---------------------------------------------------------
# # CREATE RAZORPAY ORDER
# # ---------------------------------------------------------
# @router.post("/create-order")
# async def create_order(request: Request):
#     if razorpay_client is None:
#         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment provider not configured")

#     try:
#         payload = await request.json()
#         amount = float(payload.get("amount"))
#     except Exception:
#         raise HTTPException(status_code=400, detail="Invalid payload or amount")

#     if amount <= 0:
#         raise HTTPException(status_code=400, detail="Amount must be > 0")

#     receipt = f"rcpt_{int(time.time())}_{uuid.uuid4().hex[:8]}"

#     try:
#         order = razorpay_client.order.create({
#             "amount": int(round(amount * 100)),
#             "currency": "INR",
#             "receipt": receipt,
#             "payment_capture": 1,
#             "notes": payload.get("notes", {})
#         })
#         return {"ok": True, "order": order}
#     except Exception as e:
#         log.exception("Error creating Razorpay order: %s", e)
#         raise HTTPException(status_code=500, detail="Failed to create Razorpay order")


# # ---------------------------------------------------------
# # VERIFY PAYMENT
# # ---------------------------------------------------------
# @router.post("/verify")
# async def verify_payment(request: Request, db: Session = Depends(get_db)):
#     if RAZORPAY_KEY_SECRET is None:
#         raise HTTPException(status_code=503, detail="Payment provider not configured")

#     try:
#         payload = await request.json()
#         order_id = payload.get("razorpay_order_id")
#         payment_id = payload.get("razorpay_payment_id")
#         signature = payload.get("razorpay_signature")
#         email = payload.get("email")
#         plan_id = payload.get("plan_id")
#         billing = (payload.get("billing") or "monthly").lower()
#     except Exception:
#         raise HTTPException(status_code=400, detail="Invalid payload")

#     if not all([order_id, payment_id, signature, email]):
#         raise HTTPException(status_code=400, detail="Missing required fields")

#     # Verify signature
#     gen_sig = hmac.new(
#         RAZORPAY_KEY_SECRET.encode("utf-8"),
#         f"{order_id}|{payment_id}".encode("utf-8"),
#         hashlib.sha256
#     ).hexdigest()

#     if not hmac.compare_digest(gen_sig, signature):
#         raise HTTPException(status_code=400, detail="Invalid payment signature")

#     # Prevent duplicate processing
#     existing = db.execute(
#         text("SELECT id, user_id FROM payment_transactions WHERE payment_id = :pid LIMIT 1"),
#         {"pid": payment_id}
#     ).fetchone()
#     if existing:
#         return {"ok": True, "msg": "already_processed", "payment_tx_id": existing["id"]}

#     # Fetch user
#     user_row = db.execute(
#         text("SELECT id FROM users WHERE email = :email LIMIT 1"),
#         {"email": email}
#     ).fetchone()
#     if not user_row:
#         raise HTTPException(status_code=404, detail="User not found")
#     user_id = user_row["id"]

#     # Insert payment transaction
#     res = db.execute(text("""
#         INSERT INTO payment_transactions
#         (user_id, order_id, payment_id, amount, currency, gateway, status, provider_response, created_at)
#         VALUES
#         (:user_id, :order_id, :payment_id, :amount, 'INR', 'razorpay', 'success', :response, now())
#         RETURNING id
#     """), {
#         "user_id": user_id,
#         "order_id": order_id,
#         "payment_id": payment_id,
#         "amount": float(payload.get("amount", 0)),
#         "response": json.dumps(payload)
#     })
#     payment_tx_id = res.fetchone()["id"]

#     # Wallet top-up path
#     if not plan_id:
#         wallet = db.query(ORMWalletBalance).filter_by(user_email=email).with_for_update().first()
#         if not wallet:
#             wallet = ORMWalletBalance(user_email=email, balance=float(payload.get("amount", 0)))
#             db.add(wallet)
#         else:
#             wallet.balance += float(payload.get("amount", 0))
#         db.add(ORMWalletTransaction(wallet_id=getattr(wallet, "id", None),
#                                     order_id=order_id,
#                                     payment_id=payment_id,
#                                     amount=float(payload.get("amount", 0)),
#                                     type="topup"))
#         db.commit()
#         db.refresh(wallet)
#         return {"ok": True, "status": "verified", "purpose": "topup", "new_balance": float(wallet.balance)}

#     # Subscription path
#     # Check idempotency
#     existing_sub = db.execute(
#         text("SELECT id FROM user_subscriptions WHERE external_payment_id = :pid LIMIT 1"),
#         {"pid": payment_id}
#     ).fetchone()
#     if existing_sub:
#         db.commit()
#         return {"ok": True, "msg": "subscription_already_active", "subscription_id": existing_sub["id"]}

#     # Create pending + activate
#     pending = crud.create_pending_subscription(user_id=user_id, plan_id=plan_id, billing_cycle=billing, meta={"order_id": order_id})
#     activated = crud.activate_subscription(subscription_id=pending.id, payment_id=payment_id, provider="razorpay", provider_payload={"order_id": order_id})
#     db.commit()

#     return {
#         "ok": True,
#         "status": "subscription_activated",
#         "subscription_id": activated.id if activated else pending.id,
#         "amount_paid": float(payload.get("amount", 0))
#     }










# ---------------------------------------------------------
# app/api/payment_routes.py
# FINAL, FULLY UPDATED
# Ensures subscriptions and wallet top-ups persist in DB
# ---------------------------------------------------------

import os
import time
import uuid
import hmac
import hashlib
import logging
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db import get_db, SessionLocal
from app import crud
from app.models.wallet_model import WalletTransaction as ORMWalletTransaction, WalletBalance as ORMWalletBalance

log = logging.getLogger("app.payment_routes")
log.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

# Razorpay credentials
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# Initialize Razorpay client if keys exist
razorpay_client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    try:
        import razorpay
        razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        log.info("✅ Razorpay client initialized")
    except Exception as e:
        log.warning("⚠️ Razorpay client could not be initialized: %s", e)

router = APIRouter(prefix="/payment", tags=["payment"])


# ---------------------------------------------------------
# CREATE RAZORPAY ORDER
# ---------------------------------------------------------
@router.post("/create-order")
async def create_order(request: Request):
    if razorpay_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment provider not configured")
    try:
        payload = await request.json()
        amount = float(payload.get("amount"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload or amount")

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be > 0")

    receipt = f"rcpt_{int(time.time())}_{uuid.uuid4().hex[:8]}"

    try:
        order = razorpay_client.order.create({
            "amount": int(round(amount * 100)),  # amount in paise
            "currency": "INR",
            "receipt": receipt,
            "payment_capture": 1,
            "notes": payload.get("notes", {})
        })
        return {"ok": True, "order": order}
    except Exception as e:
        log.exception("Error creating Razorpay order: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create Razorpay order")


# ---------------------------------------------------------
# VERIFY PAYMENT
# ---------------------------------------------------------
@router.post("/verify")
async def verify_payment(request: Request, db: Session = Depends(get_db)):
    if RAZORPAY_KEY_SECRET is None:
        raise HTTPException(status_code=503, detail="Payment provider not configured")

    try:
        payload = await request.json()
        order_id = payload.get("razorpay_order_id")
        payment_id = payload.get("razorpay_payment_id")
        signature = payload.get("razorpay_signature")
        email = payload.get("email")
        plan_id = payload.get("plan_id")
        billing = (payload.get("billing") or "monthly").lower()
        amount = float(payload.get("amount", 0))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    if not all([order_id, payment_id, signature, email]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Verify signature
    gen_sig = hmac.new(
        RAZORPAY_KEY_SECRET.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(gen_sig, signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    try:
        # Prevent duplicate processing
        existing = db.execute(
            text("SELECT id, user_id FROM payment_transactions WHERE payment_id = :pid LIMIT 1"),
            {"pid": payment_id}
        ).fetchone()
        if existing:
            return {"ok": True, "msg": "already_processed", "payment_tx_id": existing["id"]}

        # Fetch user
        user_row = db.execute(text("SELECT id FROM users WHERE email = :email LIMIT 1"), {"email": email}).fetchone()
        if not user_row:
            raise HTTPException(status_code=404, detail="User not found")
        user_id = user_row["id"]

        # Insert payment transaction
        res = db.execute(text("""
            INSERT INTO payment_transactions
            (user_id, order_id, payment_id, amount, currency, gateway, status, provider_response, created_at)
            VALUES
            (:user_id, :order_id, :payment_id, :amount, 'INR', 'razorpay', 'success', :response, now())
            RETURNING id
        """), {
            "user_id": user_id,
            "order_id": order_id,
            "payment_id": payment_id,
            "amount": amount,
            "response": json.dumps(payload)
        })
        payment_tx_id = res.fetchone()["id"]

        # WALLET TOP-UP PATH
        if not plan_id:
            wallet = db.query(ORMWalletBalance).filter_by(user_email=email).with_for_update().first()
            if not wallet:
                wallet = ORMWalletBalance(user_email=email, balance=amount)
                db.add(wallet)
            else:
                wallet.balance += amount
            db.add(ORMWalletTransaction(
                wallet_id=getattr(wallet, "id", None),
                order_id=order_id,
                payment_id=payment_id,
                amount=amount,
                type="topup"
            ))
            db.commit()
            db.refresh(wallet)
            return {"ok": True, "status": "verified", "purpose": "topup", "new_balance": float(wallet.balance)}

        # SUBSCRIPTION PATH
        # Check idempotency
        existing_sub = db.execute(
            text("SELECT id FROM user_subscriptions WHERE external_payment_id = :pid LIMIT 1"),
            {"pid": payment_id}
        ).fetchone()
        if existing_sub:
            db.commit()
            return {"ok": True, "msg": "subscription_already_active", "subscription_id": existing_sub["id"]}

        # Create pending + activate subscription
        pending = crud.create_pending_subscription(
            user_id=user_id,
            plan_id=plan_id,
            billing_cycle=billing,
            meta={"order_id": order_id},
            db=db
        )
        activated = crud.activate_subscription(
            subscription_id=pending.id,
            payment_id=payment_id,
            provider="razorpay",
            provider_payload={"order_id": order_id},
            db=db
        )
        db.commit()
        db.refresh(activated)
        return {
            "ok": True,
            "status": "subscription_activated",
            "subscription_id": activated.id if activated else pending.id,
            "amount_paid": amount
        }

    except Exception as e:
        db.rollback()
        log.exception("Payment verification failed for user=%s, payment_id=%s: %s", email, payment_id, e)
        raise HTTPException(status_code=500, detail="Payment verification failed")
