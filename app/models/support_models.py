from sqlalchemy import Column, BigInteger, Text, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from app.core.database import Base

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    subject = Column(Text)
    body = Column(Text)
    status = Column(Text, default="open")
    priority = Column(Text, default="normal")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class OnboardingRequest(Base):
    __tablename__ = "onboarding_requests"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger)
    provider = Column(Text)
    notes = Column(Text)
    status = Column(Text, default="new")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
