# Frontend Auth and Database Schema Handover — Stage 1

This document gives the frontend team what it needs to build email/password sign-up and sign-in, keep a session, and call the protected FastAPI routes. The browser connects directly to Supabase Auth. It never receives a service-role key.

## Frontend environment

Create `apps/web/.env` from `apps/web/.env.example`:

```env
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<Supabase publishable-or-anon-key>
VITE_API_BASE_URL=http://localhost:8000/v1
```

`VITE_SUPABASE_ANON_KEY` is intended for browser use with Row Level Security. Do not add `SUPABASE_SERVICE_ROLE_KEY`, `NVIDIA_API_KEY`, database passwords, or Railway credentials to the frontend.

Install the browser client:

```bash
pnpm --filter web add @supabase/supabase-js
```

## One shared client

Create `apps/web/src/lib/supabase.ts`:

```ts
import { createClient } from "@supabase/supabase-js";

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY,
);
```

Create one client for the app, not one per component. The client persists the signed-in session in browser storage and refreshes access tokens when possible.

## Sign-up flow

The `/signup` page contains email, password, and optional display name.

```ts
const { data, error } = await supabase.auth.signUp({
  email,
  password,
  options: {
    data: { display_name: displayName.trim() || undefined },
    emailRedirectTo: `${window.location.origin}/login`,
  },
});
```

If `error` exists, show its message next to the form. If `data.session` is present, route to `/dashboard`. If it is absent, show: “Check your email to confirm your account, then sign in.” Supabase creates `auth.users`; the database trigger creates the matching `public.profiles` row automatically.

For demo-only testing, a project administrator may disable **Confirm email** in Supabase Auth settings. Keep email confirmation enabled for any deployed public version.

## Sign-in and sign-out

```ts
const { data, error } = await supabase.auth.signInWithPassword({ email, password });
if (!error && data.session) navigate("/dashboard");

await supabase.auth.signOut();
navigate("/login");
```

On application start, call `supabase.auth.getSession()`. Subscribe to `supabase.auth.onAuthStateChange` so the UI responds to token refresh, sign-out, and expired sessions.

## Calling FastAPI with the user token

Before every protected FastAPI request, obtain the current session. Do not cache a token in a module variable because Supabase can refresh it.

```ts
export async function apiFetch(path: string, init: RequestInit = {}) {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) throw new Error("Please sign in again.");

  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
      ...init.headers,
    },
  });

  if (response.status === 204) return null;
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail ?? "Request failed");
  return body;
}
```

Use `GET /v1/me` after sign-in as the profile readiness check. A `503` with “Profile is missing” indicates that the Supabase profile trigger was not deployed correctly; do not create the profile from the frontend.

## Required UI behavior

| Situation | UI action |
| --- | --- |
| No session | Redirect protected pages to `/login`. |
| `401` from FastAPI | Clear the stale session and redirect to `/login`. |
| `404` for a case | Show “Case not found” and return to dashboard. Do not infer whether another user owns it. |
| `409` on create/update/restore | Keep form values and show “An active case already uses this Case ID.” |
| `422` | Display field validation errors without clearing the form. |
| `503` | Show a retry action; do not claim the case was saved. |

## Database schema the frontend can rely on

Frontend code should use FastAPI responses for case data. It may use Supabase Auth directly, but should not query or mutate the tables below directly in Stage 1.

### `profiles`

| Column | Type | Meaning |
| --- | --- | --- |
| `id` | UUID | Same ID as `auth.users.id`; primary key. |
| `email` | text | Email supplied by Supabase Auth. |
| `display_name` | text nullable | Initial value from sign-up metadata. |
| `created_at`, `updated_at` | timestamptz | UTC timestamps. |

RLS allows a signed-in user to read and update only their own profile.

### `cases`

| Column | Type | Meaning |
| --- | --- | --- |
| `id` | UUID | Internal identifier. Use this in API path parameters. |
| `owner_id` | UUID | Authenticated owner; never send it from the frontend. |
| `external_case_id` | text | User-entered Case ID, returned by FastAPI as `case_id`. |
| `case_name` | text | User-entered case name. |
| `status` | enum | `draft`, `processing`, `review`, or `ready`; Stage 1 creates `draft`. |
| `archived_at` | timestamptz nullable | Set when archived; restored cases reset it to `null`. |
| `created_at`, `updated_at` | timestamptz | UTC timestamps. |

Only one active `external_case_id` is permitted for the same owner. Archived cases do not block reuse of their Case ID.

### `activity_events`

| Column | Type | Meaning |
| --- | --- | --- |
| `id` | UUID | Event ID. |
| `case_id` | UUID | Related case. |
| `actor_id` | UUID | User who performed the action. |
| `actor_type` | text | `user`, `ai`, or `system`; Stage 1 writes `user`. |
| `action` | text | `case_created`, `case_updated`, `case_archived`, or `case_restored`. |
| `details` | JSONB | Safe metadata, such as changed field names. |
| `created_at` | timestamptz | UTC timestamp. |

RLS permits reading activity only for owned cases. The dashboard returns up to ten recent events; a standalone activity endpoint is a later stage.

## Auth-to-API smoke test

1. Create an account or sign in.
2. In the browser console, run `const { data } = await supabase.auth.getSession(); copy(data.session?.access_token)`.
3. Import the Stage 1 Postman collection and environment.
4. Put the token only in the Postman environment’s `access_token` value. Never commit or share it.
5. Run `GET /v1/me`, then the Case lifecycle folder in order.

The Postman collection also obtains and stores the token automatically when its Supabase **Sign in** request succeeds.
