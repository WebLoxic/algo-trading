# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from datetime import datetime
# from typing import List

# from app.db import SessionLocal
# from app.auth import get_current_user_row
# from app.models.rewards_model import Reward, UserReward
# from app.schemas.rewards_schemas import RewardOut, UserRewardOut
# from app.crud import crud_rewards

# router = APIRouter(prefix="/api/rewards", tags=["Rewards"])

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # -----------------------------
# # GET ALL ACTIVE REWARDS
# # -----------------------------
# @router.get("/", response_model=List[RewardOut])
# def list_rewards(db: Session = Depends(get_db)):
#     rewards = crud_rewards.list_rewards(db)
#     active_rewards = [r for r in rewards if r.active]
#     return active_rewards

# # -----------------------------
# # GET USER REWARDS
# # -----------------------------
# @router.get("/me", response_model=List[UserRewardOut])
# def user_rewards(
#     user = Depends(get_current_user_row),
#     db: Session = Depends(get_db)
# ):
#     return crud_rewards.list_user_rewards(db, user_id=user["user_id"], active_only=False)

# # -----------------------------
# # CLAIM A REWARD
# # -----------------------------
# @router.post("/claim/{reward_id}", response_model=UserRewardOut)
# def claim_reward(
#     reward_id: int,
#     user = Depends(get_current_user_row),
#     db: Session = Depends(get_db)
# ):
#     reward = crud_rewards.get_reward(db, reward_id)
#     if not reward or not reward.active:
#         raise HTTPException(status_code=404, detail="Reward not found or inactive")

#     existing = db.query(UserReward).filter(
#         UserReward.user_id == user["user_id"],
#         UserReward.reward_id == reward_id
#     ).first()
#     if existing:
#         raise HTTPException(status_code=400, detail="Reward already claimed")

#     return crud_rewards.assign_reward_to_user(db, user_id=user["user_id"], reward_id=reward_id)







# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from typing import List
# from app.db import SessionLocal
# from app.auth import get_current_user_row
# from app.schemas.rewards_schemas import RewardOut, UserRewardOut
# from app.crud import crud_rewards

# router = APIRouter(prefix="/api/rewards", tags=["Rewards"])

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# # -----------------------------
# # LIST REWARDS
# # -----------------------------
# @router.get("/", response_model=List[RewardOut])
# def list_rewards(db: Session = Depends(get_db)):
#     rewards = crud_rewards.list_rewards(db)
#     active_rewards = [r for r in rewards if r.active]
#     return active_rewards


# # -----------------------------
# # USER REWARDS
# # -----------------------------
# @router.get("/me", response_model=List[UserRewardOut])
# def user_rewards(user=Depends(get_current_user_row), db: Session = Depends(get_db)):
#     return crud_rewards.list_user_rewards(db, user_id=user["user_id"], active_only=False)


# # -----------------------------
# # CLAIM REWARD
# # -----------------------------
# @router.post("/claim/{reward_id}", response_model=UserRewardOut)
# def claim_reward(reward_id: int, user=Depends(get_current_user_row), db: Session = Depends(get_db)):
#     reward = crud_rewards.get_reward(db, reward_id)
#     if not reward or not reward.active:
#         raise HTTPException(status_code=404, detail="Reward not found or inactive")

#     existing = db.query(UserReward).filter(
#         UserReward.user_id == user["user_id"],
#         UserReward.reward_id == reward_id
#     ).first()
#     if existing:
#         raise HTTPException(status_code=400, detail="Reward already claimed")

#     return crud_rewards.assign_reward_to_user(db, user_id=user["user_id"], reward_id=reward_id)


# # -----------------------------
# # LIST USER REFERRALS
# # -----------------------------
# @router.get("/referrals", response_model=List[UserRewardOut])
# def user_referrals(user=Depends(get_current_user_row), db: Session = Depends(get_db)):
#     return crud_rewards.list_user_referrals(db, user_id=user["user_id"])


