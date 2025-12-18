# print_columns.py
import os, sys
sys.path.insert(0, os.path.abspath("."))

from app.models.wallet_model import WalletTransaction

print("\nWalletTransaction columns detected by SQLAlchemy:")
print([c.name for c in WalletTransaction.__table__.columns])
