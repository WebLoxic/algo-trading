

# # app/models/__init__.py
# """
# Safe models aggregator.

# This module collects model classes into a single namespace so other parts of the app can
# `from app.models import User, Subscription, PaymentTransaction, ...`.

# Behaviors:
# - Attempts to import SQLAlchemy Base from app.core.database (preferred) or app.db (fallback).
# - Imports auth_models first (User + PasswordReset).
# - Tolerantly imports other model modules (so dev-time partial states won't break imports).
# - Guards inline model definitions to avoid redefinition on repeated imports.

# This updated version adds explicit subscription-related models:
# - SubscriptionPlan: catalog of available plans (trial/pro/enterprise).
# - UserSubscription: concrete purchase/activation records per user (start/end/status).
# - UserFeature: denormalized fast-lookup flags like brokers_unlocked, credits.
# We keep the older inline `Subscription` model for backward compatibility, but prefer
# `UserSubscription` + `SubscriptionPlan` for new flows.
# """
# from typing import List
# from sqlalchemy import (
#     Column, Integer, Float, DateTime, JSON, Text, Boolean,
#     String, ForeignKey, UniqueConstraint, BigInteger
# )
# from sqlalchemy.sql import func
# from sqlalchemy.orm import relationship
# from .rewards_model import Reward, UserReward, Referral

# # --- Import Base (try multiple known locations) ---
# Base = None
# _base_errors: List[str] = []

# try:
#     # preferred project layout
#     from app.core.database import Base  # type: ignore
#     _BASE_SOURCE = "app.core.database"
# except Exception as exc1:
#     _base_errors.append(f"app.core.database failed: {exc1!s}")
#     try:
#         # older layout fallback
#         from app.db import Base  # type: ignore
#         _BASE_SOURCE = "app.db"
#     except Exception as exc2:
#         _base_errors.append(f"app.db failed: {exc2!s}")
#         Base = None
#         _BASE_SOURCE = None

# if Base is None:
#     raise ImportError(
#         "Could not import SQLAlchemy Base. Tried app.core.database and app.db. "
#         "Ensure one of those modules defines `Base` (declarative_base()).\n"
#         + "\n".join(_base_errors)
#     )

# # Helper to avoid duplicate class defs when reimported
# def _class_defined(name: str) -> bool:
#     return name in globals()

# # ------------------------------
# # Import core auth models first (User is used by other models)
# # ------------------------------
# try:
#     from app.models.auth_models import User, PasswordReset  # noqa: E402,F401
# except Exception as e:
#     # Auth models are core; raise clear error if missing/failing
#     raise ImportError(f"Failed to import app.models.auth_models: {e!s}")

# # ------------------------------
# # Tolerant import of other model modules present in repo
# # (we import modules so they register themselves with Base metadata)
# # ------------------------------
# _optional_model_modules = [
#     "app.models.wallet_model",
#     "app.models.wallet_utils",
#     "app.models.audit_model",
#     "app.models.backtest_models",
#     "app.models.broker_models",
#     "app.models.credits_model",
#     "app.models.marketplace_models",
#     "app.models.notifications_model",
#     "app.models.orders_model",
#     "app.models.plans_model",
#     "app.models.subscriptions_model",
#     "app.models.support_models",
# ]

# for _mod in _optional_model_modules:
#     try:
#         __import__(_mod)
#     except Exception:
#         # ignore import errors here to keep aggregator tolerant during development
#         pass

# # ------------------------------
# # Inline / fallback simple models (only if not already defined)
# # Some small lightweight models are kept inline for backward compatibility.
# # ------------------------------
# if not _class_defined("MLModelFile"):
#     class MLModelFile(Base):
#         __tablename__ = "ml_models"
#         __table_args__ = {"extend_existing": True}
#         id = Column(Integer, primary_key=True, index=True)
#         filename = Column(Text, nullable=False)
#         created_at = Column(DateTime(timezone=True), server_default=func.now())
#         rows = Column(Integer, nullable=True)
#         notes = Column(Text, nullable=True)
#         metrics = Column(JSON, nullable=True)
#         active = Column(Boolean, default=True)


# if not _class_defined("Sentiment"):
#     class Sentiment(Base):
#         __tablename__ = "sentiments"
#         __table_args__ = {"extend_existing": True}
#         id = Column(Integer, primary_key=True, index=True)
#         ticker = Column(Text, index=True)
#         score = Column(Float)
#         fetched_at = Column(DateTime(timezone=True), server_default=func.now())


