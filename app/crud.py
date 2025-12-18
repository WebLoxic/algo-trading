


# # app/crud.py
# """
# CRUD helpers (SQLAlchemy) for models used by the algo-trader backend.

# Extended subscription-related CRUD operations:
#  - create_pending_subscription
#  - activate_subscription
#  - get_active_subscription
#  - expire_subscriptions (batch)
#  - expire_subscription_by_id (single)
#  - admin_list_subscriptions
#  - cancel_subscription
#  - extend_subscription
#  - get_user_feature / upsert_user_feature

# Notes:
#  - All DB sessions are created via SessionLocal and closed with _close_session.
#  - Time arithmetic prefers dateutil.relativedelta for correct month/year additions,
#    but falls back to a days-based approximation if dateutil is not installed.
#  - Payment provider verification is intentionally NOT implemented here; verify
#    payments in your webhook/route before calling activate_subscription().
# """
# from typing import Optional, Dict, Any, List, Tuple, Iterable
# from datetime import datetime, timedelta

# from sqlalchemy import select, desc, and_, func
# from sqlalchemy.exc import SQLAlchemyError

# from .db import SessionLocal
# from . import models

# # try to import relativedelta for exact month/year arithmetic
# try:
#     from dateutil.relativedelta import relativedelta  # type: ignore
#     _HAS_RELATIVEDELTA = True
# except Exception:
#     _HAS_RELATIVEDELTA = False


# def _close_session(session):
#     try:
#         session.close()
#     except Exception:
#         pass


# # -------------------------
# # Existing helpers (unchanged)
# # -------------------------
# def save_model_metadata(filename: str, rows: Optional[int] = None, metrics: Optional[Dict] = None,
#                         notes: Optional[str] = None, active: bool = True) -> models.MLModelFile:
#     session = SessionLocal()
#     try:
#         # If marking active, deactivate previous active models
#         if active:
#             try:
#                 session.query(models.MLModelFile).filter(models.MLModelFile.active == True).update(
#                     {models.MLModelFile.active: False}, synchronize_session=False
#                 )
#                 session.commit()
#             except Exception:
#                 session.rollback()
#         m = models.MLModelFile(
#             filename=filename,
#             rows=rows,
#             metrics=metrics or {},
#             notes=notes,
#             active=active
#         )
#         session.add(m)
#         session.commit()
#         session.refresh(m)
#         return m
#     finally:
#         _close_session(session)


# def get_latest_model() -> Optional[models.MLModelFile]:
#     session = SessionLocal()
#     try:
#         stmt = select(models.MLModelFile).order_by(desc(models.MLModelFile.created_at))
#         res = session.execute(stmt).scalars().first()
#         return res
#     finally:
#         _close_session(session)


# def list_model_versions(limit: int = 50, offset: int = 0) -> List[models.MLModelFile]:
#     session = SessionLocal()
#     try:
#         stmt = select(models.MLModelFile).order_by(desc(models.MLModelFile.created_at)).limit(limit).offset(offset)
#         return session.execute(stmt).scalars().all()
#     finally:
#         _close_session(session)


# # -------------------------
# # Sentiment
# # -------------------------
# def save_sentiment(ticker: str, score: float) -> models.Sentiment:
#     session = SessionLocal()
#     try:
#         s = models.Sentiment(ticker=ticker, score=float(score))
#         session.add(s)
#         session.commit()
#         session.refresh(s)
#         return s
#     finally:
#         _close_session(session)


# def get_latest_sentiment(ticker: str) -> Optional[models.Sentiment]:
#     session = SessionLocal()
#     try:
#         stmt = select(models.Sentiment).where(models.Sentiment.ticker == ticker).order_by(desc(models.Sentiment.fetched_at))
#         res = session.execute(stmt).scalars().first()
#         return res
#     finally:
#         _close_session(session)


# def list_sentiment_history(ticker: str, limit: int = 100) -> List[models.Sentiment]:
#     session = SessionLocal()
#     try:
#         stmt = select(models.Sentiment).where(models.Sentiment.ticker == ticker).order_by(desc(models.Sentiment.fetched_at)).limit(limit)
#         return session.execute(stmt).scalars().all()
#     finally:
#         _close_session(session)


# # -------------------------
# # Signals
# # -------------------------
# def save_signal(signal_dict: Dict[str, Any]) -> models.Signal:
#     session = SessionLocal()
#     try:
#         ts_val = signal_dict.get("ts")
#         if isinstance(ts_val, str):
#             try:
#                 ts_val = datetime.fromisoformat(ts_val)
#             except Exception:
#                 ts_val = None

#         s = models.Signal(
#             instrument_token=str(signal_dict.get("instrument_token") or signal_dict.get("token") or ""),
#             tradingsymbol=signal_dict.get("tradingsymbol") or signal_dict.get("symbol"),
#             ts=ts_val,
#             score=signal_dict.get("score"),
#             prob_up=signal_dict.get("prob_up"),
#             sentiment=signal_dict.get("sentiment"),
#             details=signal_dict.get("details") or signal_dict
#         )
#         session.add(s)
#         session.commit()
#         session.refresh(s)
#         return s
#     finally:
#         _close_session(session)


# def list_signals(limit: int = 100, offset: int = 0) -> List[models.Signal]:
#     session = SessionLocal()
#     try:
#         stmt = select(models.Signal).order_by(desc(models.Signal.ts)).limit(limit).offset(offset)
#         return session.execute(stmt).scalars().all()
#     finally:
#         _close_session(session)


# # -------------------------
# # Orders
# # -------------------------
# def save_order(order_payload: Dict[str, Any]) -> Optional[models.Signal]:
#     session = SessionLocal()
#     try:
#         payload = dict(order_payload or {})
#         ts_val = payload.get("ts") or payload.get("timestamp")
#         if isinstance(ts_val, str):
#             try:
#                 ts_val = datetime.fromisoformat(ts_val)
#             except Exception:
#                 ts_val = None

#         tradingsymbol = payload.get("tradingsymbol") or payload.get("symbol")
#         instrument_token = payload.get("instrument_token") or payload.get("token") or payload.get("instrument")
#         details = payload

#         s = models.Signal(
#             instrument_token=str(instrument_token) if instrument_token is not None else "",
#             tradingsymbol=tradingsymbol,
#             ts=ts_val,
#             score=None,
#             prob_up=None,
#             sentiment=None,
#             details=details
#         )
#         session.add(s)
#         session.commit()
#         session.refresh(s)
#         return s
#     except SQLAlchemyError:
#         session.rollback()
#         raise
#     finally:
#         _close_session(session)


# def list_orders(limit: int = 100, offset: int = 0) -> List[models.Signal]:
#     return list_signals(limit=limit, offset=offset)


