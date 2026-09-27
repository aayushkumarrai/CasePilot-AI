# Project Status

**Last updated:** 2026-09-27
**Current phase:** Stage 4 lawyer review and task workflow — Verified
**Demo readiness:** At Risk — Stages 1–4 are verified; deployment and final rehearsal remain.

## Status definitions

| Status | Meaning |
| --- | --- |
| Not Started | No implementation has begun. |
| In Progress | Work is active. |
| Ready for Review | Implementation is complete and needs final QA or integration evidence. |
| Verified | Automated and manual checks passed and evidence is recorded. |

## Delivery board

| Work item | Status | Current evidence / next action |
| --- | --- | --- |
| Stage 0 project setup and frozen base contract | Verified | Repository, local apps, Supabase project, environments, and health checks are established. |
| Stage 1 authentication, cases, dashboard, archive/restore | Verified | Real Supabase RLS and Postman lifecycle checks passed. |
| Stage 2 private document intake | Verified | PDF/DOCX/TXT signed upload, extraction, stable passages, retries, unsupported state, and owner isolation passed. |
| Stage 3.1 analysis schema and lifecycle | Verified | Immutable run-scoped output, context snapshots, citation storage, lifecycle RPCs, and RLS passed migration/lint/live checks. |
| Stage 3.2 Groq structured-output client | Verified | `openai/gpt-oss-20b` mocked tests and live smoke request passed. |
| Stage 3.3 evidence assembly and citation gate | Verified | Ready-only evidence, 180k limit, quote validation, filtered outputs, and case-summary citation persistence passed. |
| Stage 3.4 public analysis start and polling | Verified | FastAPI command/poll routes, BackgroundTasks lifecycle, safe failure behavior, and live Groq/Postman flow passed. |
| Stage 3.5 persisted review reads | Verified | Overview, timeline, issues, tasks, and activity passed completed-run, empty-state, authentication, ownership, and archived-case QA. |
| Stage 3.6 frontend integration | Verified | Dashboard/case flow, dedicated Upload route, signed uploads, analysis polling, review tabs, citation navigation, in-app PDF/DOCX/TXT readers, responsive layout, and the clean end-to-end browser rehearsal passed. |
| Stage 4 lawyer review and task mutations | Verified | Migration, schema lint, backend/frontend automated checks, live Postman workflow, and ownership QA passed. |
| Stage 5 case chat | Not Started | Implement scoped history, retrieval, evidence citations, and general-guidance labeling. |
| Stage 6 deployment and demo regression | Not Started | Deploy Railway/Vercel, set production CORS/env, run final property-dispute rehearsal. |

## Current application behavior

- New cases go to `/cases/{caseId}/upload`. This is the only page for upload, optional lawyer context, and **Analyze case**.
- The Upload page aligns its upload card, document list, and reader to the same workspace grid.
- Documents uses a responsive list, private in-app PDF preview, private DOCX preview, and stable extracted-passage navigation.
- Analysis sends context only on explicit start. Context remains a clearly labeled assertion, never document evidence.
- Overview, Timeline, Issues, and Activity remain latest-completed-run views. Stage 4 adds review actions for fields/parties and workflow controls for AI and manual tasks. A failed rerun leaves prior completed review output visible.
- Key parties and core fields are requested from Groq when clearly stated in evidence; a single grounded corrective pass is allowed if the first response omits them.

## Environment tracker

| Service | Status | Notes |
| --- | --- | --- |
| GitHub repository | Verified | Canonical remote: `aayushkumarrai/CasePilot-AI`. Current changes are prepared locally and await the maintainer’s commit/push. |
| Supabase | Verified | Auth, owner RLS, private Storage, documents, passages, analysis outputs, and lifecycle schema are applied. |
| Groq | Verified | Server-only `openai/gpt-oss-20b` smoke request passed. |
| Railway | Not Started | Deploy FastAPI and set Supabase/Groq/CORS values. |
| Vercel | Not Started | Deploy Next.js and set browser-safe Supabase/API variables. |

## Remaining blockers and next actions

| Item | Impact | Next action |
| --- | --- | --- |
| Final fictional property-dispute packet | Needed for a credible full rehearsal | Create/select the six fictional documents named in the demo script. |
| Deployment | Demo cannot be shown outside the local machine | Deploy Railway then Vercel; configure CORS and Supabase Auth redirects. |
| Stage 4 review workflow | Verified | Field/party decisions, AI/manual task workflow, safe activity, dashboard metrics, and two-user ownership checks passed. |

## Stage 3 QA evidence — 2026-09-27

The complete browser workflow passed: create a case, upload private evidence, wait for extraction, submit separate lawyer context, run Groq analysis, review overview/timeline/issues/tasks/activity, open citations in document readers, and confirm dashboard metrics. Empty, authentication, ownership, archived-case, and failed-rerun behavior passed the final QA record.

## Update rule

Update this file whenever a route, migration, UI flow, test result, or blocker changes. Mark a line Verified only after automated checks and the relevant manual workflow both pass.

## Stage 4 QA evidence — 2026-09-27

Stage 4 exit checks passed: the linked migration is applied and linted; field and party confirmation/edit/rejection preserve AI suggestions and citations; AI/manual task workflows enforce valid transitions; safe activity and dashboard open-task metrics refresh correctly; Postman and ownership checks passed.
