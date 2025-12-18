from sqlalchemy import Column, BigInteger, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(BigInteger, primary_key=True, index=True)
    actor_user_id = Column(BigInteger)
    action = Column(Text, nullable=False)
    resource_type = Column(Text)
    resource_id = Column(Text)
    payload = Column(JSONB, server_default="{}")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