# # -------------------------
# # Subscriptions & Billing CRUD (improved)
# # -------------------------
# def _now_utc() -> datetime:
#     return datetime.utcnow()


# def _normalize_billing(billing: str) -> str:
#     if not billing:
#         return "monthly"
#     b = billing.strip().lower()
#     if b in ("month", "monthly", "m"):
#         return "monthly"
#     if b in ("year", "yearly", "annual", "annually", "y"):
#         return "yearly"
#     return "monthly"


# def create_pending_subscription(user_id: int, plan_id: int, billing_cycle: str, meta: Optional[Dict[str, Any]] = None) -> models.UserSubscription:
#     """
#     Create a pending subscription record for the user.
#     Writes created_at timestamp and returns the new UserSubscription model instance.
#     """
#     session = SessionLocal()
#     try:
#         billing_norm = _normalize_billing(billing_cycle)
#         now = _now_utc()
#         s = models.UserSubscription(
#             user_id=user_id,
#             plan_id=plan_id,
#             billing_cycle=billing_norm,
#             status="pending",
#             meta=meta or {},
#             created_at=now,
#             updated_at=now
#         )
#         session.add(s)
#         session.commit()
#         session.refresh(s)
#         return s
#     except SQLAlchemyError:
#         session.rollback()
#         raise
#     finally:
#         _close_session(session)


# def _add_interval_to(dt: datetime, billing_cycle: str) -> datetime:
#     """
#     Add one billing interval to dt according to billing_cycle.
#     Uses dateutil.relativedelta if available, otherwise uses an approximation.
#     """
#     if _HAS_RELATIVEDELTA:
#         if billing_cycle in ("yearly", "annual", "annually"):
#             return dt + relativedelta(years=1)
#         else:
#             return dt + relativedelta(months=1)
#     if billing_cycle in ("yearly", "annual", "annually"):
#         return dt + timedelta(days=365)
#     return dt + timedelta(days=30)


# def _mark_subscription_active_and_unlock_features(session, s: models.UserSubscription, payment_id: str, provider: Optional[str], provider_payload: Optional[Dict[str, Any]]):
#     """
#     Internal helper to mark a subscription as active and upsert user features.
#     Assumes caller holds a session and s is a persistent model instance.
#     """
#     start = _now_utc()
#     end = _add_interval_to(start, s.billing_cycle)

#     s.status = "active"
#     s.start_at = start
#     s.end_at = end
#     s.external_payment_id = payment_id
#     if provider:
#         s.meta = (s.meta or {})
#         try:
#             # merge provider info in meta safely
#             s.meta.update({"provider": provider, "provider_payload": provider_payload or {}})
#         except Exception:
#             s.meta = {"provider": provider, "provider_payload": provider_payload or {}}
#     s.updated_at = _now_utc()
#     session.add(s)

#     uf = session.query(models.UserFeature).filter(models.UserFeature.user_id == s.user_id).with_for_update().first()
#     if not uf:
#         uf = models.UserFeature(user_id=s.user_id, brokers_unlocked=True, credits=0.0, meta={})
#         session.add(uf)
#     else:
#         uf.brokers_unlocked = True
#         session.add(uf)
#     # leave committing to caller


# def activate_subscription(subscription_id: int, payment_id: str, provider: Optional[str] = None, provider_payload: Optional[Dict[str, Any]] = None) -> Optional[models.UserSubscription]:
#     """
#     Mark a pending subscription as active. This MUST be called only after server-side payment verification.
#     - sets start_at to utc now, end_at according to billing_cycle
#     - sets status to 'active'
#     - writes external_payment_id
#     - creates/updates user_features.brokers_unlocked = True
#     Returns updated UserSubscription or None if not found.
#     """
#     session = SessionLocal()
#     try:
#         s = session.query(models.UserSubscription).filter(models.UserSubscription.id == subscription_id).with_for_update().first()
#         if not s:
#             return None

#         # If already active with same payment id, return as-is
#         if s.status == "active" and getattr(s, "external_payment_id", None) == payment_id:
#             session.refresh(s)
#             return s

#         # Use helper to update s and upsert features
#         _mark_subscription_active_and_unlock_features(session, s, payment_id, provider, provider_payload)

#         session.commit()
#         session.refresh(s)
#         return s
#     except SQLAlchemyError:
#         session.rollback()
#         raise
#     finally:
#         _close_session(session)


# def get_active_subscription(user_id: int) -> Optional[models.UserSubscription]:
#     """
#     Return the most-recent active subscription for user (if any), else None.
#     Active means status == 'active' and now is between start_at and end_at.
#     """
#     session = SessionLocal()
#     try:
#         now = _now_utc()
#         stmt = select(models.UserSubscription).where(
#             and_(
#                 models.UserSubscription.user_id == user_id,
#                 models.UserSubscription.status == "active",
#                 models.UserSubscription.start_at <= now,
#                 models.UserSubscription.end_at > now
#             )
#         ).order_by(desc(models.UserSubscription.end_at)).limit(1)
#         res = session.execute(stmt).scalars().first()
#         return res
#     finally:
#         _close_session(session)


# def get_user_feature(user_id: int) -> Optional[models.UserFeature]:
#     """
#     Return denormalized user feature row if present.
#     """
#     session = SessionLocal()
#     try:
#         uf = session.query(models.UserFeature).filter(models.UserFeature.user_id == user_id).first()
#         return uf
#     finally:
#         _close_session(session)


# def upsert_user_feature(user_id: int, brokers_unlocked: Optional[bool] = None, credits: Optional[float] = None, meta: Optional[Dict[str, Any]] = None) -> models.UserFeature:
#     """
#     Create or update a user_features record.
#     """
#     session = SessionLocal()
#     try:
#         uf = session.query(models.UserFeature).filter(models.UserFeature.user_id == user_id).with_for_update().first()
#         if not uf:
#             uf = models.UserFeature(
#                 user_id=user_id,
#                 brokers_unlocked=bool(brokers_unlocked) if brokers_unlocked is not None else False,
#                 credits=float(credits or 0.0),
#                 meta=meta or {}
#             )
#             session.add(uf)
#         else:
#             if brokers_unlocked is not None:
#                 uf.brokers_unlocked = bool(brokers_unlocked)
#             if credits is not None:
#                 uf.credits = float(credits)
#             if meta is not None:
#                 uf.meta = meta
#             session.add(uf)
#         session.commit()
#         session.refresh(uf)
#         return uf
#     except SQLAlchemyError:
#         session.rollback()
#         raise
#     finally:
#         _close_session(session)


