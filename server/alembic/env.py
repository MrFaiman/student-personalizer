"""Alembic environment - uses SQLModel metadata and DATABASE_URL from environment."""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from alembic import context

# Make src importable when running alembic from server/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import all models so their tables are registered in SQLModel.metadata
from dotenv import load_dotenv

import src.audit.models  # noqa: F401  - registers AuditLog
import src.auth.models  # noqa: F401  - registers User, UserSession, PasswordHistory
import src.models  # noqa: F401  - registers Student, Grade, AttendanceRecord, etc.

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from DATABASE_URL env var.
# Force psycopg3 dialect (postgresql+psycopg) - the project uses psycopg[binary] v3, not psycopg2.
database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/student_personalizer")
database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
config.set_main_option("sqlalchemy.url", database_url)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
