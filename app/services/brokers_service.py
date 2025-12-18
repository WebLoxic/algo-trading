# app/services/brokers_service.py
from sqlalchemy.orm import Session
from typing import List, Dict, Any

class BrokerService:
    def __init__(self, db: Session, user: dict):
        self.db = db
        self.user = user

    def list_status(self) -> List[Dict[str, Any]]:
        # TODO: pull connected providers from broker_providers/broker_tokens
        return [{"provider": "zerodha", "connected": False}, {"provider": "upstox", "connected": False}]

    def start_connect(self, provider: str) -> str:
        # TODO: build provider-specific connect URL and return
        # Example: return f"{BACKEND}/api/brokers/start?provider={provider}"
        return f"https://example.com/connect/{provider}"

    def disconnect(self, provider: str):
        # TODO: delete tokens, close sessions
        pass

    def list_accounts(self):
        # TODO: query broker_accounts for current user
        return []
