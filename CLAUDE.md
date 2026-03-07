# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Student Personalizer — a full-stack pedagogical dashboard for analyzing student academic performance, attendance, and behavior. Ingests Excel files with student grades/attendance data, stores in PostgreSQL, provides analytics and ML-powered at-risk predictions.

## Commands

### Client (pnpm, in `client/`)
- `pnpm dev` — Vite dev server at localhost:5173
- `pnpm build` — Production build (`tsr generate && tsc -b && vite build`)
- `pnpm lint` — ESLint

### Server (uv, in `server/`)
- `uv run server` — FastAPI server at localhost:3000
- `uv run pytest` — Run tests
- `uv sync` — Install dependencies

### Docker
- `docker-compose up` — Full dev stack (PostgreSQL + server + client)
- `docker-compose up db` — PostgreSQL only (postgres:18-alpine on port 5432)

### Linting
- **Python**: ruff (line-length=140, rules: E, F, I, ignores E501)
- **TypeScript**: eslint with react-hooks and react-refresh plugins

## Architecture

### Tech Stack
- **Client**: React 19 + TypeScript + Vite + TailwindCSS 4 + TanStack Router v1 (file-based routing)
- **Server**: Python 3.13+ + FastAPI + SQLModel (SQLAlchemy ORM) + scikit-learn
- **Database**: PostgreSQL 18, auto-created tables via `SQLModel.metadata.create_all()` on startup (no Alembic)
- **Package managers**: pnpm (client), uv (server)

### Server Layered Architecture
```
routers/  →  services/  →  models.py (SQLModel tables)
              ↓                ↓
           views/          database.py (session dependency)
              ↓
           schemas/ (Pydantic response models)
```
- **Routers**: HTTP endpoint definitions, delegate to services
- **Services**: Business logic and SQL queries
- **Views**: Response formatting/aggregation
- **Schemas**: Pydantic models for response validation
- **Models**: SQLModel table definitions (Student, Grade, Class, Teacher, Subject, AttendanceRecord, ImportLog, etc.)

### Client Architecture
- **Routing**: TanStack Router file-based routing in `src/routes/` — files map directly to URL paths
- **Server state**: React Query (`@tanstack/react-query`)
- **Client state**: Zustand (`lib/config-store.ts`) for server config
- **Filters**: React Context (`FilterContext.tsx`) — cascading class→teacher→subject filters
- **API layer**: `lib/api/` — typed fetch functions per domain, validated with Zod schemas from `lib/types/`
- **i18n**: Hebrew only (RTL), i18next with namespace JSON files in `i18n/locales/he/`
- **UI components**: Radix UI + shadcn pattern in `components/ui/`

### Key Patterns
- All API routes prefixed with `/api/` (registered in `server/src/main.py`)
- Frontend uses `@` path alias for imports (e.g., `@/components/ui/button`)
- Database uses UUID PKs for most entities, `student_tz` (ID number) as PK for students
- Data ingestion parses Hebrew column headers from Excel files
- File deduplication via SHA-256 checksum

## Environment Variables

### Server (`server/.env`)
- `DATABASE_URL` — PostgreSQL connection (default: `postgresql://postgres:postgres@localhost:5432/student_personalizer`)
- `ORIGIN_URL` — CORS allowed origin (default: `http://localhost:5173`)
- `PORT` — Server port (default: `3000`)

### Client (`client/.env`)
- `VITE_API_URL` — API base URL

## Key Configuration (`server/src/constants.py`)
- `AT_RISK_GRADE_THRESHOLD = 55` — Students below this average are "at-risk"
- Performance weights: grades 60%, attendance 25%, behavior 15%
- ML: min 5 training samples, high risk ≥ 0.7, medium risk ≥ 0.3
