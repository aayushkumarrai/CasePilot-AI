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

## Stage 3.3 verification record — verified

| Workflow | Result | Evidence |
| --- | --- | --- |
| Local evidence and citation-gate tests | Passed | 2026-09-27: focused tests cover deterministic ordering, exact evidence size limit, normalized quote checks, invalid-citation filtering, uncited-summary rejection, and dependent-task filtering. |
| Case-summary citation schema migration | Passed | 2026-09-27: `20260927130000` and `20260927130100` applied to the linked project; `supabase db lint --linked` returned no schema errors. |
| Live owner-safe fixture | Passed | 2026-09-27: all 35 requests in the full-pipeline collection passed. The fictional case was created, extracted, analyzed, archived, restored, and archived again. Request 28 returned all nine normalized citations, including the case-summary row with populated `analysis_run_id`; request 29 recorded lifecycle activity. |

## Stage 3.4 verification record — verified

| Workflow | Result | Evidence |
| --- | --- | --- |
| Public API and mocked pipeline suite | Passed | 2026-09-27: start/poll routes, blank context, no-evidence/configuration failures, reruns, active-run conflict, safe failure, and output persistence tests pass. |
| Live public Groq/Postman flow | Passed | 2026-09-27: `POST /v1/cases/{caseId}/analysis` returned queued `202`; polling reached completed with `has_completed_outputs: true` and no public context/prompt leakage. |

## Setup

- [ ] GitHub repository contains current documentation and implementation branch.
- [ ] Supabase Auth email/password flow works.
- [ ] Supabase Storage bucket is private.
- [ ] Railway API health endpoint returns success.
- [ ] The Railway frontend build uses the deployed Railway API URL ending in `/v1`.
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
- [ ] Stage 4: manual task creation works, including a source label and no citation.
- [ ] Stage 4: fields and parties can be confirmed, edited, or rejected while retaining the original AI suggestion and citations.
- [ ] Stage 4: valid task transitions work; terminal statuses and invalid transitions return `422`.
- [ ] Stage 4: dashboard counts proposed and approved AI/manual tasks only.
- [ ] Stage 4: User B cannot read or mutate User A’s review records or manual tasks.
- [ ] Approve, Reject, and Done actions persist and appear in activity history.
- [x] Evidence chat answer displays a valid citation.
- [x] General chat answer displays the required general-guidance label.
- [x] Chat history remains after page refresh.

## Stage 5 — Evidence-grounded case chat

- [x] Apply `20260927180000_stage5_case_chat.sql` to the linked project and pass schema lint.
- [x] Add deterministic ready-passage retrieval, bounded history/evidence, typed Groq output, and normalized citation validation.
- [x] Add atomic pair/citation/activity persistence and safe no-partial-save failures.
- [x] Expose FastAPI history/send routes and connect the browser Chat view without direct Supabase access.
- [x] Add focused backend/frontend automated tests and the Stage 5 Postman collection.
- [x] Run a live Groq evidence answer and inspect its resolved citation.
- [x] Run a live general-guidance answer and verify its label and absence of citations.
- [x] Reload the browser and confirm both exchanges persist; automated UI coverage confirms failed-send draft restoration.
- [x] Verify User B and an archived case receive `404` and cannot use the persistence RPC.

## Presentation readiness

- [ ] The fictional property-dispute packet is uploaded and analyzed in the demo account.
- [ ] Browser has the deployed application open and signed in.
- [ ] A fallback screen recording or screenshots are prepared.
- [ ] Demo script was rehearsed once without backend errors.
- [ ] Project readiness is marked Ready in `project-status.md`.

## Stage 3.5 persisted review reads — verified

- [x] Run the completed active-case review workflow: overview, timeline, issues, tasks, and activity returned from FastAPI.
- [x] Verify overview’s summary, document summaries, issues, proposed task, counts, separated lawyer context, and source-linked citations.
- [x] Verify chronological payment and key-handover timeline events.
- [x] Verify empty state, `401`, and cross-user/archived `404` behavior for all five routes.

## Stage 3.6 frontend integration — verified

- [x] Type-check Stage 3 frontend API contracts and workspace integration.
- [x] Add and exercise the dedicated Upload route, private document readers, responsive document layout, and analysis completion redirect during local browser QA.
- [x] Install Vitest/Testing Library and run the citation-route test.
- [x] Run one clean complete property-dispute journey in a browser.
- [x] Verify citation navigation for TXT/DOCX and the PDF Evidence focus fallback.
- [x] Verify a failed analysis rerun preserves existing review output.
- [x] Verify review-route empty state, `401`, and cross-user/archived `404` behavior.
- [x] Verify dashboard task and issue counts use latest completed output only.

## Stage 4 — Lawyer review and task workflow

- [x] Apply `20260927170000_stage4_lawyer_review_workflow.sql` through the linked Supabase project and run schema lint.
- [x] Run `CasePilot-AI-Stage-4-Review-Workflow.postman_collection.json` against an owned case with completed analysis.
- [x] Run two-user RLS verification for fields, parties, manual tasks, workflow RPCs, and activity.
- [x] Complete browser QA for review actions, task grouping, manual task edits, activity refresh, and dashboard metrics.
