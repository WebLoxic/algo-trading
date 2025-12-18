# app/api/market_routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user

from app.services.market_service import MarketService

router = APIRouter(prefix="/market", tags=["market"])

@router.get("/tick/{symbol}")
def get_latest_tick(symbol: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = MarketService(db, user)
    return svc.get_latest_tick(symbol)

@router.get("/subscribe/{symbol}")
def subscribe_symbol(symbol: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = MarketService(db, user)
    svc.subscribe(symbol)
    return {"ok": True}
