# app/services/support_service.py
from sqlalchemy.orm import Session

class SupportService:
    def __init__(self, db: Session, user):
        self.db = db
        self.user = user

    def create_ticket(self, subject: str, body: str):
        # Insert into support_tickets
        return {"ticket_id": "T1234", "subject": subject}

    def list_tickets(self):
        return []
