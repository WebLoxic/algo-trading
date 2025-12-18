# app/api/notifications_routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user

from app.services.notifications_service import NotificationsService

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/list")
def list_notifications(db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = NotificationsService(db, user)
    return svc.list_notifications()
