# FuelBuddy

A lightweight personal web app for logging motorcycle refuels and getting high-quality mileage and
cost insights — built to replace years of free-text notes with a proper, trustworthy record.

Handles two real-world data problems that would otherwise corrupt mileage analysis: fuel drained
from the tank for non-riding use, and periods of faulty or replaced odometers.

## Stack

- **Frontend**: Next.js (App Router) + TypeScript, Tailwind CSS, shadcn/ui, Recharts, TanStack Query
- **Backend**: FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, `uv`
- **Database**: MySQL 8

## Local development

1. Copy `.env.example` to `.env` and fill in values (at minimum `ADMIN_EMAIL`, `ADMIN_PASSWORD`,
   `JWT_SECRET`).
2. Start everything:
   ```bash
   docker compose up
   ```
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000 (docs at `/docs` in development)
   - MySQL: `localhost:3306`

Or run the two apps directly without Docker:

```bash
# backend
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# frontend
cd frontend
npm install
npm run dev
```

## Testing

```bash
cd backend && uv run pytest -q
cd frontend && npm run lint && npx tsc --noEmit
```

## Deployment

_Coming once the app is feature-complete: frontend on Vercel, backend on Render/Railway, database on
TiDB Cloud Serverless or Aiven._

## Project conventions

See [CLAUDE.md](./CLAUDE.md) for the data model, mileage-engine rules, and auth architecture.
