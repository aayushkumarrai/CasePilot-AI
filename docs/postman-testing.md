# Postman Testing — Full Pipeline Through Stage 3.3

Import these files into Postman:

- `postman/CasePilot-AI-Full-Pipeline-Stage-3.3.postman_collection.json`
- `postman/CasePilot-AI-Local.postman_environment.json`
- `postman/CasePilot-AI-Stage-3.4-Public-Analysis.postman_collection.json`

The full-pipeline collection is intentionally **flat**: it has no folders and contains 35 requests numbered in the order they must be run. It is the maintainer verification path for every implemented capability from Stage 1 through Stage 3.3. The older Stage 1, Stage 2, and Stage 3.1 collections remain as focused references only.

Set `api_base_url` to the local or Railway URL. Do not put `/v1` in that value: the collection adds it for versioned FastAPI routes. Set `supabase_url` and `supabase_anon_key` only in the active local Postman environment. Keep `access_token`, signed upload URLs, generated IDs, test email, and password in that environment; never export populated values or commit them.

## Before starting

1. Start FastAPI and confirm requests 01 and 02 return `200`.
2. Select the local environment and enter `supabase_url`, `supabase_anon_key`, `test_email`, and `test_password`.
3. Use a fictional dedicated test account. If email confirmation is enabled, confirm it before request 03.
4. Start at request 01 and run each request once in numeric order. Request 14 is the only polling request: repeat it manually until the TXT document reports `ready`.

Request 03 authenticates with Supabase and saves the short-lived bearer token as `access_token`. The collection creates a timestamped Case ID and automatically saves `case_uuid`, storage values, `document_uuid`, the first stable `passage_uuid`, and `analysis_run_uuid` as later requests need them. Each request checks its expected response status and writes the body to the Postman console; Postman also shows the body in its response pane.


## Stage 3.4 public analysis check

Use `CasePilot-AI-Stage-3.4-Public-Analysis.postman_collection.json` with an active `case_uuid` that already has at least one ready document. It signs in, starts analysis through FastAPI, and provides a polling request to repeat every 2–3 seconds while active. The collection contains no Groq credential and does not call internal Supabase analysis RPCs.

## What the collection verifies

| Request range | Verification |
| --- | --- |
| 01–05 | FastAPI liveness/readiness, Supabase sign-in, current user, and empty/current dashboard contract. |
| 06–09 | Owner-scoped case creation, listing, read, and update. |
| 10–17 | Private signed TXT upload, registration, asynchronous extraction, stable passage IDs, unsupported-file visibility, and retry rejection for a ready document. |
| 18–20 | Internal analysis-run lifecycle, non-evidence lawyer context snapshot, and a grounded fixture completion. |
| 21–29 | Immutable run outputs, normalized citations, and activity history read through owner-scoped Supabase REST access. |
| 30–35 | Review case status, soft archive, active/archived filtering, restore, and final test-data cleanup. |

The fixture TXT in request 11 is fictional property-dispute material. Request 20 includes a visible structured result with a case summary, document summary, payment field, Rao and Mehta parties, payment timeline event, possession conflict, missing-handover gap, proposed task, and normalized citations. Each quote is an exact substring of that uploaded passage.

## Stage 3.3 boundary

Request 20 exercises the existing Supabase persistence lifecycle with a fixture that represents output **after** Stage 3.2 Groq validation and the Stage 3.3 evidence/citation gate. Postman never calls Groq directly and never contains `GROQ_API_KEY`. Groq remains server-only until the later public analysis orchestration route is implemented.

## Expected results

- Request 14 eventually returns the TXT document with `status: "ready"`; request 15 saves its first stable passage ID.
- Request 16 records the JPG as `unsupported` without blocking the TXT document.
- Request 17 returns `409` because a ready document cannot be retried.
- Request 20 completes the run and changes the pipeline case to `review`.
- Requests 21–28 return only output associated with the saved analysis-run ID, including a `case_summary` citation and eight output citations.
- Request 30 shows the pipeline case in `review`.
- Requests 31–35 prove archive filtering and leave the generated test case archived.

## Security rules while testing

- Use only fictional data and a dedicated test account.
- A bearer token is equivalent to a temporary password. Keep it in an unshared environment and obtain a new one by rerunning request 03 when it expires.
- The direct Supabase RPC and table-read requests are maintainer verification for already implemented internal lifecycle storage. The frontend must continue to use FastAPI only; it must not call these RPCs or receive provider credentials.
- Do not use a Supabase service-role key in Postman, the frontend, or this collection.
- Sign in as a second test account separately if you need to re-run owner-isolation checks. Do not modify another account’s records.

## Stage 3.5 persisted review reads

Import `postman/CasePilot-AI-Stage-3.5-Review-Reads.postman_collection.json` with the local environment. Set `case_uuid` to an active case whose Stage 3.4 run has completed. Run Sign In, then Overview, Timeline, Issues, Tasks, and Activity in that order. The collection verifies the FastAPI response shapes and source-linked citations without direct reads from Supabase analysis tables.
