from sqlmodel import SQLModel, create_engine, Session
from contextlib import contextmanager
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")

# For SQLite, we need connect_args for async compatibility
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def init_db():
    """Initialize database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency for getting database sessions."""
    with Session(engine) as session:
        yield session


@contextmanager
def get_session_context():
    """Context manager for database sessions."""
    with Session(engine) as session:
        yield session
