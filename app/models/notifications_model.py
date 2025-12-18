from sqlalchemy import Column, BigInteger, Text, Boolean, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from app.core.database import Base

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    channel = Column(Text)
    title = Column(Text)
    body = Column(Text)
    meta = Column(JSONB, server_default="{}")
    delivered = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
