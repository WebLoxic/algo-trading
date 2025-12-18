from sqlalchemy import Column, Text, Numeric, Boolean, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Text, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    subtitle = Column(Text)
    monthly = Column(Numeric(12, 2))
    annually = Column(Numeric(12, 2))
    features = Column(JSONB)
    limits = Column(JSONB)
    sla = Column(Text)
    refund_policy = Column(Text)
    highlight = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default="now()")
