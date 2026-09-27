# Railway Deployment Preparation

CasePilot deploys as two Railway services from this monorepo. The repository contains separate production Dockerfiles for the FastAPI backend and Next.js frontend. Preparing these files does not create services or trigger a deployment.

## Service setup

Create one Railway project with two services connected to this repository and branch:

| Service | Root directory | `RAILWAY_DOCKERFILE_PATH` | Health check | Watch paths |
| --- | --- | --- | --- | --- |
| `casepilot-api` | `/` | `/apps/api/Dockerfile` | `/health/ready` | `/apps/api/**` |
| `casepilot-web` | `/` | `/apps/web/Dockerfile` | `/signin` | `/apps/web/**`, `/package.json`, `/pnpm-lock.yaml`, `/pnpm-workspace.yaml` |

Keep the root directory at `/` for both services. The frontend build needs the root `pnpm-lock.yaml` and workspace files. Set the Dockerfile path as a Railway service variable, and configure the health check and watch paths under each service's settings. Use an on-failure restart policy with at most three retries.

New Railway services cannot opt into the deprecated `railway.toml` configuration flow. The table above is the service-setting manifest to apply in Railway; the Dockerfiles remain versioned with the application.

Generate a public Railway domain for both services before setting cross-service variables. Do not set `PORT`; Railway injects it and both images bind to it.

## Frontend service

Set these variables on `casepilot-web` before its first deployment:

```env
RAILWAY_DOCKERFILE_PATH=/apps/web/Dockerfile
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<Supabase anon or publishable key>
NEXT_PUBLIC_API_BASE_URL=https://${{casepilot-api.RAILWAY_PUBLIC_DOMAIN}}/v1
```

If Railway does not expand a reference inside the URL, enter the generated backend URL explicitly, including `https://` and the `/v1` suffix.

`NEXT_PUBLIC_*` values are embedded during `next build`. Changing them requires a frontend redeployment. The Supabase anonymous key is browser-safe because database access is protected by RLS. Never configure a service-role key, database password, Groq key, or Railway credential on the frontend service.

## Backend service

Set these variables on `casepilot-api` before its first deployment:

```env
RAILWAY_DOCKERFILE_PATH=/apps/api/Dockerfile
APP_ENV=production
APP_NAME=CasePilot API
ALLOWED_ORIGINS=https://${{casepilot-web.RAILWAY_PUBLIC_DOMAIN}}
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<Supabase anon or publishable key>
GROQ_API_KEY=<Groq API key>
GROQ_MODEL=openai/gpt-oss-20b
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

If Railway does not expand the URL reference, enter the generated frontend origin explicitly with `https://` and no trailing path. Add `http://localhost:3000` as a comma-separated second origin only when a local frontend must call the deployed API.

`GROQ_API_KEY` and `GROQ_MODEL` are required for server-only analysis and case chat. Never expose Groq values to the frontend. Analysis uses FastAPI in-process background tasks, so run one backend replica for this hackathon. Chat is synchronous and can include one provider retry.

## Supabase Auth configuration

After Railway assigns the frontend domain, set it as the Supabase Auth Site URL and add these redirect URLs:

```text
https://<casepilot-web-domain>/**
http://localhost:3000/**
```

Keep the localhost redirect only while local development is needed.

## Deployment order and smoke checks

1. Create both services and generate their public domains.
2. Add backend and frontend variables without committing any secret values.
3. Deploy `casepilot-api` and wait for `/health/ready` to pass.
4. Deploy `casepilot-web`; its public API URL is embedded during the build.
5. Update Supabase Auth URLs.
6. Verify:
   - `GET https://<api-domain>/health` returns `status: ok` and `environment: production`.
   - `GET https://<api-domain>/health/ready` returns `status: ready`.
   - `https://<web-domain>/signin` loads over HTTPS.
   - Sign-in, dashboard, upload, analysis, review workflow, evidence chat, and sign-out work in the deployed browser app.
   - Browser requests have no CORS errors and no secret backend values appear in the frontend bundle.

The readiness health check deliberately verifies Supabase connectivity. A backend deployment remains unhealthy until `SUPABASE_URL` and `SUPABASE_ANON_KEY` are correct.

## Local environment

Create `apps/web/.env.local` from `apps/web/.env.example`. It contains only browser-safe Supabase and API values and is ignored by Git. Keep backend credentials in `apps/api/.env`. Never copy either local environment file into Railway source control; enter production values through Railway Variables.
