from sqlalchemy import Column, BigInteger, Text, Numeric, TIMESTAMP, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from app.core.database import Base

class MarketplaceStrategy(Base):
    __tablename__ = "marketplace_strategies"
    id = Column(BigInteger, primary_key=True, index=True)
    slug = Column(Text, unique=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    author_user_id = Column(BigInteger, ForeignKey("users.id"))
    price = Column(Numeric(12,2), default=0)
    tags = Column(ARRAY(Text))
    metadata = Column(JSONB, server_default="{}")
    visibility = Column(Text, default="public")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class MarketplacePurchase(Base):
    __tablename__ = "marketplace_purchases"
    id = Column(BigInteger, primary_key=True, index=True)
    strategy_id = Column(BigInteger, ForeignKey("marketplace_strategies.id"), nullable=False)
    buyer_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    seller_id = Column(BigInteger, ForeignKey("users.id"))
    amount = Column(Numeric(12,2), nullable=False)
    commission_pct = Column(Numeric(5,2), default=0)
    status = Column(Text, default="pending")
    payment_ref = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class SellerBalance(Base):
    __tablename__ = "seller_balances"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), unique=True, nullable=False)
    pending_balance = Column(Numeric(18,4), default=0)
    available_balance = Column(Numeric(18,4), default=0)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class MarketplacePayoutRequest(Base):
    __tablename__ = "marketplace_payout_requests"
    id = Column(BigInteger, primary_key=True, index=True)
    seller_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(18,4), nullable=False)
    status = Column(Text, default="requested")
    requested_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    processed_at = Column(TIMESTAMP(timezone=True))
