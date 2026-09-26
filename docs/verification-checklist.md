# Pre-Demo Verification Checklist

Use this checklist on the final demo environment. Record the date, person, and evidence URL or screenshot in `project-status.md`.

## Stage 1 verification record — 2026-09-26

| Workflow | Result | Evidence |
| --- | --- | --- |
| FastAPI unit/API suite | Passed | 8 tests passed locally. |
| Local health and readiness | Passed | `/health` and `/health/ready` returned `200`. |
| Supabase email/password authentication | Passed | Supabase JWT obtained through the Next.js sign-in flow. |
| Case lifecycle | Passed | Postman verified create, duplicate conflict, list, get, update, validation, archive, restore, dashboard, and activity history. |
| Owner isolation | Passed | A second authenticated user received `404` for the first user’s case. |

## Stage 2 automated verification record — 2026-09-26

| Workflow | Result | Evidence |
| --- | --- | --- |
| Backend unit/API suite | Passed | 14 tests passed locally, including TXT/DOCX extraction, signed-upload registration flow, stable passages, unsupported-file state, and retry. |
| Remote schema migration | Passed | `20260926113000_stage2_documents.sql` applied to linked Supabase project. |
| Live signed TXT upload and extraction | Passed | Postman received a signed private URL, registered the object, observed `uploaded → ready`, and read two stable passages. |
| Live signed PDF upload and private reading | Passed | Postman verified PDF upload, extraction lifecycle, and ready-document signed read behavior. |
| Live unsupported-file state | Passed | Postman registered JPG metadata and received `unsupported` with its safe explanation. |
| Live DOCX upload and passage extraction | Passed | Confirmed during Stage 2 Postman verification. |
| Live failed-document retry | Passed | Confirmed during Stage 2 Postman verification. |
| Live Storage owner isolation | Passed | Confirmed with two distinct Supabase users during Stage 2 Postman verification. |

## Stage 3.1 verification record — verified

| Workflow | Result | Evidence |
| --- | --- | --- |
| Analysis-foundation migration | Passed | `20260926150000_stage3_analysis_foundation.sql` and corrective lint migration applied. |
| Remote schema lint | Passed | Linked Supabase schema lint returned no errors. |
| Lifecycle fixture output | Passed | Internal Postman fixture completed a processing run with a context snapshot, case summary, cited output, and completion timestamp. |
| Two-user RLS | Passed | Confirmed with a second authenticated user during Stage 3.1 Postman verification. |

## Stage 3.2 verification record — verified

| Workflow | Result | Evidence |
| --- | --- | --- |
| Mocked Groq client | Passed | Typed output, JSON-object request, context boundary, timeout, retry, and invalid-response tests pass locally. |
| Live Groq smoke request | Passed | 2026-09-27: `scripts.smoke_groq` completed in 1.262 seconds using `openai/gpt-oss-20b`. The validated synthetic result included a summary, document summary, conflict, proposed task, and three passage-linked citations. |

## Stage 3.3 verification record — in progress

| Workflow | Result | Evidence |
| --- | --- | --- |
| Local evidence and citation-gate tests | Passed | 2026-09-27: focused tests cover deterministic ordering, exact evidence size limit, normalized quote checks, invalid-citation filtering, uncited-summary rejection, and dependent-task filtering. |
| Case-summary citation schema migration | Passed | 2026-09-27: `20260927130000` and `20260927130100` applied to the linked project; `supabase db lint --linked` returned no schema errors. |
| Live owner-safe fixture | Pending | Complete a fixture run with a `case_summary` citation and confirm `analysis_citations.analysis_run_id` is populated. |

## Setup

- [ ] GitHub repository contains current documentation and implementation branch.
- [ ] Supabase Auth email/password flow works.
- [ ] Supabase Storage bucket is private.
- [ ] Railway API health endpoint returns success.
- [ ] Vercel uses the deployed Railway API URL.
- [ ] Groq key is present on Railway only and never in frontend environment variables.

## Case flow

- [ ] Create Case accepts only Case ID and case name.
- [ ] Dashboard shows created case and correct status.
- [ ] Upload accepts PDF, DOCX, and TXT.
- [ ] Upload blocks a file over 50 MB and more than 50 documents.
- [ ] Unsupported file is visible and explains why it was not analyzed.
- [ ] Lawyer-provided context is optional, limited to 4,000 characters, and remains visible after an upload or analysis failure.
- [ ] Analyze Case starts only after explicit user action.
- [ ] Completed analysis changes the case to Review.

## Evidence and review

- [ ] Overview shows summary, pending details, and confirmed details separately.
- [ ] Every displayed factual finding has a working citation.
- [ ] Lawyer-provided context is labeled separately and never appears as cited document evidence.
- [ ] PDF citation opens the right page or passage label.
- [ ] DOCX/TXT citation opens the right extracted passage.
- [ ] Conflict view shows both source accounts.
- [ ] Gap wording says “not found in uploaded material.”
- [ ] Confirm/Edit/Reject field actions persist after refresh.

## Tasks and chat

- [ ] AI-proposed task begins as Proposed.
- [ ] Manual task creation works.
- [ ] Approve, Reject, and Done actions persist and appear in activity history.
- [ ] Evidence chat answer displays a valid citation.
- [ ] General chat answer displays the required general-guidance label.
- [ ] Chat history remains after page refresh.

## Presentation readiness

- [ ] The fictional property-dispute packet is uploaded and analyzed in the demo account.
- [ ] Browser has the deployed application open and signed in.
- [ ] A fallback screen recording or screenshots are prepared.
- [ ] Demo script was rehearsed once without backend errors.
- [ ] Project readiness is marked Ready in `project-status.md`.
