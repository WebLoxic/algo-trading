# config.py
import os
from dotenv import load_dotenv
load_dotenv()

KITE_API_KEY = os.getenv("KITE_API_KEY", "")
KITE_API_SECRET = os.getenv("KITE_API_SECRET", "")
KITE_REDIRECT_URL = os.getenv("KITE_REDIRECT_URL", "http://localhost:5173/")
# Path to persist tokens locally (for demo)
TOKEN_FILE = os.getenv("TOKEN_FILE", "app/storage/kite_token.json")

# Trading settings
DEFAULT_QUANTITY = int(os.getenv("DEFAULT_QUANTITY", "1"))
DEFAULT_PRODUCT = os.getenv("DEFAULT_PRODUCT", "MIS")  # MIS/NRML/CNC
DEFAULT_ORDER_TYPE = os.getenv("DEFAULT_ORDER_TYPE", "MARKET")  # MARKET/LIMIT
