## Alembic migrations

This project uses **Alembic** to manage the PostgreSQL schema (no more runtime backfills).

### Apply migrations (local dev)

From `server/`:

```powershell
uv run alembic upgrade head
```

### Wipe DB (local dev / tests only)

From `server/`:

```powershell
uv run python scripts/wipe_db.py --yes
```

The script refuses to run against non-local `DATABASE_URL` values unless you also pass `--force`.

### Create a new migration

From `server/`:

```powershell
uv run alembic revision -m "short message"
```

Then edit the generated file in `server/alembic/versions/`.

### Notes

- **PostgreSQL**: schema is expected to be managed by Alembic (run `upgrade head`).
- **SQLite (tests)**: `src/database.py:init_db()` still runs `SQLModel.metadata.create_all()` to keep tests fast and self-contained.

