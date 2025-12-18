# app/security.py
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import jwt
from passlib.context import CryptContext

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
JWT_SECRET_KEY = os.getenv("JWT_SECRET", "super_secret_key_change_this")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --------------------------------------------------
# PASSWORD HELPERS
# --------------------------------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# --------------------------------------------------
# TOKEN HELPERS
# --------------------------------------------------
def create_access_token(
    *,
    user_id: int,
    email: str,
    expires_minutes: Optional[int] = None,
) -> str:
    expire = datetime.utcnow() + timedelta(
        minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload: Dict[str, Any] = {
        "sub": email,
        "uid": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