# def expire_subscriptions() -> Tuple[int, Iterable[int]]:
#     """
#     Mark subscriptions as expired if end_at <= now and status == 'active'.
#     For each user whose subscriptions expired, lock their features if they have no other active subs.
#     Returns (num_expired, list_of_user_ids_processed).
#     Intended to be called by a scheduler (APScheduler, cron job, Celery beat, etc).
#     """
#     session = SessionLocal()
#     try:
#         now = _now_utc()
#         subs_to_expire = session.query(models.UserSubscription).filter(
#             and_(
#                 models.UserSubscription.status == "active",
#                 models.UserSubscription.end_at <= now
#             )
#         ).all()

#         if not subs_to_expire:
#             return 0, []

#         user_ids = set()
#         for s in subs_to_expire:
#             s.status = "expired"
#             s.updated_at = now
#             session.add(s)
#             user_ids.add(s.user_id)

#         session.commit()

#         processed_users = []
#         for uid in user_ids:
#             other_active_count = session.query(func.count(models.UserSubscription.id)).filter(
#                 and_(
#                     models.UserSubscription.user_id == uid,
#                     models.UserSubscription.status == "active",
#                     models.UserSubscription.end_at > now
#                 )
#             ).scalar() or 0

#             if other_active_count == 0:
#                 uf = session.query(models.UserFeature).filter(models.UserFeature.user_id == uid).first()
#                 if uf:
#                     uf.brokers_unlocked = False
#                     session.add(uf)
#                 else:
#                     uf = models.UserFeature(user_id=uid, brokers_unlocked=False)
#                     session.add(uf)
#                 session.commit()
#             processed_users.append(uid)

#         return len(subs_to_expire), processed_users
#     except SQLAlchemyError:
#         session.rollback()
#         raise
#     finally:
#         _close_session(session)


# def expire_subscription_by_id(subscription_id: int) -> bool:
#     """
#     Expire a single subscription by id. Returns True if subscription was found and expired.
#     Useful for scheduling per-subscription expiry (callable by a scheduler job specific to one subscription).
#     """
#     session = SessionLocal()
#     try:
#         now = _now_utc()
#         s = session.query(models.UserSubscription).filter(models.UserSubscription.id == subscription_id).with_for_update().first()
#         if not s:
#             return False
#         if s.status != "active":
#             # nothing to do
#             return False
#         s.status = "expired"
#         s.updated_at = now
#         session.add(s)
#         session.commit()

#         # ensure user's features are locked if no other active subscriptions exist
#         other_active_count = session.query(func.count(models.UserSubscription.id)).filter(
#             and_(
#                 models.UserSubscription.user_id == s.user_id,
#                 models.UserSubscription.status == "active",
#                 models.UserSubscription.end_at > now
#             )
#         ).scalar() or 0

#         if other_active_count == 0:
#             uf = session.query(models.UserFeature).filter(models.UserFeature.user_id == s.user_id).first()
#             if uf:
#                 uf.brokers_unlocked = False
#                 session.add(uf)
#             else:
#                 uf = models.UserFeature(user_id=s.user_id, brokers_unlocked=False)
#                 session.add(uf)
#             session.commit()

#         return True
#     except SQLAlchemyError:
#         session.rollback()
#         raise
#     finally:
#         _close_session(session)


# # -------------------------
# # Admin helpers
# # -------------------------
# def admin_list_subscriptions(status: Optional[str] = None, limit: int = 200, offset: int = 0) -> List[models.UserSubscription]:
#     """
#     Return list of subscriptions for admin UI. Filter by status if provided.
#     """
#     session = SessionLocal()
#     try:
#         q = session.query(models.UserSubscription).order_by(desc(models.UserSubscription.created_at))
#         if status:
#             q = q.filter(models.UserSubscription.status == status)
#         if offset:
#             q = q.offset(offset)
#         if limit:
#             q = q.limit(limit)
#         rows = q.all()
#         return rows
#     finally:
#         _close_session(session)


# def cancel_subscription(subscription_id: int, admin_note: Optional[str] = None) -> Optional[models.UserSubscription]:
#     """
#     Cancel a subscription (admin action or user-initiated cancellation).
#     This sets status='cancelled' and clears features if no other active subscriptions exist.
#     """
#     session = SessionLocal()
#     try:
#         s = session.query(models.UserSubscription).filter(models.UserSubscription.id == subscription_id).with_for_update().first()
#         if not s:
#             return None
#         s.status = "cancelled"
#         if admin_note:
#             s.meta = (s.meta or {})
#             s.meta.update({"cancelled_note": admin_note, "cancelled_at": datetime.utcnow().isoformat()})
#         s.updated_at = _now_utc()
#         session.add(s)
#         session.commit()

#         # check if user has any active subscriptions remaining
#         now = _now_utc()
#         other_active_count = session.query(func.count(models.UserSubscription.id)).filter(
#             and_(
#                 models.UserSubscription.user_id == s.user_id,
#                 models.UserSubscription.status == "active",
#                 models.UserSubscription.end_at > now
#             )
#         ).scalar() or 0

#         if other_active_count == 0:
#             uf = session.query(models.UserFeature).filter(models.UserFeature.user_id == s.user_id).first()
#             if uf:
#                 uf.brokers_unlocked = False
#                 session.add(uf)
#             else:
#                 uf = models.UserFeature(user_id=s.user_id, brokers_unlocked=False)
#                 session.add(uf)
#             session.commit()

#         session.refresh(s)
#         return s
#     except SQLAlchemyError:
#         session.rollback()
#         raise
#     finally:
#         _close_session(session)


# def extend_subscription(subscription_id: int, extra_interval_count: int = 1, billing_cycle: Optional[str] = None) -> Optional[models.UserSubscription]:
#     """
#     Extend a subscription by extra_interval_count billing intervals.
#     If billing_cycle is provided, use it; otherwise use the subscription's billing_cycle.
#     Example: extend_subscription(123, extra_interval_count=1, billing_cycle='monthly')
#     """
#     session = SessionLocal()
#     try:
#         s = session.query(models.UserSubscription).filter(models.UserSubscription.id == subscription_id).with_for_update().first()
#         if not s:
#             return None
#         cycle = _normalize_billing(billing_cycle or s.billing_cycle or "monthly")
#         # determine base end datetime (if end_at is None or in past, use utcnow)
#         now = _now_utc()
#         base = s.end_at if s.end_at and s.end_at > now else now
#         new_end = base
#         for _ in range(max(0, extra_interval_count)):
#             new_end = _add_interval_to(new_end, cycle)
#         s.end_at = new_end
#         s.status = "active"
#         s.updated_at = _now_utc()
#         session.add(s)
#         session.commit()
#         session.refresh(s)
#         return s
#     except SQLAlchemyError:
#         session.rollback()
#         raise
#     finally:
#         _close_session(session)


# # -------------------------
# # Utility
# # -------------------------
# def ping_db() -> bool:
#     session = SessionLocal()
#     try:
#         session.execute("SELECT 1")
#         return True
#     except Exception:
#         return False
#     finally:
#         _close_session(session)


