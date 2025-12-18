# from fastapi import APIRouter, Depends
# from sqlalchemy import text
# from typing import List

# from app.db import SessionLocal
# from app.schemas import Position
# from app.main import get_current_user_row

# router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])

# @router.get("/positions", response_model=List[Position])
# def get_positions(user=Depends(get_current_user_row)):
#     """
#     Current open positions with PnL
#     """
#     db = SessionLocal()
#     try:
#         rows = db.execute(
#             text("""
#                 SELECT symbol,
#                        SUM(quantity) as qty,
#                        AVG(price) as avg_price,
#                        MAX(ltp) as ltp
#                 FROM positions
#                 WHERE user_id=:uid
#                 GROUP BY symbol
#             """),
#             {"uid": user["id"]},
#         ).fetchall()

#         out = []
#         for r in rows:
#             pnl = (r.ltp - r.avg_price) * r.qty
#             out.append(
#                 Position(
#                     symbol=r.symbol,
#                     qty=r.qty,
#                     avg_price=r.avg_price,
#                     ltp=r.ltp,
#                     pnl=pnl,
#                 )
#             )

#         return out
#     finally:
#         db.close()





# from fastapi import APIRouter, Depends
# from sqlalchemy import text
# from typing import List

# from app.db import SessionLocal
# from app.schemas import PositionOut
# from typing import List


# from app.auth import get_current_user_row


# router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])

# @router.get("/positions", response_model=List[PositionOut])
# def get_positions(user=Depends(get_current_user)):
#     """
#     Current open positions with PnL
#     """
#     db = SessionLocal()
#     try:
#         rows = db.execute(
#             text("""
#                 SELECT symbol,
#                        SUM(quantity) as qty,
#                        AVG(price) as avg_price,
#                        MAX(ltp) as ltp
#                 FROM positions
#                 WHERE user_id=:uid
#                 GROUP BY symbol
#             """),
#             {"uid": user["user_id"]},
#         ).fetchall()

#         out = []
#         for r in rows:
#             pnl = (r.ltp - r.avg_price) * r.qty
#             out.append(
#                 Position(
#                     symbol=r.symbol,
#                     qty=r.qty,
#                     avg_price=r.avg_price,
#                     ltp=r.ltp,
#                     pnl=pnl,
#                 )
#             )

#         return out
#     finally:
#         db.close()





from fastapi import APIRouter, Depends
from typing import List

from app.db import SessionLocal
from app.schemas import PositionOut
from app.auth import get_current_user_row

router = APIRouter(
    prefix="/portfolio",
    tags=["Portfolio"]
)


# -----------------------------
# DB Dependency
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -----------------------------
# GET USER POSITIONS
# -----------------------------
@router.get("/positions", response_model=List[PositionOut])
def get_positions(
    user=Depends(get_current_user_row),
    db=Depends(get_db)
):
    """
    Returns current open positions of logged-in user
    """
    user_id = user["id"]

    rows = db.execute(
        """
        SELECT symbol,
               quantity AS qty,
               avg_price,
               avg_price AS ltp,
               0 AS pnl
        FROM positions
        WHERE user_id = :uid
        """,
        {"uid": user_id}
    ).fetchall()

    return [
        PositionOut(
            symbol=r.symbol,
            qty=r.qty,
            avg_price=r.avg_price,
            ltp=r.ltp,
            pnl=r.pnl,
        )
        for r in rows
    ]
