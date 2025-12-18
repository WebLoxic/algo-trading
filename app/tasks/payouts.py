# app/tasks/payouts.py
import logging
from app.db import SessionLocal

logger = logging.getLogger(__name__)

def process_payouts():
    db = SessionLocal()
    try:
        # TODO: find approved payout requests, call payment provider / bank transfer
        logger.info("process_payouts: running (demo)")
    finally:
        db.close()