# """
# CRUD for subscriptions and features.
# Uses only user_subscriptions table.
# """

# from typing import Optional, Dict, Any, List
# from datetime import datetime, timedelta

# from sqlalchemy.orm import Session
# from sqlalchemy import desc
# from .db import SessionLocal
# from . import models

# try:
#     from dateutil.relativedelta import relativedelta
#     _HAS_RELD = True
# except ImportError:
#     _HAS_RELD = False


# def _now() -> datetime:
#     return datetime.utcnow()


# def normalize_billing(billing: str) -> str:
#     if not billing:
#         return "monthly"
#     b = billing.lower()
#     if b in ("monthly", "month", "m"):
#         return "monthly"
#     if b in ("yearly", "annual", "y"):
#         return "yearly"
#     return "monthly"


# def add_interval(dt: datetime, billing: str) -> datetime:
#     if _HAS_RELD:
#         return dt + (relativedelta(months=1) if billing == "monthly" else relativedelta(years=1))
#     return dt + (timedelta(days=30) if billing == "monthly" else timedelta(days=365))


# # ----------------------------------------------------------
# # CREATE PENDING SUBSCRIPTION
# # ----------------------------------------------------------
# def create_pending_subscription(user_id: int, plan_id: int, billing_cycle: str, meta: Optional[Dict[str, Any]] = None, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True

#         sub = models.UserSubscription(
#             user_id=user_id,
#             plan_id=plan_id,
#             billing_cycle=normalize_billing(billing_cycle),
#             status="pending",
#             meta=meta or {},
#             created_at=_now(),
#             updated_at=_now()
#         )
#         session.add(sub)

#         if own_session:
#             session.commit()
#             session.refresh(sub)
#         else:
#             session.commit()  # <-- FORCE commit for external sessions

#         return sub
#     finally:
#         if own_session:
#             session.close()


# # ----------------------------------------------------------
# # ACTIVATE SUBSCRIPTION
# # ----------------------------------------------------------
# def activate_subscription(subscription_id: int, payment_id: str, provider: str = "razorpay", provider_payload: Optional[Dict[str, Any]] = None, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True

#         sub = session.query(models.UserSubscription).filter(models.UserSubscription.id == subscription_id).with_for_update().first()
#         if not sub:
#             return None

#         sub.status = "active"
#         sub.start_at = _now()
#         sub.end_at = add_interval(sub.start_at, sub.billing_cycle)
#         sub.external_payment_id = payment_id
#         sub.updated_at = _now()

#         # Meta handling
#         meta = sub.meta or {}
#         if not isinstance(meta, dict):
#             import json
#             try:
#                 meta = json.loads(meta)
#             except Exception:
#                 meta = {"_prev_meta": str(meta)}
#         meta["provider"] = provider
#         meta["provider_payload"] = provider_payload or {}
#         sub.meta = meta

#         # Unlock user feature
#         uf = session.query(models.UserFeature).filter(models.UserFeature.user_id == sub.user_id).with_for_update().first()
#         if not uf:
#             uf = models.UserFeature(user_id=sub.user_id, brokers_unlocked=True, credits=0.0)
#             session.add(uf)
#         else:
#             uf.brokers_unlocked = True

#         if own_session:
#             session.commit()
#             session.refresh(sub)
#         else:
#             session.commit()  # <-- FORCE commit for external sessions

#         return sub
#     finally:
#         if own_session:
#             session.close()


# # ----------------------------------------------------------
# # GET ACTIVE / ALL SUBSCRIPTIONS
# # ----------------------------------------------------------
# def get_active_subscription(user_id: int, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         now = _now()
#         return session.query(models.UserSubscription).filter(
#             models.UserSubscription.user_id == user_id,
#             models.UserSubscription.status == "active",
#             models.UserSubscription.start_at <= now,
#             models.UserSubscription.end_at > now
#         ).order_by(desc(models.UserSubscription.end_at)).first()
#     finally:
#         if own_session:
#             session.close()


# def get_all_subscriptions(user_id: int, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         return session.query(models.UserSubscription).filter(
#             models.UserSubscription.user_id == user_id
#         ).order_by(desc(models.UserSubscription.id)).all()
#     finally:
#         if own_session:
#             session.close()


# # ----------------------------------------------------------
# # ADMIN LIST / CANCEL
# # ----------------------------------------------------------
# def admin_list_subscriptions(status: Optional[str] = None, limit: int = 200, offset: int = 0, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         q = session.query(models.UserSubscription).order_by(desc(models.UserSubscription.id))
#         if status:
#             q = q.filter(models.UserSubscription.status == status)
#         return q.limit(limit).offset(offset).all()
#     finally:
#         if own_session:
#             session.close()


# def cancel_subscription(subscription_id: int, admin_note: Optional[str] = None, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         sub = session.query(models.UserSubscription).filter(models.UserSubscription.id == subscription_id).with_for_update().first()
#         if not sub:
#             return None
#         sub.status = "cancelled"
#         sub.updated_at = _now()
#         meta = sub.meta or {}
#         if admin_note:
#             meta["cancelled_note"] = admin_note
#             meta["cancelled_at"] = _now().isoformat()
#         sub.meta = meta

#         if own_session:
#             session.commit()
#             session.refresh(sub)
#         else:
#             session.commit()  # <-- FORCE commit for external sessions

#         return sub
#     finally:
#         if own_session:
#             session.close()


# # ----------------------------------------------------------
# # GET PLAN INFO
# # ----------------------------------------------------------
# def get_plan(plan_id: int, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         return session.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.id == plan_id).first()
#     finally:
#         if own_session:
#             session.close()





# # app/crud.py
# """
# Unified CRUD for subscriptions, features, and rewards.
# """

# from typing import Optional, Dict, Any, List
# from datetime import datetime, timedelta

# from sqlalchemy.orm import Session
# from sqlalchemy import desc
# from .db import SessionLocal
# from . import models

# try:
#     from dateutil.relativedelta import relativedelta
#     _HAS_RELD = True
# except ImportError:
#     _HAS_RELD = False


# def _now() -> datetime:
#     return datetime.utcnow()


# # ----------------------------
# # SUBSCRIPTION HELPERS
# # ----------------------------
# def normalize_billing(billing: str) -> str:
#     if not billing:
#         return "monthly"
#     b = billing.lower()
#     if b in ("monthly", "month", "m"):
#         return "monthly"
#     if b in ("yearly", "annual", "y"):
#         return "yearly"
#     return "monthly"


# def add_interval(dt: datetime, billing: str) -> datetime:
#     if _HAS_RELD:
#         return dt + (relativedelta(months=1) if billing == "monthly" else relativedelta(years=1))
#     return dt + (timedelta(days=30) if billing == "monthly" else timedelta(days=365))


