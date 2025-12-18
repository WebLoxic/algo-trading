# app/api/marketplace_routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user

from app.services.marketplace_service import MarketplaceService

router = APIRouter(prefix="/marketplace", tags=["marketplace"])

@router.get("/list")
def list_marketplace(db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = MarketplaceService(db, user)
    return svc.list_items()

@router.post("/buy/{strategy_id}")
def buy_strategy(strategy_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = MarketplaceService(db, user)
    return svc.buy(strategy_id)
