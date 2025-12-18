from sqlalchemy import Column, BigInteger, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from app.core.database import Base

class Backtest(Base):
    __tablename__ = "backtests"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    strategy_id = Column(BigInteger)
    params = Column(JSONB)
    status = Column(Text, default="queued")
    result = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class BacktestTrade(Base):
    __tablename__ = "backtest_trades"
    id = Column(BigInteger, primary_key=True, index=True)
    backtest_id = Column(BigInteger, ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(Text)
    side = Column(Text)
    qty = Column(Numeric(18,6))
    price = Column(Numeric(18,6))
    ts = Column(TIMESTAMP(timezone=True))
