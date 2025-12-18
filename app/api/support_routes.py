# app/api/support_routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user

from app.services.support_service import SupportService

router = APIRouter(prefix="/support", tags=["support"])

@router.post("/ticket")
def create_ticket(subject: str, body: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = SupportService(db, user)
    return svc.create_ticket(subject, body)

@router.get("/tickets")
def list_tickets(db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = SupportService(db, user)
    return svc.list_tickets()
