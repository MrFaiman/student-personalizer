# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pedagogical dashboard (דשבורד פדגוגי) — a BI system for analyzing student academic performance, behavior, and attendance. Hebrew-language educational data is ingested from Excel files and served via a REST API with analytics endpoints. The UI is RTL (right-to-left).

## Repository Structure

Monorepo with two independent apps:

- **`server/`** — Python FastAPI backend (package managed by `uv`)
- **`client/`** — React + TypeScript frontend (package managed by `pnpm`)

## Commands

### Server (run from `server/`)

```bash
uv sync                    # Install dependencies
uv run server              # Start API server (port 3000)
uv run ruff check src/     # Lint
uv run ruff format src/    # Format
uv run pytest tests/ -v    # Run all tests
uv run pytest tests/test_api.py -v             # Run single test file
uv run pytest tests/test_api.py::test_name -v  # Run single test
```

### Client (run from `client/`)

```bash
pnpm install          # Install dependencies
pnpm dev              # Dev server (port 5173)
pnpm build            # Type-check + build
pnpm lint             # ESLint
```

## Architecture

### Server

- **Entry point:** `src/main.py` — FastAPI app with CORS middleware, lifespan DB init
- **Database:** SQLite by default (`data.db`), configurable via `DATABASE_URL` env var. Uses SQLModel (SQLAlchemy + Pydantic)
- **Models** (`src/models.py`): `Class`, `Student`, `Grade`, `AttendanceRecord`, `ImportLog`
- **Routers** (`src/routers/`): `ingestion` (Excel upload/parsing), `students` (CRUD + dashboard), `analytics` (KPIs, heatmaps, rankings), `ml` (predictions)
- **Schemas** (`src/schemas/`): Pydantic response/request models, separate from SQLModel table models
- **Services** (`src/services/`): Business logic — `ingestion.py` (Excel parsing with Pandas, Hebrew column mapping), `analytics.py` (aggregation queries), `ml.py` (scikit-learn predictions)
- **Ruff config:** line-length 140, rules E/F/I

### Client

- **React 19** with **TanStack Router** (file-based routing, auto code-splitting)
- **Vite 7** dev server with `@` path alias → `src/`
- **UI:** shadcn/ui (new-york style) + Tailwind CSS v4 + Radix UI primitives + Lucide icons
- **RTL layout** enabled in shadcn config
- **Routes** in `src/routes/` — `__root.tsx` is the layout, `index.tsx` is the homepage
- **Components** in `src/components/ui/` are shadcn-generated

### Data Flow

Excel files (.xlsx with Hebrew headers) → POST `/api/ingest/upload` → Pandas parses and validates → rows written to SQLite via SQLModel → analytics endpoints aggregate and return JSON → frontend renders dashboards.