# # ----------------------------------------------------------
# # CREATE PENDING SUBSCRIPTION
# # ----------------------------------------------------------
# def create_pending_subscription(user_id: int, plan_id: int, billing_cycle: str,
#                                 meta: Optional[Dict[str, Any]] = None, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True

#         sub = models.UserSubscription(
#             user_id=user_id,
#             plan_id=plan_id,
#             billing_cycle=normalize_billing(billing_cycle),
#             status="pending",
#             meta=meta or {},
#             created_at=_now(),
#             updated_at=_now()
#         )
#         session.add(sub)

#         if own_session:
#             session.commit()
#             session.refresh(sub)
#         else:
#             session.commit()

#         return sub
#     finally:
#         if own_session:
#             session.close()


# # ----------------------------------------------------------
# # ACTIVATE SUBSCRIPTION
# # ----------------------------------------------------------
# def activate_subscription(subscription_id: int, payment_id: str, provider: str = "razorpay",
#                           provider_payload: Optional[Dict[str, Any]] = None, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True

#         sub = session.query(models.UserSubscription).filter(
#             models.UserSubscription.id == subscription_id
#         ).with_for_update().first()
#         if not sub:
#             return None

#         sub.status = "active"
#         sub.start_at = _now()
#         sub.end_at = add_interval(sub.start_at, sub.billing_cycle)
#         sub.external_payment_id = payment_id
#         sub.updated_at = _now()

#         meta = sub.meta or {}
#         if not isinstance(meta, dict):
#             import json
#             try:
#                 meta = json.loads(meta)
#             except Exception:
#                 meta = {"_prev_meta": str(meta)}
#         meta["provider"] = provider
#         meta["provider_payload"] = provider_payload or {}
#         sub.meta = meta

#         # Unlock user feature
#         uf = session.query(models.UserFeature).filter(
#             models.UserFeature.user_id == sub.user_id
#         ).with_for_update().first()
#         if not uf:
#             uf = models.UserFeature(user_id=sub.user_id, brokers_unlocked=True, credits=0.0)
#             session.add(uf)
#         else:
#             uf.brokers_unlocked = True

#         if own_session:
#             session.commit()
#             session.refresh(sub)
#         else:
#             session.commit()

#         return sub
#     finally:
#         if own_session:
#             session.close()


# # ----------------------------------------------------------
# # GET ACTIVE / ALL SUBSCRIPTIONS
# # ----------------------------------------------------------
# def get_active_subscription(user_id: int, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         now = _now()
#         return session.query(models.UserSubscription).filter(
#             models.UserSubscription.user_id == user_id,
#             models.UserSubscription.status == "active",
#             models.UserSubscription.start_at <= now,
#             models.UserSubscription.end_at > now
#         ).order_by(desc(models.UserSubscription.end_at)).first()
#     finally:
#         if own_session:
#             session.close()


# def get_all_subscriptions(user_id: int, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         return session.query(models.UserSubscription).filter(
#             models.UserSubscription.user_id == user_id
#         ).order_by(desc(models.UserSubscription.id)).all()
#     finally:
#         if own_session:
#             session.close()


# # ----------------------------------------------------------
# # ADMIN LIST / CANCEL
# # ----------------------------------------------------------
# def admin_list_subscriptions(status: Optional[str] = None, limit: int = 200, offset: int = 0,
#                              db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         q = session.query(models.UserSubscription).order_by(desc(models.UserSubscription.id))
#         if status:
#             q = q.filter(models.UserSubscription.status == status)
#         return q.limit(limit).offset(offset).all()
#     finally:
#         if own_session:
#             session.close()


# def cancel_subscription(subscription_id: int, admin_note: Optional[str] = None, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         sub = session.query(models.UserSubscription).filter(
#             models.UserSubscription.id == subscription_id
#         ).with_for_update().first()
#         if not sub:
#             return None
#         sub.status = "cancelled"
#         sub.updated_at = _now()
#         meta = sub.meta or {}
#         if admin_note:
#             meta["cancelled_note"] = admin_note
#             meta["cancelled_at"] = _now().isoformat()
#         sub.meta = meta

#         if own_session:
#             session.commit()
#             session.refresh(sub)
#         else:
#             session.commit()

#         return sub
#     finally:
#         if own_session:
#             session.close()


# # ----------------------------------------------------------
# # GET PLAN INFO
# # ----------------------------------------------------------
# def get_plan(plan_id: int, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         return session.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.id == plan_id).first()
#     finally:
#         if own_session:
#             session.close()


# # ----------------------------------------------------------
# # REWARDS CRUD
# # ----------------------------------------------------------
# def list_rewards(db: Session) -> List[models.Reward]:
#     return db.query(models.Reward).all()


# def get_reward(db: Session, reward_id: int) -> Optional[models.Reward]:
#     return db.query(models.Reward).filter(models.Reward.id == reward_id).first()


# def list_user_rewards(db: Session, user_id: int, active_only: bool = True) -> List[models.UserReward]:
#     query = db.query(models.UserReward).filter(models.UserReward.user_id == user_id)
#     if active_only:
#         query = query.join(models.Reward).filter(models.Reward.active == True)
#     return query.all()


# def assign_reward_to_user(db: Session, user_id: int, reward_id: int) -> models.UserReward:
#     user_reward = models.UserReward(
#         user_id=user_id,
#         reward_id=reward_id,
#         claimed=True,
#         claimed_at=datetime.utcnow()
#     )
#     db.add(user_reward)
#     db.commit()
#     db.refresh(user_reward)
#     return user_reward






# # app/crud.py
# """
# Unified CRUD for subscriptions, features, rewards, and referrals.
# """

# from typing import Optional, Dict, Any, List
# from datetime import datetime, timedelta

# from sqlalchemy.orm import Session
# from sqlalchemy import desc
# from .db import SessionLocal
# from . import models

# try:
#     from dateutil.relativedelta import relativedelta
#     _HAS_RELD = True
# except ImportError:
#     _HAS_RELD = False


# def _now() -> datetime:
#     return datetime.utcnow()


# # ----------------------------
# # SUBSCRIPTION HELPERS
# # ----------------------------
# def normalize_billing(billing: str) -> str:
#     if not billing:
#         return "monthly"
#     b = billing.lower()
#     if b in ("monthly", "month", "m"):
#         return "monthly"
#     if b in ("yearly", "annual", "y"):
#         return "yearly"
#     return "monthly"


# def add_interval(dt: datetime, billing: str) -> datetime:
#     if _HAS_RELD:
#         return dt + (relativedelta(months=1) if billing == "monthly" else relativedelta(years=1))
#     return dt + (timedelta(days=30) if billing == "monthly" else timedelta(days=365))


# # ----------------------------
# # SUBSCRIPTIONS CRUD
# # ----------------------------
# def create_pending_subscription(user_id: int, plan_id: int, billing_cycle: str,
#                                 meta: Optional[Dict[str, Any]] = None, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True

