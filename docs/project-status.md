# Project Status

**Last updated:** 2026-09-26  
**Current phase:** Stage 3 — Analysis and Review Outputs
**Demo readiness:** At Risk — Stage 1–2 frontend implementation is ready for live integration review; AI analysis, later-stage APIs, deployment, and end-to-end verification remain.

## Status definitions

| Status | Meaning |
| --- | --- |
| Not Started | No implementation or verification begun. |
| In Progress | Work is actively underway. |
| Blocked | Cannot proceed without a dependency or decision. |
| Ready for Review | Implementation is complete and needs integration/QA. |
| Verified | Automated and manual checks passed; evidence is recorded. |

## Delivery board

| Work item | Owner | Status | Dependency / next action | Verified by / date |
| --- | --- | --- | --- | --- |
| Product, architecture, frontend and API handover docs | Sharad | Verified | API contract frozen for Stage 1 | Team / 2026-09-26 |
| Project status, test plan, checklist, demo script | Sharad | Verified | Stage 1 evidence recorded; later-stage checks remain open | Team / 2026-09-26 |
| Stage-by-stage implementation plan | Sharad | Verified | Stages aligned to the Next.js/FastAPI monorepo | Team / 2026-09-26 |
| Frontend and FastAPI foundation | Sharad | Verified | Directory structure, health check, environment examples, and local setup guide added | 2026-09-26 |
| Supabase Stage 1 schema, profile trigger, and RLS | Sharad | Verified | Migration applied, remote lint passed, and two-user RLS verification returned `404` for a non-owner | `20260926092442`, lint, two-user Postman / 2026-09-26 |
| FastAPI Stage 1 identity, cases, and dashboard APIs | Sharad | Verified | Real Postman lifecycle and two-user RLS verification passed: create, duplicate conflict, list, get, update, validation, archive, restore, dashboard, missing-token rejection, and cross-user `404`. | `pytest`, live readiness, Postman lifecycle, two-user RLS / 2026-09-26 |
| Backend Stage 1 handoff | Sharad | Verified | OpenAPI, Postman collection, environment template, frontend auth/schema handover, and deployment guidance are ready for integration. | `docs/api-handover.md`, `postman/` / 2026-09-26 |
| Postman API and security verification package | Sharad | Verified | Collection exercised against local FastAPI and real Supabase, including missing-token `401` and cross-user `404` | `postman/`, `docs/postman-testing.md` / 2026-09-26 |
| Dashboard and case shell | Aayush | Ready for Review | Replaced mock dashboard and case lifecycle UI with token-authenticated Stage 1 API integration, protected routes, archive/restore, and error/empty/loading states. Requires live Supabase/FastAPI manual verification. | `pnpm --dir apps/web build` / 2026-09-26 |
| Auth, case creation, uploads, document reader | Akshata | Ready for Review | Implemented session handling, sign-out/401 behavior, case creation, signed direct uploads, document polling/retry, temporary PDF reading, and DOCX/TXT passage reader. Requires live Supabase/FastAPI manual verification. | `pnpm --dir apps/web build`; API `pytest` 14 passed / 2026-09-26 |
| Overview, timeline, issues, tasks, AI Chat | Aayush | Blocked | Stage 3–5 FastAPI endpoints and frozen request/response schemas are absent; current API handover declares these routes planned only. | Backend route audit / 2026-09-26 |
| Fictional document packet | Team | Not Started | Write six fictional documents | — |
| Integration and automated tests | Team | Not Started | Backend and frontend feature completion | — |
| Backend Stage 2 document intake | Sharad | Verified | Private bucket, owner-only RLS, signed upload/read flow, registration, background extraction, retry, and stable passages verified for PDF, DOCX, TXT, unsupported files, failure/retry, and two-user isolation. | `pytest` 14 passed; migration `20260926113000`; live Postman verification / 2026-09-26 |
| Lawyer-provided context | Ready for Review (Stage 2 UI) | Local 4,000-character non-evidence textarea is implemented beside uploads. Persistence and analysis submission remain blocked on the Stage 3 API. | `pnpm --dir apps/web build` / 2026-09-26 |
| Demo rehearsal and final checklist | Team | Not Started | Verified end-to-end flow | — |

## Environment tracker

| Service | Owner | Status | Notes |
| --- | --- | --- | --- |
| GitHub repository | Team | Verified | Canonical remote: `aayushkumarrai/CasePilot-AI`. |
| Supabase project | Sharad | Verified | Repository linked to `gojazidrlvbumopyjfbl`. |
| Supabase Stage 1 schema and RLS | Sharad | Verified | Migration `20260926092442`, remote schema lint, and two-user owner isolation pass. |
| Supabase Stage 2 Storage and schema | Sharad | Verified | Migration `20260926113000` applied: private `case-documents` bucket, documents/passages, RLS, and atomic activity RPCs. Live owner-isolation test passed. |
| NVIDIA API | Sharad | Not Started | Validate account access, selected model, structured-output quality. |
| Railway | Sharad | Not Started | Deploy FastAPI and configure secrets. |
| Vercel | Aayush / Akshata | Not Started | Deploy Next.js and set API/Supabase variables. |

## Current blockers

| Blocker | Owner | Impact | Resolution |
| --- | --- | --- | --- |
| No fictional source documents | Team | Blocks realistic end-to-end analysis and rehearsal | Create the six-document property dispute packet. |
| Stage 3–5 API contract and implementation are absent | Sharad | Blocks functional frontend analysis, review workspace, task lifecycle, citation navigation, and chat; the documented routes currently return `404`. | Implement and freeze the Stage 3–5 OpenAPI schemas/endpoints, then provide a configured integration environment. |
| No local frontend environment or running API | Team | Blocks documented manual frontend verification and every `Verified` status update. | Create `apps/web/.env.local`, run the FastAPI service, and use two test users against the configured Supabase project. |

## Update rule

Update this file whenever a work item changes status, an endpoint changes, a new blocker appears, or a verification test passes. Add a date and a link/screenshot/test result when marking an item Verified.
