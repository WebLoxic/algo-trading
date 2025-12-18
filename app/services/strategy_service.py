# app/services/strategy_service.py
from sqlalchemy.orm import Session
from typing import List
from app.schemas import StrategyCreate, StrategyOut

class StrategyService:
    def __init__(self, db: Session, user: dict):
        self.db = db
        self.user = user

    def create(self, payload: StrategyCreate) -> StrategyOut:
        # Save strategy to DB (marketplace or user table)
        now = __import__("datetime").datetime.utcnow().isoformat()
        return StrategyOut(id=1, title=payload.title, code=payload.code, author=self.user.get("email") if self.user else "anon", created_at=now)

    def list_all(self) -> List[StrategyOut]:
        # TODO: list user strategies from DB
        return []
