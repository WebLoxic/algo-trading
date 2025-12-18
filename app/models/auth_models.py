# # app/models/auth_models.py
# """
# Authentication-related SQLAlchemy models (safe for uvicorn autoreload).

# This file is written defensively so repeated import / reload during development
# does not raise SQLAlchemy "Table 'users' is already defined" errors.

# It also defines relationship attributes expected by other model files:
# - `credential` (one-to-one -> Credential)
# - `social_accounts` (one-to-many -> SocialAccount)

# Use string names for relationship targets so import order / circular refs don't break.
# """

# from datetime import datetime
# from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
# from sqlalchemy.orm import relationship
# from app.db import Base

# # small helper — prevents double-definition in the module during reloads
# def _defined(name: str) -> bool:
#     return name in globals()


# if not _defined("User"):
#     class User(Base):
#         __tablename__ = "users"
#         __table_args__ = {"extend_existing": True}

#         id = Column(Integer, primary_key=True, index=True)
#         email = Column(String(255), unique=True, index=True, nullable=False)
#         full_name = Column(String(255), nullable=True)
#         hashed_password = Column(String(512), nullable=False)

#         is_active = Column(Boolean, default=True)
#         is_superuser = Column(Boolean, default=False)

#         created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

#         # relationship to PasswordReset (defined here or elsewhere)
#         password_resets = relationship(
#             "PasswordReset",
#             back_populates="user",
#             cascade="all, delete-orphan",
#         )

#         # Relationship expected by app.models.__init__.py Credential.user
#         # Credential.user has back_populates="credential" -> so here we name attribute `credential`
#         credential = relationship(
#             "Credential",
#             uselist=False,
#             back_populates="user",
#             cascade="all, delete-orphan"
#         )

#         # Relationship expected by app.models.__init__.py SocialAccount.user
#         social_accounts = relationship(
#             "SocialAccount",
#             back_populates="user",
#             cascade="all, delete-orphan"
#         )


# if not _defined("PasswordReset"):
#     class PasswordReset(Base):
#         __tablename__ = "password_resets"
#         __table_args__ = {"extend_existing": True}

#         id = Column(Integer, primary_key=True, index=True)
#         user_id = Column(
#             Integer,
#             ForeignKey("users.id", ondelete="CASCADE"),
#             nullable=False,
#         )
#         token = Column(String(1024), unique=True, index=True, nullable=False)
#         expires_at = Column(DateTime, nullable=False)
#         used = Column(Boolean, default=False)

#         created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

#         user = relationship("User", back_populates="password_resets")


# __all__ = ["User", "PasswordReset"]




"""
Authentication-related SQLAlchemy models.

Safe for:
- uvicorn --reload
- multiple imports
- circular references

This file defines ONLY core auth tables:
- User
- PasswordReset

Password storage rule (IMPORTANT):
- Actual password hash lives in `credentials` table
- User table DOES NOT store password
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

# IMPORTANT: Base must come from SAME place as models/__init__.py
from app.core.database import Base


# -------------------------------------------------
# Helper to avoid duplicate class definition
# -------------------------------------------------
def _defined(name: str) -> bool:
    return name in globals()


# -------------------------------------------------
# USER MODEL
# -------------------------------------------------
if not _defined("User"):
    class User(Base):
        __tablename__ = "users"
        __table_args__ = {"extend_existing": True}

        id = Column(Integer, primary_key=True, index=True)

        email = Column(String(255), unique=True, index=True, nullable=False)
        full_name = Column(String(255), nullable=True)

        # USER STATE
        is_active = Column(Boolean, default=True, nullable=False)
        is_superuser = Column(Boolean, default=False, nullable=False)

        created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

        # -------------------------
        # RELATIONSHIPS
        # -------------------------

        # Password resets
        password_resets = relationship(
            "PasswordReset",
            back_populates="user",
            cascade="all, delete-orphan",
        )

        # One-to-one credential (actual password hash)
        credential = relationship(
            "Credential",
            uselist=False,
            back_populates="user",
            cascade="all, delete-orphan"
        )

        # Social logins
        social_accounts = relationship(
            "SocialAccount",
            back_populates="user",
            cascade="all, delete-orphan"
        )


# -------------------------------------------------
# PASSWORD RESET MODEL
# -------------------------------------------------
if not _defined("PasswordReset"):
    class PasswordReset(Base):
        __tablename__ = "password_resets"
        __table_args__ = {"extend_existing": True}

        id = Column(Integer, primary_key=True, index=True)

        user_id = Column(
            Integer,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )

        token = Column(String(1024), unique=True, index=True, nullable=False)
        expires_at = Column(DateTime(timezone=True), nullable=False)
        used = Column(Boolean, default=False, nullable=False)

        created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

        # Relationship back to User
        user = relationship(
            "User",
            back_populates="password_resets"
        )


__all__ = ["User", "PasswordReset"]
