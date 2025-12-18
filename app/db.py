



# db.py

import os
import logging
from typing import Generator  # Import Generator for type hinting
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

# Set up logging
log = logging.getLogger("app.db")
log.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
log.addHandler(console_handler)

# Load environment variables from the .env file
load_dotenv()

# DATABASE_URL examples:
# postgresql+psycopg2://user:pass@host:5432/dbname
# sqlite:///./app/storage/app.db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app/storage/app.db").strip()

# Engine kwargs (can be overridden with environment vars)
engine_kwargs = {
    "echo": os.getenv("DB_ECHO", "false").lower() in ("1", "true", "yes"),
    "future": True,
}

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, **engine_kwargs)

# SessionLocal to interact with the DB
SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True, expire_on_commit=False)

# Base class for all models
Base = declarative_base()

def init_db(create_timescale: bool = False) -> None:
    """
    Initialize DB (create tables registered on Base).
    If using Postgres and create_timescale=True, attempt to create timescaledb extension
    and convert 'ticks' to hypertable. These operations are best-effort and errors are ignored.
    """
    log.info("Initializing the database...")  # Add log for database initialization
    try:
        import app.models  # noqa: F401
    except Exception:
        log.error("Failed to import models")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    log.info("Database tables created (if not already present).")
    
    # TimescaleDB extension logic (if necessary)
    if create_timescale and not DATABASE_URL.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                try:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
                    conn.commit()
                except Exception as e:
                    log.warning(f"Could not create timescaledb extension: {e}")
                    
                try:
                    exists_res = conn.execute(text("SELECT to_regclass('public.ticks') IS NOT NULL as exists;"))
                    exists = exists_res.scalar()
                    if exists:
                        try:
                            conn.execute(text("SELECT create_hypertable('ticks', 'ts', if_not_exists => TRUE);"))
                            conn.commit()
                        except Exception as e:
                            log.warning(f"Could not create hypertable: {e}")
                except Exception as e:
                    log.warning(f"Could not check hypertable existence: {e}")
        except Exception as e:
            log.warning(f"Error in connecting to database for TimescaleDB operations: {e}")

def get_db() -> Generator:
    """
    FastAPI dependency generator that yields a SQLAlchemy session and ensures it is closed.
    Usage in FastAPI endpoints:
        from fastapi import Depends
        def endpoint(db = Depends(get_db)): ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

