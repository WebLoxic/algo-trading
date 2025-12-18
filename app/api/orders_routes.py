# app/api/orders_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user

from app.schemas import OrderCreate, OrderResponse
from app.services.orders_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/place", response_model=OrderResponse)
def place_order(payload: OrderCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = OrderService(db, user)
    order = svc.place_order(payload)
    return order

@router.post("/cancel/{order_id}")
def cancel_order(order_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = OrderService(db, user)
    svc.cancel_order(order_id)
    return {"ok": True}

@router.get("/history")
def list_orders(db: Session = Depends(get_db), user=Depends(get_current_user)):
    svc = OrderService(db, user)
    return svc.list_history()