# # -----------------------------
# # CLAIM REFERRAL REWARD
# # -----------------------------
# @router.post("/referrals/claim/{referral_id}", response_model=UserRewardOut)
# def claim_referral(referral_id: int, user=Depends(get_current_user_row), db: Session = Depends(get_db)):
#     ref = crud_rewards.assign_referral_reward(db, ref_id=referral_id, reward_id=None)
#     if not ref:
#         raise HTTPException(status_code=404, detail="Referral not found or already claimed")
#     return ref


# # -----------------------------
# # LEADERBOARD
# # -----------------------------
# @router.get("/leaderboard")
# def leaderboard(db: Session = Depends(get_db)):
#     leaderboard = crud_rewards.get_leaderboard(db)
#     return leaderboard







# app/api/rewards_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db import SessionLocal
from app.auth import get_current_user_row
from app.schemas import RewardOut, UserRewardOut
from app import crud


router = APIRouter(prefix="/rewards", tags=["Rewards"])

# Dependency: database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -----------------------------
# LIST ALL ACTIVE REWARDS
# -----------------------------
@router.get("/", response_model=List[RewardOut])
def list_rewards(db: Session = Depends(get_db)):
    rewards = crud.list_rewards(db)
    active_rewards = [r for r in rewards if r.active]
    return active_rewards


# -----------------------------
# GET USER REWARDS
# -----------------------------
@router.get("/me", response_model=List[UserRewardOut])
def user_rewards(user=Depends(get_current_user_row), db: Session = Depends(get_db)):
    return crud.list_user_rewards(db, user_id=user["user_id"], active_only=False)


# -----------------------------
# CLAIM A REWARD
# -----------------------------
@router.post("/claim/{reward_id}", response_model=UserRewardOut)
def claim_reward(reward_id: int, user=Depends(get_current_user_row), db: Session = Depends(get_db)):
    reward = crud.get_reward(db, reward_id)
    if not reward or not reward.active:
        raise HTTPException(status_code=404, detail="Reward not found or inactive")

    # Check if user already claimed
    existing = db.query(crud.models.UserReward).filter(
        crud.models.UserReward.user_id == user["user_id"],
        crud.models.UserReward.reward_id == reward_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Reward already claimed")

    return crud.assign_reward_to_user(db, user_id=user["user_id"], reward_id=reward_id)


# -----------------------------
# LIST USER REFERRALS
# -----------------------------
@router.get("/referrals", response_model=List[UserRewardOut])
def user_referrals(user=Depends(get_current_user_row), db: Session = Depends(get_db)):
    return crud.list_user_referrals(db, user_id=user["user_id"])


# -----------------------------
# CLAIM REFERRAL REWARD
# -----------------------------
@router.post("/referrals/claim/{referral_id}", response_model=UserRewardOut)
def claim_referral(referral_id: int, user=Depends(get_current_user_row), db: Session = Depends(get_db)):
    ref = crud.assign_referral_reward(db, ref_id=referral_id, reward_id=None)
    if not ref:
        raise HTTPException(status_code=404, detail="Referral not found or already claimed")
    return ref


# -----------------------------
# LEADERBOARD
# -----------------------------
@router.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db)):
    return crud.get_leaderboard(db)





# -----------------------------
# ADMIN: LIST ALL REWARDS
# -----------------------------
@router.get("/admin/all", response_model=List[RewardOut])
def admin_list_rewards(db: Session = Depends(get_db), user=Depends(get_current_user_row)):
    if not user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return crud_rewards.list_rewards(db)


# -----------------------------
# ADMIN: LIST ALL USER REWARDS
# -----------------------------
@router.get("/admin/user_rewards", response_model=List[UserRewardOut])
def admin_user_rewards(db: Session = Depends(get_db), user=Depends(get_current_user_row)):
    if not user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return db.query(models.UserReward).all()


# -----------------------------
# ADMIN: LEADERBOARD
# -----------------------------
@router.get("/admin/leaderboard")
def admin_leaderboard(db: Session = Depends(get_db), user=Depends(get_current_user_row)):
    if not user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return crud_rewards.get_leaderboard(db)
