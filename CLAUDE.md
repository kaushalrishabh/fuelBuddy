# FuelBuddy — conventions for Claude Code

Personal single-user app to log motorcycle refuels and compute mileage/cost analytics. Quality of the
data and insights is the top priority; keep everything else simple.

## Stack

- **Frontend** (`frontend/`): Next.js App Router + TypeScript, Tailwind v4, shadcn/ui, Recharts,
  TanStack Query, React Hook Form + Zod. `npm` for packages.
- **Backend** (`backend/`): FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, MySQL (via PyMySQL),
  `uv` for packages/venv.
- **DB**: MySQL 8, local via `docker-compose.yml`; production on a MySQL-compatible serverless host
  (TiDB Cloud / Aiven). All schema changes go through Alembic migrations — never hand-edit the DB.

## Hard rules (do not relitigate without asking)

- **No delete endpoints or buttons, anywhere.** Editing is allowed and every edit is recorded in
  `entry_audit`. Bad data is neutralized by marking it `faulty`/logging an odometer event, not by
  deleting it.
- **Auth**: single seeded user (from `ADMIN_EMAIL`/`ADMIN_PASSWORD`, no signup). JWT in an httpOnly
  cookie with `SameSite=None; Secure` (frontend and backend are cross-origin in prod — Vercel vs
  Render/Railway). CORS allows only the exact `FRONTEND_ORIGIN`, `credentials: true`. State-changing
  requests also require a custom header (e.g. `X-FuelBuddy-Client`) as a CSRF mitigation.
- **Mileage engine lives in `backend/app/services/mileage.py` as pure, unit-tested functions** —
  never duplicate this math in an API route or in the frontend.
  - Full-to-full segments: a segment runs between two consecutive `full` refuels; interior `partial`
    fills and `fuel_removed` entries attach to the segment they fall inside.
  - `effective_odometer(entry)` = raw reading + cumulative offset from every `replaced`/`reset`
    `odometer_event` at or before that date (offset = `old_reading_at_change − new_reading_at_change`).
  - `distance_override_km` lives on the entry that **closes** a segment, not the one that opens it.
  - Segment status precedence: **override > faulty > anomalous > valid**. A `distance_override_km`
    rescues an otherwise-faulty segment rather than being blocked by it.
  - A `fuel_removed` entry attaches to the segment where `opening_fill.date < removal.date <= closing_fill.date`.
- Env vars only, via `.env` (see `.env.example` for the full documented list). Nothing hard-coded.
  Never commit `.env`.

## Commands

```bash
# Backend (run from backend/)
uv sync                # install deps
uv run uvicorn app.main:app --reload
uv run pytest -q
uv run ruff check .
uv run mypy app

# Frontend (run from frontend/)
npm run dev
npm run lint
npx tsc --noEmit

# Full stack locally
docker compose up
```

## Git

- Small, meaningful commits per phase, conventional commit messages (`feat:`, `fix:`, `chore:`, …).
- Do not push or create/touch the GitHub remote unless explicitly asked.