# if not _class_defined("Signal"):
#     class Signal(Base):
#         __tablename__ = "signals"
#         __table_args__ = {"extend_existing": True}
#         id = Column(Integer, primary_key=True, index=True)
#         instrument_token = Column(Text, index=True)
#         tradingsymbol = Column(Text, index=True)
#         ts = Column(DateTime(timezone=True), server_default=func.now(), index=True)
#         score = Column(Float)
#         prob_up = Column(Float)
#         sentiment = Column(Float)
#         details = Column(JSON)


# if not _class_defined("Instrument"):
#     class Instrument(Base):
#         __tablename__ = "instruments"
#         __table_args__ = {"extend_existing": True}
#         id = Column(Integer, primary_key=True, index=True)
#         instrument_token = Column(Text, unique=True, index=True)
#         tradingsymbol = Column(Text, index=True)
#         yahoo_symbol = Column(Text, index=True)


# if not _class_defined("Tick"):
#     class Tick(Base):
#         __tablename__ = "ticks"
#         __table_args__ = {"extend_existing": True}
#         id = Column(Integer, primary_key=True, index=True)
#         instrument_token = Column(Text, index=True)
#         tradingsymbol = Column(Text, index=True)
#         ts = Column(DateTime(timezone=True), server_default=func.now(), index=True)
#         ltp = Column(Float)
#         raw = Column(JSON)

# # ------------------------------
# # Credential & SocialAccount inline (referencing User from auth_models)
# # ------------------------------
# if not _class_defined("Credential"):
#     class Credential(Base):
#         __tablename__ = "credentials"
#         __table_args__ = {"extend_existing": True}
#         id = Column(Integer, primary_key=True, index=True)
#         user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
#         email = Column(String(255), nullable=False, unique=True, index=True)
#         hashed_password = Column(String(255), nullable=False)
#         created_at = Column(DateTime(timezone=True), server_default=func.now())
#         last_login = Column(DateTime(timezone=True), nullable=True)
#         user = relationship("User", back_populates="credential")


# if not _class_defined("SocialAccount"):
#     class SocialAccount(Base):
#         __tablename__ = "social_accounts"
#         __table_args__ = (
#             UniqueConstraint("provider", "provider_id", name="uq_provider_providerid"),
#             {"extend_existing": True},
#         )
#         id = Column(Integer, primary_key=True, index=True)
#         user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
#         provider = Column(String(50), nullable=False)
#         provider_id = Column(String(255), nullable=False)
#         email = Column(String(255), nullable=True)
#         name = Column(String(255), nullable=True)
#         raw_profile = Column(JSON, nullable=True)
#         created_at = Column(DateTime(timezone=True), server_default=func.now())
#         user = relationship("User", back_populates="social_accounts")

# # ------------------------------
# # Subscription / Billing inline (if not provided by subscriptions_model)
# # - Keep legacy Subscription model for compatibility
# # - Add more robust models: SubscriptionPlan, UserSubscription, UserFeature
# # ------------------------------
# if not _class_defined("Subscription"):
#     class Subscription(Base):
#         __tablename__ = "subscriptions"
#         __table_args__ = {"extend_existing": True}
#         id = Column(Integer, primary_key=True, index=True)
#         user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
#         email = Column(String(255), nullable=True, index=True)
#         plan_id = Column(String(128), nullable=False, index=True)
#         plan_name = Column(String(255), nullable=True)
#         billing = Column(String(32), nullable=True)
#         amount = Column(Float, nullable=True)
#         status = Column(String(32), nullable=True, index=True)
#         started = Column(DateTime(timezone=True), nullable=True)
#         ends = Column(DateTime(timezone=True), nullable=True)
#         invoice = Column(String(255), nullable=True)
#         meta = Column(JSON, nullable=True)
#         created_at = Column(DateTime(timezone=True), server_default=func.now())
#         user = relationship("User", backref="subscriptions")

# # New: subscription plans catalog
# if not _class_defined("SubscriptionPlan"):
#     class SubscriptionPlan(Base):
#         __tablename__ = "subscription_plans"
#         __table_args__ = {"extend_existing": True}
#         id = Column(Integer, primary_key=True, index=True)
#         key_name = Column(String(128), nullable=False, unique=True, index=True)  # e.g. 'trial','pro'
#         title = Column(String(255), nullable=True)
#         monthly_price = Column(Float, nullable=True)
#         yearly_price = Column(Float, nullable=True)
#         meta = Column(JSON, nullable=True)
#         created_at = Column(DateTime(timezone=True), server_default=func.now())

