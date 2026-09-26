# Development Setup

## One-time setup

1. Copy `apps/web/.env.example` to `apps/web/.env.local` and enter the Supabase project URL, anonymous key, and local API URL. Next.js loads `.env.local` automatically; it must remain uncommitted.
2. Copy `apps/api/.env.example` to `apps/api/.env` and enter backend-only Supabase and Groq credentials.
3. Never place `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, or `GROQ_API_KEY` in the frontend environment file.

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

Stages 1 and 2 are verified after both services run locally, the backend tests pass, and the documented Postman ownership test returns `404` for a second user. For Stage 2, also run the signed upload, registration, extraction, reader, retry, and unsupported-file requests in the Stage 2 collection.

## Verify Groq locally

After adding `GROQ_API_KEY` to `apps/api/.env`, run:

```bash
cd apps/api && .venv/bin/python -u -m scripts.smoke_groq
```

The command sends synthetic evidence only. A successful run prints typed output with citations; it does not access Supabase or persist any data.

## Verify Stage 3.3 with Supabase

After applying the Stage 3.3 migrations, run the opt-in integration test against a disposable owned case with a ready passage. It creates a run, completes it with fixture output, and verifies that the case-summary citation is stored against the analysis run.

```bash
cd apps/api
RUN_SUPABASE_INTEGRATION_TESTS=1 \
STAGE3_TEST_ACCESS_TOKEN=<user-jwt> \
STAGE3_TEST_CASE_ID=<owned-case-uuid> \
STAGE3_TEST_PASSAGE_ID=<passage-uuid> \
.venv/bin/python -m pytest -m integration -q
```

Use a quote that is actually present in the specified passage if you also test the Stage 3.3 Python citation gate. The RPC fixture itself validates ownership and target relationships; quote-substring validation is enforced by the internal citation gate before Stage 3.4 calls the RPC.
