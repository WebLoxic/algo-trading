# # -----------------------------------------------------------
# # app/services/billing_service.py
# # Final version — supports Razorpay & Wallet
# # -----------------------------------------------------------
# from sqlalchemy.orm import Session
# from app.utils.payments import create_razorpay_order


# class BillingService:
#     def __init__(self, db: Session, user):
#         self.db = db
#         self.user = user

#     # Return available plans (static or DB-based)
#     def list_plans(self):
#         return [
#             {"id": 1, "name": "Pro", "monthly": 1499, "yearly": 9999},
#             {"id": 2, "name": "Premium", "monthly": 2499, "yearly": 14999},
#         ]

#     # Generate Razorpay order
#     def create_payment_order(self, amount: float):
#         rp_order = create_razorpay_order(int(amount * 100))
#         return {
#             "gateway": "razorpay",
#             "order": rp_order
#         }



# -----------------------------------------------------------
# app/services/billing_service.py
# Final version — Razorpay + Wallet ready
# -----------------------------------------------------------

from sqlalchemy.orm import Session
from app.payments import create_razorpay_order



class BillingService:
    def __init__(self, db: Session, user: dict):
        self.db = db
        self.user = user

    # Static plans (can be DB-driven later)
    def list_plans(self):
        return [
            {"id": 1, "name": "Pro", "monthly": 1499, "yearly": 9999},
            {"id": 2, "name": "Premium", "monthly": 2499, "yearly": 14999},
        ]

    # Create Razorpay order
    def create_payment_order(self, amount: float):
        receipt = f"sub_{self.user['id']}"

        rp_order = create_razorpay_order(
            amount=amount,        # 👈 pass RUPEES
            receipt=receipt
        )

        return {
            "gateway": "razorpay",
            "order": rp_order
        }
