"""
database.py
-----------
Sets up the SQLAlchemy engine/session machinery used across the whole app.
Follows the SQL (Relational) Databases FastAPI tutorial pattern: a `SessionLocal`
factory and a `get_db` dependency that yields one session per request and always
closes it, even on error.
"""

from sqlalchemy import create_engine                     # Builds the low-level DB connection pool
from sqlalchemy.orm import sessionmaker, DeclarativeBase  # Session factory + modern declarative base class

from app.config import settings  # Import our centralized settings (holds the DB URL)

# The Engine manages a pool of physical connections to Postgres.
engine = create_engine(
    settings.database_url,   # Postgres connection string, e.g. postgresql://user:pass@host/db
    pool_pre_ping=True,       # Test connections for liveness before using them (avoids stale-connection errors)
    pool_size=10,              # Number of persistent connections kept open in the pool
    max_overflow=20,           # Extra connections allowed beyond pool_size under load
)

# SessionLocal is a factory: calling SessionLocal() gives you a new DB session/transaction.
SessionLocal = sessionmaker(
    autocommit=False,   # We control commits explicitly (safer than implicit autocommit)
    autoflush=False,     # Don't auto-flush pending changes before every query (explicit is clearer)
    bind=engine,          # Bind this session factory to our engine/connection pool
)


class Base(DeclarativeBase):
    """
    Base class every SQLAlchemy ORM model inherits from.
    SQLAlchemy uses this to collect metadata (table definitions) for all models,
    which Alembic/`Base.metadata.create_all()` can then use to create tables.
    """
    pass  # No extra behaviour needed; this just anchors the declarative mapping system


def get_db():
    """
    FastAPI dependency that yields a single DB session per request.
    Using `yield` (instead of `return`) lets us run cleanup code (session.close())
    after the request finishes, even if an exception was raised - this is the
    standard FastAPI "dependency with yield" pattern.
    """
    db = SessionLocal()  # Open a new session/transaction for this request
    try:
        yield db          # Hand the session to the path operation function
    finally:
        db.close()        # Always release the connection back to the pool afterwards
