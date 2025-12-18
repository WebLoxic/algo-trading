from sqlalchemy import Column, BigInteger, Numeric, TIMESTAMP, Text
from sqlalchemy.sql import func
from app.core.database import Base
from sqlalchemy import ForeignKey

class CreditsBalance(Base):
    __tablename__ = "credits_balance"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    credits = Column(Numeric(18,4), default=0)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class CreditsHistory(Base):
    __tablename__ = "credits_history"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    delta = Column(Numeric(18,4), nullable=False)
    reason = Column(Text)
    source = Column(Text)
    reference_id = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
