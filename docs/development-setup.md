# Development Setup

## One-time setup

1. Copy `apps/web/.env.example` to `apps/web/.env.local` and enter the Supabase project URL, anonymous key, and local API URL. Next.js loads `.env.local` automatically; it must remain uncommitted.
2. Copy `apps/api/.env.example` to `apps/api/.env` and enter backend-only Supabase and NVIDIA credentials.
3. Never place `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, or `NVIDIA_API_KEY` in the frontend environment file.

## Run locally

From the repository root:

```bash
pnpm install
uv sync --directory apps/api --all-groups
pnpm dev:web
pnpm dev:api
```

The Next.js frontend runs on `http://localhost:3000`; FastAPI runs on `http://localhost:8000`; FastAPI health is available at `http://localhost:8000/health`.

## Validate the foundation

```bash
pnpm --dir apps/web build
uv run --directory apps/api pytest
```

Stage 1 is verified after both services run locally, the backend tests pass, and the documented Postman ownership test returns `404` for a second user.
