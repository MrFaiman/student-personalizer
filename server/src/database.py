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

    Database schema is managed via Alembic migrations (see server/alembic).
    """
    if not _is_sqlite:
        return

    # SQLite is used for tests / local scratch DBs; keep automatic table creation
    # to avoid needing to run Alembic inside every test.
    from .audit.models import AuditLog  # noqa: F401
    from .auth.models import PasswordHistory, User, UserSchoolMembership, UserSession  # noqa: F401
    from .models import (  # noqa: F401
        AttendanceRecord,
        Class,
        Grade,
        ImportLog,
        OpenDayRegistration,
        Student,
        Subject,
        Teacher,
    )

    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency for getting database sessions."""
    with Session(engine) as session:
        yield session
