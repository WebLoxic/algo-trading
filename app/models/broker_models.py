from sqlalchemy import Column, Text, BigInteger, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from app.core.database import Base

class BrokerProvider(Base):
    __tablename__ = "broker_providers"
    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    config = Column(JSONB, server_default="{}")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class BrokerAccount(Base):
    __tablename__ = "broker_accounts"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    provider_id = Column(Text, ForeignKey("broker_providers.id"), nullable=False)
    account_identifier = Column(Text)
    meta = Column(JSONB, server_default="{}")
    connected_at = Column(TIMESTAMP(timezone=True))
    disconnected_at = Column(TIMESTAMP(timezone=True))

class BrokerToken(Base):
    __tablename__ = "broker_tokens"
    id = Column(BigInteger, primary_key=True, index=True)
    broker_account_id = Column(BigInteger, ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=False)
    token_type = Column(Text)
    token_encrypted = Column(Text, nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True))
    meta = Column(JSONB, server_default="{}")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
