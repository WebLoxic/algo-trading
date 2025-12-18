
# # app/db.py
# """
# Database configuration and helpers.

# Responsibilities:
#  - load DATABASE_URL from environment (.env supported)
#  - create SQLAlchemy engine + SessionLocal + Base
#  - ensure sqlite file parent dir exists for local dev
#  - provide init_db() to create tables and optional TimescaleDB hypertable for ticks
#  - expose get_session() and get_db() FastAPI dependency

# Notes:
#  - This module is intentionally minimal and has no dependency on app.crud to avoid import cycles.
#  - If you plan to use async SQLAlchemy (async ORM) use a separate async engine/module.
# """

# from pathlib import Path
# import os
# from typing import Generator, Optional
# from dotenv import load_dotenv
# from sqlalchemy import create_engine, text
# from sqlalchemy.orm import sessionmaker, declarative_base

# # load .env (silent if not present)
# load_dotenv()

# # DATABASE_URL examples:
# # postgresql+psycopg2://user:pass@host:5432/dbname
# # sqlite:///./app/storage/app.db
# DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app/storage/app.db").strip()

# # Ensure parent directory exists for sqlite file (dev convenience)
# if DATABASE_URL.startswith("sqlite"):
#     try:
#         # remove sqlite:/// or sqlite:///
#         sqlite_path = DATABASE_URL.split("///", 1)[-1]
#         p = Path(sqlite_path).resolve()
#         parent = p.parent
#         if not parent.exists():
#             parent.mkdir(parents=True, exist_ok=True)
#     except Exception:
#         # ignore filesystem issues here; engine will raise if problematic
#         pass

# # Engine kwargs (can be overridden with environment vars)
# engine_kwargs = {
#     "echo": os.getenv("DB_ECHO", "false").lower() in ("1", "true", "yes"),
#     "future": True,
# }

# # sqlite needs check_same_thread and connect_args
# connect_args = {}
# if DATABASE_URL.startswith("sqlite"):
#     connect_args = {"check_same_thread": False}
#     engine_kwargs["connect_args"] = connect_args
# else:
#     # Postgres / MySQL: add pool settings (override with env)
#     try:
#         pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
#         max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
#     except Exception:
#         pool_size = 10
#         max_overflow = 20

#     engine_kwargs.update({
#         "pool_pre_ping": True,
#         "pool_size": pool_size,
#         "max_overflow": max_overflow,
#     })

# # Create engine
# engine = create_engine(DATABASE_URL, **engine_kwargs)

# # Session factory
# # expire_on_commit=False keeps objects usable after commit (useful for API responses)
# SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True, expire_on_commit=False)
# Base = declarative_base()


# def init_db(create_timescale: bool = True) -> None:
#     """
#     Initialize DB (create tables registered on Base).
#     If using Postgres and create_timescale=True, attempt to create timescaledb extension
#     and convert 'ticks' to hypertable. These operations are best-effort and errors are ignored.
#     """
#     # import models to ensure they are registered with Base.metadata
#     try:
#         # Importing app.models should register SQLAlchemy models on Base
#         import app.models  # noqa: F401
#     except Exception:
#         # If models import fails, still attempt to create whatever metadata exists
#         pass

#     # create tables
#     Base.metadata.create_all(bind=engine)

#     # If using Postgres (not sqlite) optionally try to enable timescaledb extension & hypertable
#     if create_timescale and not DATABASE_URL.startswith("sqlite"):
#         try:
#             with engine.connect() as conn:
#                 try:
#                     conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
#                     conn.commit()
#                 except Exception:
#                     # ignore - not fatal (may lack permissions or extension absent)
#                     pass

#                 # best-effort: if ticks table exists, attempt to create hypertable
#                 try:
#                     exists_res = conn.execute(text("SELECT to_regclass('public.ticks') IS NOT NULL as exists;"))
#                     exists = exists_res.scalar()
#                     if exists:
#                         try:
#                             conn.execute(text("SELECT create_hypertable('ticks', 'ts', if_not_exists => TRUE);"))
#                             conn.commit()
#                         except Exception:
#                             # ignore (may lack permissions or extension not available)
#                             pass
#                 except Exception:
#                     # ignore any errors during check/create
#                     pass
#         except Exception:
#             # connection attempt failed; ignore so init_db won't crash apps that call it
#             pass


# def get_session():
#     """
#     Convenience: return a new SessionLocal() instance.
#     Use this for manual session management.
#     """
#     return SessionLocal()


# def get_db() -> Generator:
#     """
#     FastAPI dependency generator that yields a SQLAlchemy session and ensures it is closed.
#     Usage in FastAPI endpoints:
#         from fastapi import Depends
#         def endpoint(db = Depends(get_db)): ...
#     """
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         try:
#             db.close()
#         except Exception:
#             pass


# # db.py

# from pathlib import Path
# import os
# from typing import Generator
# from dotenv import load_dotenv
# from sqlalchemy import create_engine, text
# from sqlalchemy.orm import sessionmaker, declarative_base

# # Load environment variables from the .env file
# load_dotenv()

# # DATABASE_URL examples:
# # postgresql+psycopg2://user:pass@host:5432/dbname
# # sqlite:///./app/storage/app.db
# DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app/storage/app.db").strip()

# # Ensure parent directory exists for sqlite file (dev convenience)
# if DATABASE_URL.startswith("sqlite"):
#     try:
#         # remove sqlite:/// or sqlite:///
#         sqlite_path = DATABASE_URL.split("///", 1)[-1]
#         p = Path(sqlite_path).resolve()
#         parent = p.parent
#         if not parent.exists():
#             parent.mkdir(parents=True, exist_ok=True)
#     except Exception:
#         # ignore filesystem issues here; engine will raise if problematic
#         pass

