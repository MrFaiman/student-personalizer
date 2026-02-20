from sqlmodel import Session, SQLModel, create_engine

from .constants import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False, pool_size=5, max_overflow=10)


def init_db():
    """Initialize database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency for getting database sessions."""
    with Session(engine) as session:
        yield session