#         sub = models.UserSubscription(
#             user_id=user_id,
#             plan_id=plan_id,
#             billing_cycle=normalize_billing(billing_cycle),
#             status="pending",
#             meta=meta or {},
#             created_at=_now(),
#             updated_at=_now()
#         )
#         session.add(sub)

#         if own_session:
#             session.commit()
#             session.refresh(sub)
#         else:
#             session.commit()

#         return sub
#     finally:
#         if own_session:
#             session.close()


# def activate_subscription(subscription_id: int, payment_id: str, provider: str = "razorpay",
#                           provider_payload: Optional[Dict[str, Any]] = None, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True

#         sub = session.query(models.UserSubscription).filter(
#             models.UserSubscription.id == subscription_id
#         ).with_for_update().first()
#         if not sub:
#             return None

#         sub.status = "active"
#         sub.start_at = _now()
#         sub.end_at = add_interval(sub.start_at, sub.billing_cycle)
#         sub.external_payment_id = payment_id
#         sub.updated_at = _now()

#         meta = sub.meta or {}
#         if not isinstance(meta, dict):
#             import json
#             try:
#                 meta = json.loads(meta)
#             except Exception:
#                 meta = {"_prev_meta": str(meta)}
#         meta["provider"] = provider
#         meta["provider_payload"] = provider_payload or {}
#         sub.meta = meta

#         # Unlock user feature
#         uf = session.query(models.UserFeature).filter(
#             models.UserFeature.user_id == sub.user_id
#         ).with_for_update().first()
#         if not uf:
#             uf = models.UserFeature(user_id=sub.user_id, brokers_unlocked=True, credits=0.0)
#             session.add(uf)
#         else:
#             uf.brokers_unlocked = True

#         if own_session:
#             session.commit()
#             session.refresh(sub)
#         else:
#             session.commit()

#         return sub
#     finally:
#         if own_session:
#             session.close()


# def get_active_subscription(user_id: int, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         now = _now()
#         return session.query(models.UserSubscription).filter(
#             models.UserSubscription.user_id == user_id,
#             models.UserSubscription.status == "active",
#             models.UserSubscription.start_at <= now,
#             models.UserSubscription.end_at > now
#         ).order_by(desc(models.UserSubscription.end_at)).first()
#     finally:
#         if own_session:
#             session.close()


# def get_all_subscriptions(user_id: int, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         return session.query(models.UserSubscription).filter(
#             models.UserSubscription.user_id == user_id
#         ).order_by(desc(models.UserSubscription.id)).all()
#     finally:
#         if own_session:
#             session.close()


# def admin_list_subscriptions(status: Optional[str] = None, limit: int = 200, offset: int = 0,
#                              db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         q = session.query(models.UserSubscription).order_by(desc(models.UserSubscription.id))
#         if status:
#             q = q.filter(models.UserSubscription.status == status)
#         return q.limit(limit).offset(offset).all()
#     finally:
#         if own_session:
#             session.close()


# def cancel_subscription(subscription_id: int, admin_note: Optional[str] = None, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         sub = session.query(models.UserSubscription).filter(
#             models.UserSubscription.id == subscription_id
#         ).with_for_update().first()
#         if not sub:
#             return None
#         sub.status = "cancelled"
#         sub.updated_at = _now()
#         meta = sub.meta or {}
#         if admin_note:
#             meta["cancelled_note"] = admin_note
#             meta["cancelled_at"] = _now().isoformat()
#         sub.meta = meta

#         if own_session:
#             session.commit()
#             session.refresh(sub)
#         else:
#             session.commit()

#         return sub
#     finally:
#         if own_session:
#             session.close()


# def get_plan(plan_id: int, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         return session.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.id == plan_id).first()
#     finally:
#         if own_session:
#             session.close()


# # ----------------------------
# # REWARDS CRUD
# # ----------------------------
# def list_rewards(db: Session) -> List[models.Reward]:
#     return db.query(models.Reward).all()


# def get_reward(db: Session, reward_id: int) -> Optional[models.Reward]:
#     return db.query(models.Reward).filter(models.Reward.id == reward_id).first()


# def list_user_rewards(db: Session, user_id: int, active_only: bool = True) -> List[models.UserReward]:
#     query = db.query(models.UserReward).filter(models.UserReward.user_id == user_id)
#     if active_only:
#         query = query.join(models.Reward).filter(models.Reward.active == True)
#     return query.all()


# def assign_reward_to_user(db: Session, user_id: int, reward_id: int) -> models.UserReward:
#     user_reward = models.UserReward(
#         user_id=user_id,
#         reward_id=reward_id,
#         claimed=True,
#         claimed_at=datetime.utcnow()
#     )
#     db.add(user_reward)
#     db.commit()
#     db.refresh(user_reward)
#     return user_reward


# # ----------------------------
# # REFERRALS CRUD
# # ----------------------------
# def list_user_referrals(db: Session, user_id: int) -> List[models.UserReward]:
#     return db.query(models.UserReward).filter(models.UserReward.user_id == user_id).all()


# def assign_referral_reward(db: Session, ref_id: int, reward_id: Optional[int] = None) -> Optional[models.UserReward]:
#     ref = db.query(models.UserReward).filter(models.UserReward.id == ref_id).first()
#     if not ref or ref.claimed:
#         return None
#     ref.claimed = True
#     ref.claimed_at = datetime.utcnow()
#     db.commit()
#     db.refresh(ref)
#     return ref


# # ----------------------------
# # LEADERBOARD
# # ----------------------------
# def get_leaderboard(db: Session) -> List[Dict[str, Any]]:
#     from sqlalchemy import func
#     results = db.query(
#         models.UserReward.user_id,
#         func.count(models.UserReward.id).label("rewards_claimed")
#     ).group_by(models.UserReward.user_id).order_by(func.count(models.UserReward.id).desc()).all()

#     return [{"user_id": r.user_id, "rewards_claimed": r.rewards_claimed} for r in results]






# # app/crud.py
# """
# Unified CRUD for subscriptions, features, rewards, referrals, and help articles.
# """

# from typing import Optional, Dict, Any, List
# from datetime import datetime, timedelta

# from sqlalchemy.orm import Session
# from sqlalchemy import desc, func
# from .db import SessionLocal
# from . import models

# try:
#     from dateutil.relativedelta import relativedelta
#     _HAS_RELD = True
# except ImportError:
#     _HAS_RELD = False


# def _now() -> datetime:
#     return datetime.utcnow()


# # ----------------------------
# # SUBSCRIPTION HELPERS
# # ----------------------------
# def normalize_billing(billing: str) -> str:
#     if not billing:
#         return "monthly"
#     b = billing.lower()
#     if b in ("monthly", "month", "m"):
#         return "monthly"
#     if b in ("yearly", "annual", "y"):
#         return "yearly"
#     return "monthly"


