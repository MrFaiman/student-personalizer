# Student Personalizer - server

FastAPI backend for the pedagogical dashboard: Excel ingestion, PostgreSQL storage, analytics, JWT auth with RBAC and school scope, optional field-level PII encryption, and ML at-risk predictions. All HTTP APIs live under `/api/...` except `/`, `/health`, and (when enabled) OpenAPI.

## Stack

- **Python 3.13+**
- **FastAPI**, **Uvicorn**
- **SQLModel** (SQLAlchemy) on **PostgreSQL** - tables created on startup (`create_all`; no Alembic in this repo)
- **pandas** / **openpyxl** for ingestion, **scikit-learn** for ML
- **uv** for dependencies and runs

## Prerequisites

- **PostgreSQL** (18 recommended; matches docker-compose)
- **uv** ([installation](https://docs.astral.sh/uv/getting-started/installation/))

## Quick start

```bash
cd server
uv sync
cp .env.example .env   # edit DATABASE_URL, secrets for real environments
uv run python -m src.main
```

Default listen address is `0.0.0.0` and port **3000** (override with `PORT`). Default DB URL matches local Postgres: `postgresql://postgres:postgres@localhost:5432/student_personalizer` (see `src/constants.py`).

On startup the app creates tables, seeds RBAC, and ensures a bootstrap admin (see `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env.example`).

## Scripts

| Command | Purpose |
|--------|---------|
| `uv run python -m src.main` | Run API server |
| `uv run poe dev` | Same as above (Poe task alias) |
| `uv run pytest tests/ -v` | Tests (expects `DATABASE_URL` and usually `JWT_SECRET_KEY` when `AUTH_REQUIRED=true`) |
| `uv run poe test` | Same as CI: `pytest tests/ -v --tb=short` |
| `uv run poe check` | Runs `lint` then `test` (local pre-push smoke) |
| `uv run ruff check src/` | Lint (line length 140; E, F, I, B, UP; E501 and B008 ignored) |
| `uv run poe lint` | Same as above |
| `uv run bandit -r src/ -ll -x src/debug` | SAST (debug package excluded in CI) |
| `uv run poe bandit` | Same as above |

`uv` has no `[tool.uv.scripts]`; tasks live under `[tool.poe.tasks]` and run via `uv run poe <name>`.

## Configuration

Copy `server/.env.example` and adjust. Common variables:

| Variable | Role |
|----------|------|
| `DATABASE_URL` | PostgreSQL connection string |
| `ORIGIN_URL` | Single allowed CORS origin (SPA URL); must match how the browser calls the API |
| `JWT_SECRET_KEY` | Required when `AUTH_REQUIRED=true` |
| `FIELD_ENCRYPTION_KEY` / `HASH_PEPPER` | Required when `FIELD_ENCRYPTION_REQUIRED=true` (production hardening) |
| `ENABLE_DEBUG` | When true: mounts `/docs`, `/redoc`, and the optional `/api/debug` router |

Validated settings and startup security checks live in `src/config.py`. Refresh tokens use an **httpOnly** cookie; the SPA should use `credentials: "include"`. For split origins (separate app vs API hostnames), you typically need `COOKIE_SAMESITE` / `COOKIE_SECURE` - notes are in `.env.example`.

For a full **Docker Compose** production example (DB + API env wiring), see the repository root `docker-compose.prod.yml` and `.env.example`.

## Layout

```
src/
  main.py           # App factory, middleware, router registration
  config.py         # Pydantic settings + security validation
  constants.py      # Defaults (thresholds, URLs, feature flags)
  models.py         # SQLModel tables
  database.py       # Engine, sessions, optional SSL
  routers/          # HTTP endpoints -> services
  services/         # Business logic, queries
  schemas/          # Pydantic request/response models
  views/            # Response shaping where used
  auth/             # Login, refresh, MFA, RBAC, SSO hooks
  crypto/           # Field encryption + lookup hashes
```

## API surface

Routers include **auth**, **config**, **ingestion**, **students**, **classes**, **teachers**, **subjects**, **analytics**, **open_day**, **ml**, and (if `ENABLE_DEBUG`) **debug**. Most domain routes require a Bearer access token and, where applicable, an active **school** scope in the token.

When `ENABLE_DEBUG=true`, interactive docs are at `/docs` and `/redoc`. Otherwise rely on the codebase or a local debug run for OpenAPI.

## Excel ingestion

Uploads are `.xlsx` with **Hebrew** headers. The parser infers **grades** vs **events/attendance** from columns. Implementation: `src/services/ingestion.py`; open-day spreadsheets are handled in `src/services/open_day.py`.

## Docker

From the **repository root** (same as CI):

```bash
docker build -f server/Dockerfile.prod server/
```

The image runs `uv run python -m src.main` as a non-root user and exposes port 3000 with a `/health` check.

## Security

Operational controls (auth, encryption, rate limits, audit logging) are summarized in the repo root `SECURITY.md`.