# # Engine kwargs (can be overridden with environment vars)
# engine_kwargs = {
#     "echo": os.getenv("DB_ECHO", "false").lower() in ("1", "true", "yes"),
#     "future": True,
# }

# # SQLite specific settings
# connect_args = {}
# if DATABASE_URL.startswith("sqlite"):
#     connect_args = {"check_same_thread": False}
#     engine_kwargs["connect_args"] = connect_args
# else:
#     # Postgres / MySQL: add pool settings (override with env)
#     try:
#         pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
#         max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
#     except Exception:
#         pool_size = 10
#         max_overflow = 20

#     engine_kwargs.update({
#         "pool_pre_ping": True,
#         "pool_size": pool_size,
#         "max_overflow": max_overflow,
#     })

# # Create SQLAlchemy engine
# engine = create_engine(DATABASE_URL, **engine_kwargs)

# # SessionLocal to interact with the DB
# SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True, expire_on_commit=False)

# # Base class for all models
# Base = declarative_base()

# def init_db(create_timescale: bool = False) -> None:
#     """
#     Initialize DB (create tables registered on Base).
#     If using Postgres and create_timescale=True, attempt to create timescaledb extension
#     and convert 'ticks' to hypertable. These operations are best-effort and errors are ignored.
#     """
#     # Import models to ensure they are registered with Base.metadata
#     try:
#         # Importing app.models should register SQLAlchemy models on Base
#         import app.models  # noqa: F401
#     except Exception:
#         # If models import fails, still attempt to create whatever metadata exists
#         pass

#     # Create tables
#     Base.metadata.create_all(bind=engine)

#     # If using Postgres (not sqlite) optionally try to enable timescaledb extension & hypertable
#     if create_timescale and not DATABASE_URL.startswith("sqlite"):
#         try:
#             with engine.connect() as conn:
#                 # Try to create the timescaledb extension
#                 try:
#                     conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
#                     conn.commit()
#                 except Exception:
#                     # Ignore if we can't create the extension (not fatal)
#                     pass

#                 # Best-effort: If 'ticks' table exists, attempt to create a hypertable
#                 try:
#                     exists_res = conn.execute(text("SELECT to_regclass('public.ticks') IS NOT NULL as exists;"))
#                     exists = exists_res.scalar()
#                     if exists:
#                         try:
#                             conn.execute(text("SELECT create_hypertable('ticks', 'ts', if_not_exists => TRUE);"))
#                             conn.commit()
#                         except Exception:
#                             # Ignore if hypertable creation fails
#                             pass
#                 except Exception:
#                     pass
#         except Exception:
#             # Ignore any errors during connection or extension creation
#             pass

# def get_session():
#     """
#     Convenience: return a new SessionLocal() instance.
#     Use this for manual session management.
#     """
#     return SessionLocal()

# def get_db() -> Generator:
#     """
#     FastAPI dependency generator that yields a SQLAlchemy session and ensures it is closed.
#     Usage in FastAPI endpoints:
#         from fastapi import Depends
#         def endpoint(db = Depends(get_db)): ...
#     """
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         try:
#             db.close()
#         except Exception:
#             pass




# app/db.py  (or app/core/database.py — but be consistent)

import os
import logging
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

# -------------------------------------------------
# LOGGING (safe for reload)
# -------------------------------------------------

log = logging.getLogger("app.db")
if not log.handlers:
    log.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    log.addHandler(handler)

# -------------------------------------------------
# ENV
# -------------------------------------------------

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./app/storage/app.db"
)

# -------------------------------------------------
# SQLALCHEMY BASE (SINGLE SOURCE OF TRUTH)
# -------------------------------------------------

Base = declarative_base()

# -------------------------------------------------
# ENGINE
# -------------------------------------------------

engine_kwargs = {
    "echo": os.getenv("DB_ECHO", "false").lower() in ("1", "true", "yes"),
    "future": True,
}

engine = create_engine(DATABASE_URL, **engine_kwargs)

# -------------------------------------------------
# SESSION
# -------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)

# -------------------------------------------------
# INIT DB
# -------------------------------------------------

def init_db(create_timescale: bool = False) -> None:
    """
    Initialize database and create tables.
    """
    log.info("Initializing database...")

    try:
        # IMPORTANT: this registers all models on Base
        import app.models  # noqa: F401
    except Exception as e:
        log.error("Failed to import models: %s", e)
        raise

    Base.metadata.create_all(bind=engine)
    log.info("Database tables ensured.")

    # Optional: TimescaleDB support
    if create_timescale and DATABASE_URL.startswith("postgres"):
        try:
            with engine.begin() as conn:
                try:
                    conn.execute(
                        text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
                    )
                except Exception as e:
                    log.warning("Timescale extension not created: %s", e)

                try:
                    exists = conn.execute(
                        text("SELECT to_regclass('public.ticks') IS NOT NULL;")
                    ).scalar()
                    if exists:
                        conn.execute(
                            text(
                                "SELECT create_hypertable('ticks', 'ts', if_not_exists => TRUE);"
                            )
                        )
                except Exception as e:
                    log.warning("Hypertable creation skipped: %s", e)
        except Exception as e:
            log.warning("Timescale setup failed: %s", e)

# -------------------------------------------------
# FASTAPI DEPENDENCY
# -------------------------------------------------

def get_db() -> Generator:
    """
    FastAPI dependency.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