# def add_interval(dt: datetime, billing: str) -> datetime:
#     if _HAS_RELD:
#         return dt + (relativedelta(months=1) if billing == "monthly" else relativedelta(years=1))
#     return dt + (timedelta(days=30) if billing == "monthly" else timedelta(days=365))


# # ----------------------------
# # SUBSCRIPTIONS CRUD
# # ----------------------------
# def create_pending_subscription(user_id: int, plan_id: int, billing_cycle: str,
#                                 meta: Optional[Dict[str, Any]] = None, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True

#         sub = models.UserSubscription(
#             user_id=user_id,
#             plan_id=plan_id,
#             billing_cycle=normalize_billing(billing_cycle),
#             status="pending",
#             meta=meta or {},
#             created_at=_now(),
#             updated_at=_now()
#         )
#         session.add(sub)

#         if own_session:
#             session.commit()
#             session.refresh(sub)
#         else:
#             session.commit()

#         return sub
#     finally:
#         if own_session:
#             session.close()


# def activate_subscription(subscription_id: int, payment_id: str, provider: str = "razorpay",
#                           provider_payload: Optional[Dict[str, Any]] = None, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True

#         sub = session.query(models.UserSubscription).filter(
#             models.UserSubscription.id == subscription_id
#         ).with_for_update().first()
#         if not sub:
#             return None

#         sub.status = "active"
#         sub.start_at = _now()
#         sub.end_at = add_interval(sub.start_at, sub.billing_cycle)
#         sub.external_payment_id = payment_id
#         sub.updated_at = _now()

#         meta = sub.meta or {}
#         if not isinstance(meta, dict):
#             import json
#             try:
#                 meta = json.loads(meta)
#             except Exception:
#                 meta = {"_prev_meta": str(meta)}
#         meta["provider"] = provider
#         meta["provider_payload"] = provider_payload or {}
#         sub.meta = meta

#         # Unlock user feature
#         uf = session.query(models.UserFeature).filter(
#             models.UserFeature.user_id == sub.user_id
#         ).with_for_update().first()
#         if not uf:
#             uf = models.UserFeature(user_id=sub.user_id, brokers_unlocked=True, credits=0.0)
#             session.add(uf)
#         else:
#             uf.brokers_unlocked = True

#         if own_session:
#             session.commit()
#             session.refresh(sub)
#         else:
#             session.commit()

#         return sub
#     finally:
#         if own_session:
#             session.close()


# def get_active_subscription(user_id: int, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         now = _now()
#         return session.query(models.UserSubscription).filter(
#             models.UserSubscription.user_id == user_id,
#             models.UserSubscription.status == "active",
#             models.UserSubscription.start_at <= now,
#             models.UserSubscription.end_at > now
#         ).order_by(desc(models.UserSubscription.end_at)).first()
#     finally:
#         if own_session:
#             session.close()


# def get_all_subscriptions(user_id: int, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         return session.query(models.UserSubscription).filter(
#             models.UserSubscription.user_id == user_id
#         ).order_by(desc(models.UserSubscription.id)).all()
#     finally:
#         if own_session:
#             session.close()


# def admin_list_subscriptions(status: Optional[str] = None, limit: int = 200, offset: int = 0,
#                              db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         q = session.query(models.UserSubscription).order_by(desc(models.UserSubscription.id))
#         if status:
#             q = q.filter(models.UserSubscription.status == status)
#         return q.limit(limit).offset(offset).all()
#     finally:
#         if own_session:
#             session.close()


# def cancel_subscription(subscription_id: int, admin_note: Optional[str] = None, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         sub = session.query(models.UserSubscription).filter(
#             models.UserSubscription.id == subscription_id
#         ).with_for_update().first()
#         if not sub:
#             return None
#         sub.status = "cancelled"
#         sub.updated_at = _now()
#         meta = sub.meta or {}
#         if admin_note:
#             meta["cancelled_note"] = admin_note
#             meta["cancelled_at"] = _now().isoformat()
#         sub.meta = meta

#         if own_session:
#             session.commit()
#             session.refresh(sub)
#         else:
#             session.commit()

#         return sub
#     finally:
#         if own_session:
#             session.close()


# def get_plan(plan_id: int, db: Optional[Session] = None):
#     own_session = False
#     session = db
#     try:
#         if session is None:
#             session = SessionLocal()
#             own_session = True
#         return session.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.id == plan_id).first()
#     finally:
#         if own_session:
#             session.close()


# # ----------------------------
# # REWARDS CRUD
# # ----------------------------
# def list_rewards(db: Session) -> List[models.Reward]:
#     return db.query(models.Reward).all()


# def get_reward(db: Session, reward_id: int) -> Optional[models.Reward]:
#     return db.query(models.Reward).filter(models.Reward.id == reward_id).first()


# def list_user_rewards(db: Session, user_id: int, active_only: bool = True) -> List[models.UserReward]:
#     query = db.query(models.UserReward).filter(models.UserReward.user_id == user_id)
#     if active_only:
#         query = query.join(models.Reward).filter(models.Reward.active == True)
#     return query.all()


# def assign_reward_to_user(db: Session, user_id: int, reward_id: int) -> models.UserReward:
#     user_reward = models.UserReward(
#         user_id=user_id,
#         reward_id=reward_id,
#         claimed=True,
#         claimed_at=datetime.utcnow()
#     )
#     db.add(user_reward)
#     db.commit()
#     db.refresh(user_reward)
#     return user_reward


# # ----------------------------
# # REFERRALS CRUD
# # ----------------------------
# def list_user_referrals(db: Session, user_id: int) -> List[models.UserReward]:
#     return db.query(models.UserReward).filter(models.UserReward.user_id == user_id).all()


# def assign_referral_reward(db: Session, ref_id: int, reward_id: Optional[int] = None) -> Optional[models.UserReward]:
#     ref = db.query(models.UserReward).filter(models.UserReward.id == ref_id).first()
#     if not ref or ref.claimed:
#         return None
#     ref.claimed = True
#     ref.claimed_at = datetime.utcnow()
#     db.commit()
#     db.refresh(ref)
#     return ref


# # ----------------------------
# # LEADERBOARD
# # ----------------------------
# def get_leaderboard(db: Session) -> List[Dict[str, Any]]:
#     results = db.query(
#         models.UserReward.user_id,
#         func.count(models.UserReward.id).label("rewards_claimed")
#     ).group_by(models.UserReward.user_id).order_by(func.count(models.UserReward.id).desc()).all()

#     return [{"user_id": r.user_id, "rewards_claimed": r.rewards_claimed} for r in results]


# # ----------------------------
# # HELP MODULE CRUD
# # ----------------------------
# def list_help_categories(db: Session):
#     return db.query(models.HelpCategory).all()


