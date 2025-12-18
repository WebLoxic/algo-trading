from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db import Base
from datetime import datetime

# ---------------------------
# REWARD MASTER
# ---------------------------
class Reward(Base):
    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    reward_type = Column(String, nullable=False)  # deposit, referral, task
    description = Column(Text, nullable=True)
    amount = Column(Float, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("UserReward", back_populates="reward")

# ---------------------------
# USER REWARDS
# ---------------------------
class UserReward(Base):
    __tablename__ = "user_rewards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    reward_id = Column(Integer, ForeignKey("rewards.id"))
    claimed = Column(Boolean, default=False)
    claimed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    reward = relationship("Reward", back_populates="users")


# ---------------------------
# REFERRALS
# ---------------------------
class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(Integer, index=True, nullable=False)
    referee_id = Column(Integer, index=True, nullable=False)
    reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    claimed = Column(Boolean, default=False)
    claimed_at = Column(DateTime, nullable=True)

    reward = relationship("Reward")