# # New: user_subscriptions - persistent activation records
# if not _class_defined("UserSubscription"):
#     class UserSubscription(Base):
#         __tablename__ = "user_subscriptions"
#         __table_args__ = {"extend_existing": True}
#         id = Column(BigInteger, primary_key=True, index=True)
#         user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
#         plan_id = Column(Integer, ForeignKey("subscription_plans.id", ondelete="SET NULL"), nullable=False, index=True)
#         billing_cycle = Column(String(32), nullable=False, index=True)  # 'monthly' | 'yearly'
#         status = Column(String(32), nullable=False, index=True, default="pending")  # 'pending','active','expired','cancelled'
#         start_at = Column(DateTime(timezone=True), nullable=True, index=True)
#         end_at = Column(DateTime(timezone=True), nullable=True, index=True)
#         external_payment_id = Column(String(255), nullable=True, index=True)
#         invoice = Column(String(255), nullable=True)
#         meta = Column(JSON, nullable=True)
#         created_at = Column(DateTime(timezone=True), server_default=func.now())
#         updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

#         plan = relationship("SubscriptionPlan", backref="user_subscriptions")
#         user = relationship("User", backref="user_subscriptions")

# # New: denormalized user features for fast access (e.g. brokers unlocked)
# if not _class_defined("UserFeature"):
#     class UserFeature(Base):
#         __tablename__ = "user_features"
#         __table_args__ = {"extend_existing": True}
#         user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
#         brokers_unlocked = Column(Boolean, default=False, nullable=False)
#         credits = Column(Float, default=0.0, nullable=False)
#         meta = Column(JSON, nullable=True)
#         updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

#         user = relationship("User", backref="features")

# # ------------------------------
# # Payment / Wallet Transaction inline (if not present in payment or wallet models)
# # ------------------------------
# if not _class_defined("PaymentTransaction"):
#     class PaymentTransaction(Base):
#         __tablename__ = "payment_transactions"
#         __table_args__ = {"extend_existing": True}
#         id = Column(Integer, primary_key=True, index=True)
#         user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
#         email = Column(String(255), nullable=True, index=True)
#         amount = Column(Float, nullable=False)
#         status = Column(String(64), nullable=True)
#         note = Column(Text, nullable=True)
#         payment_id = Column(String(255), nullable=True, index=True)
#         order_id = Column(String(255), nullable=True, index=True)
#         meta = Column(JSON, nullable=True)
#         created_at = Column(DateTime(timezone=True), server_default=func.now())
#         user = relationship("User", backref="payment_transactions")

# # ------------------------------
# # Credential history inline
# # ------------------------------
# if not _class_defined("CredentialHistory"):
#     class CredentialHistory(Base):
#         __tablename__ = "credential_history"
#         __table_args__ = {"extend_existing": True}
#         id = Column(Integer, primary_key=True, index=True)
#         user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
#         email = Column(String(255), nullable=True, index=True)
#         event = Column(String(128), nullable=False)
#         meta = Column(JSON, nullable=True)
#         created_at = Column(DateTime(timezone=True), server_default=func.now())
#         user = relationship("User", backref="credential_history")

# # ------------------------------
# # If wallet_model exists it will register its classes into metadata; import if present.
# # ------------------------------
# try:
#     from app.models.wallet_model import *  # noqa: E402,F401
# except Exception:
#     # tolerate missing or failing wallet_model during early dev
#     pass

# # ------------------------------
# # Provide a canonical __all__ for easier imports
# # ------------------------------
# __all__ = [
#     # core auth
#     "User", "PasswordReset", "Credential", "SocialAccount",
#     # analytics
#     "MLModelFile", "Sentiment", "Signal", "Instrument", "Tick",
#     # billing (legacy)
#     "Subscription",
#     # billing (new)
#     "SubscriptionPlan", "UserSubscription", "UserFeature",
#     # payment
#     "PaymentTransaction", "CredentialHistory",
#     # plus: other model modules define their classes on import (e.g. orders_model, marketplace_models, etc.)
# ]





# app/models/__init__.py
"""
Safe models aggregator.

Goals:
- Single import namespace: from app.models import User, Credential, Subscription, ...
- Stable Base import
- No circular import crashes
- Auth/register flow MUST NOT break
"""

