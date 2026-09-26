# Frontend Tasks — Stage 1 Integration

## Goal

Turn the existing Next.js UI into a working authenticated Stage 1 workspace. Use Supabase only for authentication and use FastAPI for all CasePilot case data.

## Before starting

1. Pull the latest `main` branch and run `pnpm install` from the repository root.
2. Create `apps/web/.env.local` from `apps/web/.env.example`.
3. Start the frontend with `pnpm dev:web` and the API with `pnpm dev:api`.
4. Review [Frontend Auth and database-schema handover](frontend-auth-and-schema-handover.md) and [API handover](api-handover.md).

## Task group 1 — Authentication and session handling

The `/signin` and `/signup` screens are already wired to Supabase Auth. Complete the application-level behavior around them.

1. Confirm sign-up shows the email-confirmation message when Supabase returns no session.
2. Confirm sign-in routes an authenticated user to `/dashboard`.
3. Add an application session provider or equivalent shared session state.
4. Redirect unauthenticated visitors from `/dashboard` and every `/cases/*` route to `/signin`.
5. Redirect authenticated visitors away from `/signin` and `/signup` to `/dashboard`.
6. Add a sign-out action in the workspace navigation using `supabase.auth.signOut()`.
7. On a FastAPI `401`, clear the stale session and route the user to `/signin`.
8. Do not display access tokens in the UI. The development-only console token is for Postman testing only.

### Completion check

- A new user can sign up, sign in, refresh the page, and remain signed in.
- A signed-out user cannot open dashboard or case routes.
- Signing out returns the user to `/signin`.

## Task group 2 — Shared API client

Create a small API client in `apps/web/lib/`.

1. Retrieve the current Supabase session before each protected request.
2. Send `Authorization: Bearer <session.access_token>` to FastAPI.
3. Use `NEXT_PUBLIC_API_BASE_URL` as the base URL. It already includes `/v1`.
4. Parse the standard FastAPI error shape: `{ "detail": "..." }`.
5. Handle these states consistently:

| Status | Required behavior |
| --- | --- |
| `401` | Sign out and route to `/signin`. |
| `404` | Show “Case not found” and return to dashboard. |
| `409` | Keep entered values and show duplicate Case ID guidance. |
| `422` | Show validation feedback beside the affected form field. |
| `503` | Show a retry action and do not present stale writes as successful. |

### Completion check

- The API client never sends a token from a hard-coded value or environment variable.
- Browser code never contains Supabase service-role, NVIDIA, database, or Railway secrets.

## Task group 3 — Dashboard integration

Replace dashboard mock data with `GET /dashboard`.

1. Fetch data after a valid session is available.
2. Render `metrics.total_cases`, `metrics.in_review`, `metrics.pending_tasks`, and `metrics.unresolved_issues`.
3. Render `cases` sorted as returned by the API.
4. Render up to ten `recent_activity` records.
5. Display a loading state while fetching, an empty state when there are no cases, and a recoverable error state when the request fails.
6. Use `case.id` for routes and `case.case_id` as the visible Case ID.
7. Do not invent document counts, issue counts, or AI status values until their API endpoints exist.

### Completion check

- A case created through the API appears on dashboard refresh.
- The dashboard shows `0` for pending tasks and unresolved issues during Stage 1.

## Task group 4 — Create Case integration

Replace the Create Case dummy submit handler with `POST /cases`.

1. Keep only two inputs: `case_id` and `case_name`.
2. Trim values before submission.
3. Validate required values before sending.
4. Show the API `409` message when the active Case ID already belongs to the signed-in user.
5. On a `201` response, route to `/cases/<case.id>/overview`.
6. Disable repeated submissions while the request is active.

### Completion check

- Creating `PROP-001 — Rao v Mehta` returns the user to its case workspace.
- A duplicate active Case ID stays on the form and shows an understandable error.

## Task group 5 — Case shell and supported case actions

Use the current Stage 1 endpoints only.

1. Fetch `GET /cases/{caseId}` for the case header.
2. Render case name, visible Case ID, and status badge.
3. Implement case name/Case ID editing using `PATCH /cases/{caseId}`.
4. Implement archive using `DELETE /cases/{caseId}` and return to dashboard on success.
5. Offer restore only from an archived-case view when `GET /cases?include_archived=true` is added to the UI.
6. Keep Documents, Timeline, Issues, Tasks, and Chat as clearly labeled placeholders until their backend routes exist.

### Completion check

- A user can open, rename, archive, and restore only their own case.
- An unknown or unowned case shows the standard not-found state.

## Out of scope for this frontend batch

- Document upload and reader integration.
- Analysis controls, polling, timeline, issues, tasks, evidence citations, and chat.
- Direct browser access to Supabase database tables.
- Any legal conclusion or autonomous action.

Those items start after the Stage 2 backend document APIs are available.

## Final verification

Run this sequence with a normal user account:

1. Sign in.
2. Open the dashboard.
3. Create a case.
4. Refresh dashboard and confirm the case appears.
5. Open the case and update its name.
6. Archive the case and confirm it leaves the active list.
7. Restore it and confirm it returns to the active list.
8. Sign out and confirm protected pages redirect to sign-in.

Record passed checks in [Project Status](project-status.md). Do not mark the dashboard or case-shell integration Verified until this sequence passes against the running FastAPI service.
