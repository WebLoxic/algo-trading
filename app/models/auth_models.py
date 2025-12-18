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
Authentication-related SQLAlchemy models (safe for uvicorn autoreload).

This file is written defensively so repeated import / reload during development
does not raise SQLAlchemy "Table 'users' is already defined" errors.

It also defines relationship attributes expected by other model files:
- `credential` (one-to-one -> Credential)
- `social_accounts` (one-to-many -> SocialAccount)

Use string names for relationship targets so import order / circular refs don't break.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base

# small helper — prevents double-definition in the module during reloads
def _defined(name: str) -> bool:
    return name in globals()


# Define the User model if not already defined
if not _defined("User"):
    class User(Base):
        __tablename__ = "users"
        __table_args__ = {"extend_existing": True}

        id = Column(Integer, primary_key=True, index=True)
        email = Column(String(255), unique=True, index=True, nullable=False)
        full_name = Column(String(255), nullable=True)
        hashed_password = Column(String(512), nullable=False)

        is_active = Column(Boolean, default=True)
        is_superuser = Column(Boolean, default=False)

        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

        # Relationship to PasswordReset
        password_resets = relationship(
            "PasswordReset",
            back_populates="user",
            cascade="all, delete-orphan",
        )

        # Relationship expected by app.models.__init__.py (Credential)
        credential = relationship(
            "Credential",
            uselist=False,
            back_populates="user",
            cascade="all, delete-orphan"
        )

        # Relationship expected by app.models.__init__.py (SocialAccount)
        social_accounts = relationship(
            "SocialAccount",
            back_populates="user",
            cascade="all, delete-orphan"
        )


# Define the PasswordReset model if not already defined
if not _defined("PasswordReset"):
    class PasswordReset(Base):
        __tablename__ = "password_resets"
        __table_args__ = {"extend_existing": True}

        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(
            Integer,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        )
        token = Column(String(1024), unique=True, index=True, nullable=False)
        expires_at = Column(DateTime, nullable=False)
        used = Column(Boolean, default=False)

        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

        # Relationship back to User
        user = relationship("User", back_populates="password_resets")


__all__ = ["User", "PasswordReset"]
