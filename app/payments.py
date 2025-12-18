# # app/utils/payments.py
# def verify_razorpay_signature(payload: dict) -> bool:
#     # TODO: implement actual signature verification using razorpay secret
#     return True

# def create_razorpay_order(amount_inr: int, currency: str = "INR"):
#     # TODO: call Razorpay create order API and return order_id + key
#     return {"order_id": f"demo_{amount_inr}", "key": "rzp_test_demo", "amount": amount_inr}




# -----------------------------------------------------------
# app/payments.py
# FINAL — Razorpay Order + Signature Verification
# -----------------------------------------------------------

import os
import razorpay
import hmac
import hashlib
from typing import Dict


# -----------------------------------------------------------
# Razorpay Client (Singleton)
# -----------------------------------------------------------
_client = None


def get_razorpay_client():
    global _client
    if _client is None:
        _client = razorpay.Client(
            auth=(
                os.getenv("RAZORPAY_KEY_ID"),
                os.getenv("RAZORPAY_KEY_SECRET"),
            )
        )
    return _client


# -----------------------------------------------------------
# Create Razorpay Order
# -----------------------------------------------------------
def create_razorpay_order(
    amount: float,
    receipt: str,
    currency: str = "INR"
) -> Dict:
    """
    amount = INR (e.g. 1499.00)
    Razorpay expects paise → conversion done here
    """

    client = get_razorpay_client()

    order = client.order.create({
        "amount": int(amount * 100),   # ✅ INR → paise
        "currency": currency,
        "receipt": receipt,
        "payment_capture": 1
    })

    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "key": os.getenv("RAZORPAY_KEY_ID"),
        "receipt": receipt
    }


# -----------------------------------------------------------
# Verify Razorpay Payment Signature
# -----------------------------------------------------------
def verify_razorpay_signature(payload: dict) -> bool:
    """
    payload must contain:
    - razorpay_order_id
    - razorpay_payment_id
    - razorpay_signature
    """

    secret = os.getenv("RAZORPAY_KEY_SECRET")

    order_id = payload.get("razorpay_order_id")
    payment_id = payload.get("razorpay_payment_id")
    signature = payload.get("razorpay_signature")

    if not order_id or not payment_id or not signature:
        return False

    generated_signature = hmac.new(
        secret.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()

    return generated_signature == signature