from typing import List
from sqlalchemy import (
    Column, Integer, Float, DateTime, JSON, Text, Boolean,
    String, ForeignKey, UniqueConstraint, BigInteger
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

# =====================================================
# BASE IMPORT (STRICT)
# =====================================================

Base = None
_base_errors: List[str] = []

try:
    from app.core.database import Base  # preferred
except Exception as e1:
    _base_errors.append(f"app.core.database: {e1}")
    try:
        from app.db import Base  # fallback
    except Exception as e2:
        _base_errors.append(f"app.db: {e2}")

if Base is None:
    raise ImportError(
        "SQLAlchemy Base import failed.\n" + "\n".join(_base_errors)
    )

# =====================================================
# CORE AUTH MODELS (STRICT – REQUIRED)
# =====================================================

try:
    from app.models.auth_models import User, PasswordReset
except Exception as e:
    raise ImportError(f"auth_models import failed: {e}")

# =====================================================
# SAFE OPTIONAL MODEL IMPORTS (NO CRASH)
# =====================================================

_optional_modules = [
    "app.models.wallet_model",
    "app.models.wallet_utils",
    "app.models.audit_model",
    "app.models.backtest_models",
    "app.models.broker_models",
    "app.models.credits_model",
    "app.models.marketplace_models",
    "app.models.notifications_model",
    "app.models.orders_model",
    "app.models.plans_model",
    "app.models.subscriptions_model",
    "app.models.support_models",
]

for _mod in _optional_modules:
    try:
        __import__(_mod)
    except Exception:
        pass

# =====================================================
# HELPER
# =====================================================

def _defined(name: str) -> bool:
    return name in globals()

# =====================================================
# AUTH: CREDENTIAL & SOCIAL
# =====================================================

if not _defined("Credential"):
    class Credential(Base):
        __tablename__ = "credentials"
        __table_args__ = {"extend_existing": True}

        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
        email = Column(String(255), unique=True, index=True, nullable=False)
        hashed_password = Column(String(255), nullable=False)
        created_at = Column(DateTime(timezone=True), server_default=func.now())
        last_login = Column(DateTime(timezone=True), nullable=True)

        user = relationship("User", back_populates="credential")


if not _defined("SocialAccount"):
    class SocialAccount(Base):
        __tablename__ = "social_accounts"
        __table_args__ = (
            UniqueConstraint("provider", "provider_id", name="uq_provider_providerid"),
            {"extend_existing": True},
        )

        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
        provider = Column(String(50), nullable=False)
        provider_id = Column(String(255), nullable=False)
        email = Column(String(255), nullable=True)
        name = Column(String(255), nullable=True)
        raw_profile = Column(JSON, nullable=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())

        user = relationship("User", back_populates="social_accounts")

# =====================================================
# ANALYTICS / MARKET
# =====================================================

if not _defined("MLModelFile"):
    class MLModelFile(Base):
        __tablename__ = "ml_models"
        __table_args__ = {"extend_existing": True}

        id = Column(Integer, primary_key=True, index=True)
        filename = Column(Text, nullable=False)
        created_at = Column(DateTime(timezone=True), server_default=func.now())
        rows = Column(Integer, nullable=True)
        notes = Column(Text, nullable=True)
        metrics = Column(JSON, nullable=True)
        active = Column(Boolean, default=True)


if not _defined("Sentiment"):
    class Sentiment(Base):
        __tablename__ = "sentiments"
        __table_args__ = {"extend_existing": True}

        id = Column(Integer, primary_key=True, index=True)
        ticker = Column(Text, index=True)
        score = Column(Float)
        fetched_at = Column(DateTime(timezone=True), server_default=func.now())


if not _defined("Signal"):
    class Signal(Base):
        __tablename__ = "signals"
        __table_args__ = {"extend_existing": True}

        id = Column(Integer, primary_key=True, index=True)
        instrument_token = Column(Text, index=True)
        tradingsymbol = Column(Text, index=True)
        ts = Column(DateTime(timezone=True), server_default=func.now(), index=True)
        score = Column(Float)
        prob_up = Column(Float)
        sentiment = Column(Float)
        details = Column(JSON)


if not _defined("Instrument"):
    class Instrument(Base):
        __tablename__ = "instruments"
        __table_args__ = {"extend_existing": True}

        id = Column(Integer, primary_key=True, index=True)
        instrument_token = Column(Text, unique=True, index=True)
        tradingsymbol = Column(Text, index=True)
        yahoo_symbol = Column(Text, index=True)


if not _defined("Tick"):
    class Tick(Base):
        __tablename__ = "ticks"
        __table_args__ = {"extend_existing": True}

        id = Column(Integer, primary_key=True, index=True)
        instrument_token = Column(Text, index=True)
        tradingsymbol = Column(Text, index=True)
        ts = Column(DateTime(timezone=True), server_default=func.now(), index=True)
        ltp = Column(Float)
        raw = Column(JSON)

# =====================================================
# BILLING / SUBSCRIPTION
# =====================================================

if not _defined("Subscription"):
    class Subscription(Base):
        __tablename__ = "subscriptions"
        __table_args__ = {"extend_existing": True}

        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
        email = Column(String(255), index=True)
        plan_id = Column(String(128), nullable=False)
        plan_name = Column(String(255))
        billing = Column(String(32))
        amount = Column(Float)
        status = Column(String(32), index=True)
        started = Column(DateTime(timezone=True))
        ends = Column(DateTime(timezone=True))
        invoice = Column(String(255))
        meta = Column(JSON)
        created_at = Column(DateTime(timezone=True), server_default=func.now())

        user = relationship("User", backref="subscriptions")


if not _defined("SubscriptionPlan"):
    class SubscriptionPlan(Base):
        __tablename__ = "subscription_plans"
        __table_args__ = {"extend_existing": True}

        id = Column(Integer, primary_key=True, index=True)
        key_name = Column(String(128), unique=True, index=True, nullable=False)
        title = Column(String(255))
        monthly_price = Column(Float)
        yearly_price = Column(Float)
        meta = Column(JSON)
        created_at = Column(DateTime(timezone=True), server_default=func.now())


if not _defined("UserSubscription"):
    class UserSubscription(Base):
        __tablename__ = "user_subscriptions"
        __table_args__ = {"extend_existing": True}

        id = Column(BigInteger, primary_key=True, index=True)
        user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
        plan_id = Column(Integer, ForeignKey("subscription_plans.id", ondelete="SET NULL"), index=True, nullable=False)
        billing_cycle = Column(String(32), nullable=False)
        status = Column(String(32), default="pending", index=True)
        start_at = Column(DateTime(timezone=True))
        end_at = Column(DateTime(timezone=True))
        external_payment_id = Column(String(255))
        invoice = Column(String(255))
        meta = Column(JSON)
        created_at = Column(DateTime(timezone=True), server_default=func.now())
        updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

        plan = relationship("SubscriptionPlan", backref="user_subscriptions")
        user = relationship("User", backref="user_subscriptions")


if not _defined("UserFeature"):
    class UserFeature(Base):
        __tablename__ = "user_features"
        __table_args__ = {"extend_existing": True}

        user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
        brokers_unlocked = Column(Boolean, default=False, nullable=False)
        credits = Column(Float, default=0.0, nullable=False)
        meta = Column(JSON)
        updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

        user = relationship("User", backref="features")

# =====================================================
# PAYMENTS / AUDIT
# =====================================================

if not _defined("PaymentTransaction"):
    class PaymentTransaction(Base):
        __tablename__ = "payment_transactions"
        __table_args__ = {"extend_existing": True}

        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
        email = Column(String(255), index=True)
        amount = Column(Float, nullable=False)
        status = Column(String(64))
        note = Column(Text)
        payment_id = Column(String(255), index=True)
        order_id = Column(String(255), index=True)
        meta = Column(JSON)
        created_at = Column(DateTime(timezone=True), server_default=func.now())

        user = relationship("User", backref="payment_transactions")


if not _defined("CredentialHistory"):
    class CredentialHistory(Base):
        __tablename__ = "credential_history"
        __table_args__ = {"extend_existing": True}

        id = Column(Integer, primary_key=True, index=True)
        user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
        email = Column(String(255), index=True)
        event = Column(String(128), nullable=False)
        meta = Column(JSON)
        created_at = Column(DateTime(timezone=True), server_default=func.now())

        user = relationship("User", backref="credential_history")

# =====================================================
# EXPORTS
# =====================================================

__all__ = [
    "User",
    "PasswordReset",
    "Credential",
    "SocialAccount",
    "MLModelFile",
    "Sentiment",
    "Signal",
    "Instrument",
    "Tick",
    "Subscription",
    "SubscriptionPlan",
    "UserSubscription",
    "UserFeature",
    "PaymentTransaction",
    "CredentialHistory",
]
