# app/oauth_clients.py
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from authlib.integrations.starlette_client import OAuth

# -------------------------------------------------
# Load environment
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
dotenv_path = BASE_DIR / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    print(f"✅ Loaded .env from {dotenv_path}")
else:
    print(f"⚠️ .env not found at {dotenv_path}")

# -------------------------------------------------
# Environment Variables
# -------------------------------------------------
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID")
FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5173")

# -------------------------------------------------
# Logger
# -------------------------------------------------
log = logging.getLogger("app.oauth_clients")
log.setLevel(logging.INFO)

# -------------------------------------------------
# OAuth Client Setup
# -------------------------------------------------
oauth = OAuth()

# === Google ===
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    log.info(f"✅ Google OAuth ready ({GOOGLE_CLIENT_ID[:10]}...)")
else:
    log.warning("⚠️ Google OAuth missing credentials.")

# === Facebook ===
if FACEBOOK_CLIENT_ID and FACEBOOK_CLIENT_SECRET:
    oauth.register(
        name="facebook",
        client_id=FACEBOOK_CLIENT_ID,
        client_secret=FACEBOOK_CLIENT_SECRET,
        authorize_url="https://www.facebook.com/v10.0/dialog/oauth",
        access_token_url="https://graph.facebook.com/v10.0/oauth/access_token",
        api_base_url="https://graph.facebook.com/",
        client_kwargs={"scope": "email public_profile"},
    )
    log.info(f"✅ Facebook OAuth ready ({FACEBOOK_CLIENT_ID[:10]}...)")
else:
    log.warning("⚠️ Facebook OAuth missing credentials.")

# -------------------------------------------------
# Debug Registered Clients
# -------------------------------------------------
try:
    log.info("🔍 Registered OAuth providers: %s", list(oauth._clients.keys()))
except Exception as e:
    log.warning("⚠️ Could not inspect oauth._clients: %s", e)

# -------------------------------------------------
# Exports
# -------------------------------------------------
__all__ = ["oauth", "FRONTEND_URL", "BACKEND_URL"]
