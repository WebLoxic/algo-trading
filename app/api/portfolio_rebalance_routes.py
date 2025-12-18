from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List

from app.main import get_current_user_row
from app.services.portfolio_rebalancer import rebalance_preview
from app.services.portfolio_executor import execute_rebalance

router = APIRouter(
    prefix="/portfolio/rebalance",
    tags=["Portfolio-Rebalancer"]
)

# ============================
# SCHEMAS
# ============================

class Target(BaseModel):
    symbol: str
    weight: float   # percentage

class RebalanceRequest(BaseModel):
    basket_name: str
    capital: float
    targets: List[Target]


# ============================
# PREVIEW (NO ORDERS)
# ============================
@router.post("/preview")
def preview(payload: RebalanceRequest, user=Depends(get_current_user_row)):
    actions = rebalance_preview(
        user_id=user["id"],
        capital=payload.capital,
        targets=[t.dict() for t in payload.targets]
    )

    return {
        "basket": payload.basket_name,
        "actions": actions
    }


# ============================
# EXECUTE (LIVE / PAPER)
# ============================
@router.post("/execute")
def execute(
    payload: RebalanceRequest,
    access_token: str | None = None,
    user=Depends(get_current_user_row),
):
    actions = rebalance_preview(
        user_id=user["id"],
        capital=payload.capital,
        targets=[t.dict() for t in payload.targets]
    )

    if not actions:
        raise HTTPException(400, "Portfolio already balanced")

    order_ids = execute_rebalance(
        user_id=user["id"],
        actions=actions,
        access_token=access_token
    )

    return {
        "basket": payload.basket_name,
        "orders_placed": order_ids
    }
