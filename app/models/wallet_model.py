# # app/models/wallet_model.py
# from sqlalchemy import (
#     Column, Integer, Float, DateTime, Text, Boolean, String, ForeignKey, JSON, UniqueConstraint
# )
# from sqlalchemy.sql import func
# from sqlalchemy.orm import relationship
# from app.db import Base

# class WalletBalance(Base):
#     __tablename__ = "wallet_balances"
#     id = Column(Integer, primary_key=True, index=True)
#     user_email = Column(String(255), nullable=False, index=True, unique=False)
#     balance = Column(Float, nullable=False, default=0.0)
#     currency = Column(String(12), nullable=False, default="INR")
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


# class WalletTransaction(Base):
#     __tablename__ = "wallet_transactions"
#     id = Column(Integer, primary_key=True, index=True)
#     user_email = Column(String(255), nullable=False, index=True)
#     order_id = Column(String(128), nullable=True, index=True)        # provider order id (Razorpay)
#     payment_id = Column(String(128), nullable=True, index=True)      # provider payment id (Razorpay) — nullable
#     amount = Column(Float, nullable=False, default=0.0)              # rupees
#     status = Column(String(32), nullable=False, default="pending")   # pending / success / refunded / failed
#     provider = Column(String(64), nullable=True)                     # 'razorpay' etc.
#     currency = Column(String(12), nullable=False, default="INR")
#     note = Column(Text, nullable=True)
#     provider_response = Column(JSON, nullable=True)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

#     # add indexes/unique constraints as needed
#     __table_args__ = (UniqueConstraint("order_id", "payment_id", name="uq_order_payment"),)


# class RefundRequest(Base):
#     __tablename__ = "wallet_refunds"
#     id = Column(Integer, primary_key=True, index=True)
#     txn_id = Column(Integer, nullable=True)      # optional FK to wallet_transactions.id
#     user_email = Column(String(255), nullable=False, index=True)
#     payment_id = Column(String(128), nullable=True)
#     order_id = Column(String(128), nullable=True)
#     amount = Column(Float, nullable=False, default=0.0)  # rupees
#     reason = Column(Text, nullable=True)
#     status = Column(String(32), nullable=False, default="requested")  # requested / processing / refunded / failed
#     provider_response = Column(JSON, nullable=True)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())








# app/models/wallet_model.py
from sqlalchemy import (
    Column, Integer, Float, DateTime, Text, Boolean, String, ForeignKey, JSON, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base

class WalletBalance(Base):
    __tablename__ = "wallet_balances"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), nullable=False, index=True, unique=False)
    balance = Column(Float, nullable=False, default=0.0)
    currency = Column(String(12), nullable=False, default="INR")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), nullable=False, index=True)
    order_id = Column(String(128), nullable=True, index=True)        # provider order id (Razorpay)
    payment_id = Column(String(128), nullable=True, index=True)      # provider payment id (Razorpay) — nullable
    amount = Column(Float, nullable=False, default=0.0)              # rupees (positive for credit, negative for debit)
    status = Column(String(32), nullable=False, default="pending")   # pending / success / refunded / failed
    provider = Column(String(64), nullable=True)                     # 'razorpay' etc.
    currency = Column(String(12), nullable=False, default="INR")
    note = Column(Text, nullable=True)
    provider_response = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # add indexes/unique constraints as needed
    __table_args__ = (UniqueConstraint("order_id", "payment_id", name="uq_order_payment"),)


class RefundRequest(Base):
    __tablename__ = "wallet_refunds"
    id = Column(Integer, primary_key=True, index=True)
    txn_id = Column(Integer, nullable=True)      # optional FK to wallet_transactions.id
    user_email = Column(String(255), nullable=False, index=True)
    payment_id = Column(String(128), nullable=True)
    order_id = Column(String(128), nullable=True)
    amount = Column(Float, nullable=False, default=0.0)  # rupees
    reason = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="requested")  # requested / processing / refunded / failed
    provider_response = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


# ----------------------------
# Trading / position models
# ----------------------------
class OpenPosition(Base):
    """
    Records each buy (entry) as an open position that can later be closed on sell.
    qty is units bought (e.g. shares / lots). amount is INR invested for this entry.
    status: open / closed / partial
    """
    __tablename__ = "open_positions"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), nullable=False, index=True)
    symbol = Column(String(64), nullable=False, index=True)
    amount = Column(Float, nullable=False, default=0.0)      # INR invested
    qty = Column(Float, nullable=False, default=0.0)         # units bought
    entry_price = Column(Float, nullable=False, default=0.0) # price per unit at buy
    remaining_qty = Column(Float, nullable=False, default=0.0) # qty left open
    status = Column(String(32), nullable=False, default="open") # open / closed / partial
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class TradeHistory(Base):
    """
    Records closed trades (sell events) and realized PnL.
    For partial closes, multiple TradeHistory rows can reference different open_position ids via position_ids JSON.
    """
    __tablename__ = "trade_history"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), nullable=False, index=True)
    symbol = Column(String(64), nullable=False, index=True)
    sell_qty = Column(Float, nullable=False, default=0.0)
    sell_price = Column(Float, nullable=False, default=0.0)
    gross_proceeds = Column(Float, nullable=False, default=0.0)   # sell_qty * sell_price
    cost_basis = Column(Float, nullable=False, default=0.0)       # total invested amount for closed qty
    realized_pnl = Column(Float, nullable=False, default=0.0)     # gross_proceeds - cost_basis
    position_ids = Column(JSON, nullable=True)                    # list of {pos_id, closed_qty, entry_price, amount_closed}
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
