# app/services/notifications_service.py
from sqlalchemy.orm import Session

class NotificationsService:
    def __init__(self, db: Session, user):
        self.db = db
        self.user = user

    def list_notifications(self):
        # query notifications table
        return []
