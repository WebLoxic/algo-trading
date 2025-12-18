# apply_wallet_alters.py
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/dbname")
engine = create_engine(DATABASE_URL)

stmts = [
    "ALTER TABLE wallet_transactions ALTER COLUMN payment_id DROP NOT NULL;",
    "ALTER TABLE wallet_transactions ADD COLUMN IF NOT EXISTS provider VARCHAR(64);",
    "ALTER TABLE wallet_transactions ADD COLUMN IF NOT EXISTS currency VARCHAR(12) DEFAULT 'INR';",
    "ALTER TABLE wallet_transactions ADD COLUMN IF NOT EXISTS provider_response TEXT;",
    "ALTER TABLE wallet_transactions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT now();",
    "ALTER TABLE wallet_transactions ALTER COLUMN created_at SET DEFAULT now();"
]

with engine.begin() as conn:
    for s in stmts:
        try:
            conn.execute(text(s))
            print("OK:", s)
        except Exception as e:
            print("ERR:", s, e)
