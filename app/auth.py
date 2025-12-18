# # app/auth.py
# import os
# from dotenv import load_dotenv
# from passlib.context import CryptContext
# from datetime import datetime, timedelta
# from typing import Optional, Dict, Any

# from fastapi import Depends, HTTPException
# from fastapi.security import OAuth2PasswordBearer
# from jose import jwt, JWTError

# # --------------------------------------------------
# # ENV & SETTINGS
# # --------------------------------------------------
# load_dotenv()

# SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
# ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
# ACCESS_TOKEN_EXPIRE_MINUTES = int(
#     os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24)
# )

# # OAuth2
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# # --------------------------------------------------
# # PASSWORD UTILS
# # --------------------------------------------------
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     return pwd_context.verify(plain_password, hashed_password)

# def get_password_hash(password: str) -> str:
#     return pwd_context.hash(password)

# # --------------------------------------------------
# # JWT TOKEN CREATE
# # --------------------------------------------------
# def create_access_token(
#     subject: str,
#     uid: Optional[int] = None,
#     broker: str = "zerodha",
#     expires_delta: Optional[int] = None,
# ) -> str:
#     """
#     Create JWT token used across REST + WS

#     Payload contains:
#     - sub     : email / username
#     - uid     : user_id
#     - broker  : selected broker
#     - exp     : expiry
#     """
#     if expires_delta is None:
#         expires_delta = ACCESS_TOKEN_EXPIRE_MINUTES

#     expire = datetime.utcnow() + timedelta(minutes=expires_delta)

#     to_encode = {
#         "sub": str(subject),
#         "uid": uid,
#         "broker": broker,
#         "exp": expire,
#     }

#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt

# # --------------------------------------------------
# # CURRENT USER DEPENDENCY (MOST IMPORTANT)
# # --------------------------------------------------
# def get_current_user(
#     token: str = Depends(oauth2_scheme),
# ) -> Dict[str, Any]:
#     """
#     Used in:
#     - REST APIs
#     - WebSocket auth (via token)
#     - Permissions / broker routing
#     """
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#     except JWTError:
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid or expired token",
#         )

#     user_id = payload.get("uid")
#     email = payload.get("sub")

#     if not user_id or not email:
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid token payload",
#         )

#     return {
#         "user_id": user_id,
#         "email": email,
#         "broker": payload.get("broker", "zerodha"),
#         "token_exp": payload.get("exp"),
#     }




# app/auth.py
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import text

from app.db import SessionLocal

# --------------------------------------------------
# JWT CONFIG
# --------------------------------------------------
SECRET_KEY = os.getenv("JWT_SECRET", "super_secret_key_change_this")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --------------------------------------------------
# PASSWORD HELPERS
# --------------------------------------------------
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


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
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# --------------------------------------------------
# 🔑 MAIN DEPENDENCY (IMPORTANT)
# --------------------------------------------------
def get_current_user_row(
    token: str = Depends(oauth2_scheme),
) -> Dict[str, Any]:
    """
    ✅ SINGLE SOURCE OF TRUTH
    Used by:
    - help_routes
    - admin routes
    - subscriptions
    - any protected API
    """

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("uid")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    db = SessionLocal()
    try:
        row = db.execute(
            text("""
                SELECT id, email, full_name,
                       is_active, is_superuser, created_at
                FROM users
                WHERE id = :uid
                LIMIT 1
            """),
            {"uid": user_id},
        ).first()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        return dict(row._mapping)

    finally:
        db.close()
