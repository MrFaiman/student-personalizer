# Student Personalizer - client

Hebrew (RTL) web app for the pedagogical dashboard: grades, attendance, ingestion, analytics, and ML predictions. It talks to the FastAPI backend under `/api`.

## Stack

- **React 19** + **TypeScript** + **Vite 7**
- **TanStack Router** (file-based routes in `src/routes/`)
- **TanStack Query** for server state
- **Zustand** for auth and config
- **Tailwind CSS 4** + **Radix UI** (shadcn-style components in `src/components/ui/`)
- **i18next** - locale files in `src/i18n/locales/he/`

## Prerequisites

- **Node.js** 20+
- **pnpm** 9+ (the repo pins a version in `packageManager` in `package.json`; use `corepack enable` if you rely on Corepack)

## Setup

```bash
pnpm install
```

Create `client/.env` (optional for local dev; defaults target the usual backend port):

```env
VITE_API_URL=http://localhost:3000
```

The API client sends cookies with requests (`credentials: "include"`) for refresh-token auth.

## Scripts

| Command | Purpose |
|--------|---------|
| `pnpm dev` | Dev server (default [http://localhost:5173](http://localhost:5173)) |
| `pnpm build` | `tsr generate` → TypeScript project references → production Vite build |
| `pnpm preview` | Serve the `dist/` output locally |
| `pnpm lint` | ESLint |

After adding or renaming route files, the TanStack Router plugin updates codegen in dev; `pnpm build` runs `tsr generate` explicitly so CI and Docker builds stay in sync.

## Project layout

- `src/routes/` - URL tree (TanStack Router file routes)
- `src/lib/api/` - Typed `fetch` helpers per domain
- `src/lib/types/` - Zod schemas / shared types aligned with API responses
- `src/lib/auth-store.ts` - Auth session (Zustand + selective `localStorage` persistence)
- `src/components/` - Feature UI and shared layout
- `@/` - Path alias to `src/` (see `tsconfig` / Vite)

## Production build (Docker)

The image is built from `Dockerfile.prod` at the repo root context (`client/`). Pass the public API URL at build time:

```bash
docker build -f Dockerfile.prod . --build-arg VITE_API_URL=https://your-api.example.com
```

See the root `docker-compose.prod.yml` and `.env.example` for a full stack example.
