# # src/backend/deps.py
# from typing import Generator, Optional
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, Session
# import os
# from fastapi import Depends, HTTPException, status, Header

# DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")  # change for prod

# engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# def get_db() -> Generator[Session, None, None]:
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # Simple admin key auth (replace with real JWT/session)
# ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "changeme_admin_key")

# def require_admin(x_api_key: Optional[str] = Header(None)):
#     if not x_api_key or x_api_key != ADMIN_API_KEY:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin auth required")
#     return True







# app/deps.py
from typing import Generator, Optional, Dict, Any

from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import text
import os

from app.db import SessionLocal
from app.main import get_current_user_row


# ======================================================
# DATABASE SESSION DEPENDENCY
# ======================================================
def get_db() -> Generator[Session, None, None]:
    """
    Provides a SQLAlchemy DB session.
    Automatically closes after request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ======================================================
# AUTHENTICATED USER DEPENDENCY (JWT BASED)
# ======================================================
def get_current_user(
    user: Dict[str, Any] = Depends(get_current_user_row),
) -> Dict[str, Any]:
    """
    Returns the current authenticated user.
    Used by most protected APIs.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


# ======================================================
# SUPER ADMIN / ADMIN DEPENDENCY (JWT ROLE BASED)
# ======================================================
def require_superuser(
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Allows access only to superusers/admins.
    """
    if not user.get("is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# ======================================================
# API KEY BASED ADMIN (OPTIONAL / LEGACY SUPPORT)
# ======================================================
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "changeme_admin_key")

def require_admin_key(
    x_api_key: Optional[str] = Header(None),
):
    """
    Legacy admin auth using API Key.
    Useful for internal tools / cron / webhooks.
    """
    if not x_api_key or x_api_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin API key",
        )
    return True


# ======================================================
# OPTIONAL: USER ID EXTRACTOR (SAFE HELPER)
# ======================================================
def get_current_user_id(
    user: Dict[str, Any] = Depends(get_current_user),
) -> int:
    """
    Returns only user ID.
    Handy for simple CRUD endpoints.
    """
    uid = user.get("id")
    if uid is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
        )
    return int(uid)
