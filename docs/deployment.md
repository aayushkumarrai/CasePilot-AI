# Deployment Configuration

## Frontend — Vercel

Import the GitHub repository in Vercel and set the **Root Directory** to `apps/web`. Vercel detects the Next.js application and uses `pnpm build` automatically.

Set these environment variables in Vercel for **Preview** and **Production** before deploying:

```env
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<Supabase anon or publishable key>
NEXT_PUBLIC_API_BASE_URL=https://<railway-api-domain>/v1
```

`NEXT_PUBLIC_*` values are embedded in the browser build. The Supabase anonymous key is acceptable here because it is restricted by Supabase Row Level Security. Never configure a service-role key, database password, Groq key, or Railway credential in Vercel frontend variables.

After the first Vercel deployment, add its deployed URL in Supabase Auth **URL Configuration** as the Site URL and an allowed redirect URL. Add the Vercel preview URL too if preview authentication is required.

## Backend — Railway

Create a Railway service from the same repository with the root directory `apps/api`. Use this start command:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set these Railway variables:

```env
APP_ENV=production
APP_NAME=CasePilot API
ALLOWED_ORIGINS=https://<vercel-production-domain>,https://<vercel-preview-domain>
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<Supabase anon or publishable key>
GROQ_API_KEY=<Groq API key>
GROQ_MODEL=openai/gpt-oss-20b
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

`GROQ_API_KEY` and `GROQ_MODEL` are required for the server-only analysis client. `GROQ_BASE_URL` defaults to Groq's OpenAI-compatible endpoint. Do not set any Groq value in Vercel or another browser-visible environment. Stage 3.4 analysis uses FastAPI in-process background tasks, so deploy a single Railway application process for the hackathon; durable queues and cross-process job recovery are deferred.

Use the deployed Railway URL as `NEXT_PUBLIC_API_BASE_URL` in Vercel, then redeploy the frontend. Public frontend values are fixed during the Next.js build, so an environment change needs a new Vercel deployment.

## Local environment

Create `apps/web/.env.local` from `apps/web/.env.example`. It contains only browser-safe Supabase and API values and is ignored by Git. Keep the backend credentials in `apps/api/.env`.
