# app/api/billing_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user

from app.schemas import PlanOut, SubscribeIn
from app.services.billing_service import BillingService

router = APIRouter(prefix="/billing", tags=["billing"])

@router.get("/plans", response_model=list[PlanOut])
def get_plans(db: Session = Depends(get_db)):
    svc = BillingService(db, None)
    return svc.list_plans()

@router.post("/subscribe")
def subscribe(payload: SubscribeIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = BillingService(db, user)
    return svc.subscribe(payload)
