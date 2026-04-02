import argparse
import os
from pathlib import Path

from sqlalchemy import text
from sqlmodel import SQLModel

from src.database import engine


def _is_probably_local_db(database_url: str) -> bool:
    url = database_url.lower()
    return (
        url.startswith("sqlite")
        or "localhost" in url
        or "127.0.0.1" in url
        or "student_personalizer_test" in url
        or "student_personalizer_dev" in url
    )


def _load_all_models() -> None:
    # Ensure all tables are registered on SQLModel.metadata
    import src.audit.models  # noqa: F401
    import src.auth.models  # noqa: F401
    import src.models  # noqa: F401


def _wipe_sqlmodel_metadata() -> None:
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def _wipe_postgres() -> None:
    # Drop all known tables (metadata), plus legacy alembic version table if present.
    SQLModel.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))

    # Recreate current schema from models.
    SQLModel.metadata.create_all(engine)


def main() -> int:
    parser = argparse.ArgumentParser(description="Wipe the database (DANGEROUS).")
    parser.add_argument("--yes", action="store_true", help="Required confirmation flag.")
    parser.add_argument("--force", action="store_true", help="Allow wiping non-local DB URLs.")
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL", "")
    if not args.yes:
        raise SystemExit("Refusing to wipe DB without --yes.")

    if not args.force and database_url and not _is_probably_local_db(database_url):
        raise SystemExit(f"Refusing to wipe non-local DATABASE_URL without --force: {database_url}")

    _load_all_models()

    dialect = engine.dialect.name
    if dialect == "postgresql":
        _wipe_postgres()
    else:
        _wipe_sqlmodel_metadata()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

