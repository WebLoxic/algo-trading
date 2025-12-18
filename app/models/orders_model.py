from sqlalchemy import Column, BigInteger, Text, Numeric, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from app.core.database import Base

class Order(Base):
    __tablename__ = "orders"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    broker_account_id = Column(BigInteger, ForeignKey("broker_accounts.id"))
    symbol = Column(Text, nullable=False)
    side = Column(Text, nullable=False)
    qty = Column(Numeric(18,6))
    order_type = Column(Text)
    price = Column(Numeric(18,6))
    status = Column(Text, default="created")
    external_order_id = Column(Text)
    filled_qty = Column(Numeric(18,6), default=0)
    avg_fill_price = Column(Numeric(18,6))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class OrderEvent(Base):
    __tablename__ = "order_events"
    id = Column(BigInteger, primary_key=True, index=True)
    order_id = Column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(Text)
    payload = Column(JSONB, server_default="{}")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
