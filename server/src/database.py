import os

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from .constants import DATABASE_URL

# Force psycopg3 dialect for PostgreSQL URLs (project uses psycopg[binary] v3, not psycopg2)
_db_url = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

_is_sqlite = _db_url.startswith("sqlite")
_connect_args: dict = {}

if _is_sqlite:
    # SQLite in-memory: require same-thread=False for test sessions
    _connect_args["check_same_thread"] = False
    engine = create_engine(_db_url, connect_args=_connect_args, poolclass=StaticPool)
else:
    if os.getenv("DB_SSL_REQUIRED", "").lower() in ("1", "true", "yes"):
        _connect_args["sslmode"] = "require"
    engine = create_engine(_db_url, echo=False, pool_size=5, max_overflow=10, connect_args=_connect_args)


def init_db():
    """Initialize database.

    Schema is managed at runtime via SQLModel metadata.

    Note: This project intentionally does not use Alembic migrations. Tables are
    created (if missing) on startup using `SQLModel.metadata.create_all()`.
    """
    # Import all models so their tables are registered in SQLModel.metadata
    import src.audit.models  # noqa: F401
    import src.auth.models  # noqa: F401
    import src.models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency for getting database sessions."""
    with Session(engine) as session:
        yield session
