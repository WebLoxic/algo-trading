from sqlalchemy import Column, BigInteger, Text, Numeric, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy import ForeignKey

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(Text, ForeignKey("plans.id"), nullable=False)
    billing_cycle = Column(Text, nullable=False)
    amount = Column(Numeric(12,2))
    status = Column(Text, nullable=False)
    started_at = Column(TIMESTAMP(timezone=True))
    ends_at = Column(TIMESTAMP(timezone=True))
    invoice_id = Column(Text)
    metadata = Column(JSONB, server_default="{}")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # relationships (optional)
    # user = relationship("User", back_populates="subscriptions")
    # plan = relationship("Plan")