# def list_help_articles(db: Session, category_id: Optional[int] = None, active_only: bool = True):
#     query = db.query(models.HelpArticle)
#     if category_id:
#         query = query.filter(models.HelpArticle.category_id == category_id)
#     if active_only:
#         query = query.filter(models.HelpArticle.is_active == True)
#     return query.all()


# def get_help_article(db: Session, article_id: int):
#     return db.query(models.HelpArticle).filter(models.HelpArticle.id == article_id).first()




# app/crud.py
"""
Unified CRUD for subscriptions, rewards, referrals, leaderboard, and help module.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.db import SessionLocal
from app import models

try:
    from dateutil.relativedelta import relativedelta
    _HAS_RELD = True
except ImportError:
    _HAS_RELD = False


# -------------------------------------------------
# HELPERS
# -------------------------------------------------
def _now() -> datetime:
    return datetime.utcnow()


def normalize_billing(billing: str) -> str:
    if not billing:
        return "monthly"
    b = billing.lower()
    if b in ("monthly", "month", "m"):
        return "monthly"
    if b in ("yearly", "annual", "y"):
        return "yearly"
    return "monthly"


def add_interval(dt: datetime, billing: str) -> datetime:
    if _HAS_RELD:
        return dt + (relativedelta(months=1) if billing == "monthly" else relativedelta(years=1))
    return dt + (timedelta(days=30) if billing == "monthly" else timedelta(days=365))


# =================================================
# SUBSCRIPTIONS CRUD
# =================================================
def create_pending_subscription(
    user_id: int,
    plan_id: int,
    billing_cycle: str,
    meta: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None,
):
    own = False
    session = db or SessionLocal()
    if db is None:
        own = True

    try:
        sub = models.UserSubscription(
            user_id=user_id,
            plan_id=plan_id,
            billing_cycle=normalize_billing(billing_cycle),
            status="pending",
            meta=meta or {},
            created_at=_now(),
            updated_at=_now(),
        )
        session.add(sub)
        session.commit()
        session.refresh(sub)
        return sub
    finally:
        if own:
            session.close()


def activate_subscription(
    subscription_id: int,
    payment_id: str,
    provider: str = "razorpay",
    provider_payload: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None,
):
    own = False
    session = db or SessionLocal()
    if db is None:
        own = True

    try:
        sub = (
            session.query(models.UserSubscription)
            .filter(models.UserSubscription.id == subscription_id)
            .with_for_update()
            .first()
        )
        if not sub:
            return None

        sub.status = "active"
        sub.start_at = _now()
        sub.end_at = add_interval(sub.start_at, sub.billing_cycle)
        sub.external_payment_id = payment_id
        sub.updated_at = _now()

        meta = sub.meta or {}
        meta["provider"] = provider
        meta["provider_payload"] = provider_payload or {}
        sub.meta = meta

        session.commit()
        session.refresh(sub)
        return sub
    finally:
        if own:
            session.close()


def get_active_subscription(user_id: int, db: Optional[Session] = None):
    own = False
    session = db or SessionLocal()
    if db is None:
        own = True

    try:
        now = _now()
        return (
            session.query(models.UserSubscription)
            .filter(
                models.UserSubscription.user_id == user_id,
                models.UserSubscription.status == "active",
                models.UserSubscription.start_at <= now,
                models.UserSubscription.end_at > now,
            )
            .order_by(desc(models.UserSubscription.end_at))
            .first()
        )
    finally:
        if own:
            session.close()


# =================================================
# REWARDS CRUD (MATCHES YOUR DB + MODELS)
# =================================================
def list_rewards(db: Session) -> List[models.Reward]:
    return (
        db.query(models.Reward)
        .filter(models.Reward.active == True)
        .order_by(desc(models.Reward.created_at))
        .all()
    )


def get_reward(db: Session, reward_id: int) -> Optional[models.Reward]:
    return db.query(models.Reward).filter(models.Reward.id == reward_id).first()


def list_user_rewards(
    db: Session,
    user_id: int,
    active_only: bool = True,
) -> List[models.UserReward]:
    q = (
        db.query(models.UserReward)
        .join(models.Reward)
        .filter(models.UserReward.user_id == user_id)
    )

    if active_only:
        q = q.filter(models.Reward.active == True)

    return q.all()


def assign_reward_to_user(
    db: Session,
    user_id: int,
    reward_id: int,
) -> models.UserReward:
    user_reward = models.UserReward(
        user_id=user_id,
        reward_id=reward_id,
        claimed=True,
        claimed_at=_now(),
        created_at=_now(),
    )
    db.add(user_reward)
    db.commit()
    db.refresh(user_reward)
    return user_reward


# =================================================
# REFERRALS CRUD (FIXED & CLEAN)
# =================================================
def list_user_referrals(
    db: Session,
    user_id: int,
) -> List[models.Referral]:
    return (
        db.query(models.Referral)
        .filter(
            (models.Referral.referrer_id == user_id)
            | (models.Referral.referee_id == user_id)
        )
        .order_by(desc(models.Referral.created_at))
        .all()
    )


def assign_referral_reward(
    db: Session,
    referral_id: int,
    reward_id: Optional[int] = None,
) -> Optional[models.Referral]:
    ref = (
        db.query(models.Referral)
        .filter(models.Referral.id == referral_id)
        .with_for_update()
        .first()
    )

    if not ref or ref.claimed:
        return None

    ref.claimed = True
    ref.claimed_at = _now()
    ref.reward_id = reward_id

    db.commit()
    db.refresh(ref)
    return ref


# =================================================
# LEADERBOARD
# =================================================
def get_leaderboard(db: Session) -> List[Dict[str, Any]]:
    rows = (
        db.query(
            models.UserReward.user_id,
            func.count(models.UserReward.id).label("rewards_claimed"),
        )
        .group_by(models.UserReward.user_id)
        .order_by(desc(func.count(models.UserReward.id)))
        .all()
    )

    return [
        {"user_id": r.user_id, "rewards_claimed": r.rewards_claimed}
        for r in rows
    ]


# =================================================
# HELP MODULE CRUD
# =================================================
def list_help_categories(db: Session):
    return db.query(models.HelpCategory).all()


def list_help_articles(
    db: Session,
    category_id: Optional[int] = None,
    active_only: bool = True,
):
    q = db.query(models.HelpArticle)

    if category_id:
        q = q.filter(models.HelpArticle.category_id == category_id)

    if active_only:
        q = q.filter(models.HelpArticle.is_active == True)

    return q.order_by(desc(models.HelpArticle.created_at)).all()


def get_help_article(db: Session, article_id: int):
    return (
        db.query(models.HelpArticle)
        .filter(models.HelpArticle.id == article_id)
        .first()
    )
