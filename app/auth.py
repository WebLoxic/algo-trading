


# # app/auth.py
# import os
# from datetime import datetime, timedelta
# from typing import Optional, Dict, Any

# from fastapi import Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer
# from jose import jwt, JWTError
# from passlib.context import CryptContext
# from sqlalchemy import text

# from app.db import SessionLocal

# # --------------------------------------------------
# # JWT CONFIG
# # --------------------------------------------------
# SECRET_KEY = os.getenv("JWT_SECRET", "super_secret_key_change_this")
# ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
# ACCESS_TOKEN_EXPIRE_MINUTES = int(
#     os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)
# )

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# # --------------------------------------------------
# # PASSWORD HELPERS
# # --------------------------------------------------
# def verify_password(plain: str, hashed: str) -> bool:
#     return pwd_context.verify(plain, hashed)


# def hash_password(password: str) -> str:
#     return pwd_context.hash(password)


# # --------------------------------------------------
# # TOKEN HELPERS
# # --------------------------------------------------
# def create_access_token(
#     *,
#     user_id: int,
#     email: str,
#     expires_minutes: Optional[int] = None,
# ) -> str:
#     expire = datetime.utcnow() + timedelta(
#         minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
#     )

#     payload: Dict[str, Any] = {
#         "sub": email,
#         "uid": user_id,
#         "exp": expire,
#     }

#     return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# # --------------------------------------------------
# # 🔑 MAIN DEPENDENCY (IMPORTANT)
# # --------------------------------------------------
# def get_current_user_row(
#     token: str = Depends(oauth2_scheme),
# ) -> Dict[str, Any]:
#     """
#     ✅ SINGLE SOURCE OF TRUTH
#     Used by:
#     - help_routes
#     - admin routes
#     - subscriptions
#     - any protected API
#     """

#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#     except JWTError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid or expired token",
#         )

#     user_id = payload.get("uid")
#     if not user_id:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid token payload",
#         )

#     db = SessionLocal()
#     try:
#         row = db.execute(
#             text("""
#                 SELECT id, email, full_name,
#                        is_active, is_superuser, created_at
#                 FROM users
#                 WHERE id = :uid
#                 LIMIT 1
#             """),
#             {"uid": user_id},
#         ).first()

#         if not row:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="User not found",
#             )

#         return dict(row._mapping)

#     finally:
#         db.close()





# app/auth.py

from typing import Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.security import JWT_SECRET_KEY, JWT_ALGORITHM

# --------------------------------------------------
# OAUTH2 CONFIG
# --------------------------------------------------
# tokenUrl is informational (Swagger ke liye)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# --------------------------------------------------
# 🔑 CURRENT USER DEPENDENCY
# --------------------------------------------------
def get_current_user_row(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    ✅ SINGLE SOURCE OF TRUTH for authenticated user
    Used by:
    - admin routes
    - subscriptions
    - protected APIs
    """

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
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
