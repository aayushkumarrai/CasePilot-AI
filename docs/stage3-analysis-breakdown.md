# Stage 3 Breakdown — Analysis and Review Outputs

## Goal

Transform ready document passages into lawyer-reviewable, source-linked case outputs only after the lawyer explicitly selects **Analyze Case**. Stage 3 adds analysis runs, optional lawyer-provided context persistence, structured AI extraction, citation validation, and read-only review APIs.

## Stage 3 completion definition

Stage 3 is complete when an owner can analyze a case with one or more ready documents and receive a case summary, pending fields, parties, timeline events, conflicts/gaps, and proposed tasks. Every factual item must point to valid stored passage IDs. Lawyer-provided context remains visibly separate from document evidence.

## Guardrails that apply to every substage

- Analyze only active cases owned by the current Supabase user.
- Analyze only documents whose status is `ready`; failed and unsupported files never block usable evidence.
- Never call Groq from the browser. `GROQ_API_KEY` and model configuration live only in backend/Railway environment variables.
- Treat lawyer-provided context as a non-evidence assertion. It may guide prioritization and tasks, but cannot support a factual claim, citation, timeline event, payment assertion, or conflict resolution.
- Persist no AI citation unless its document, passage, page/label, and quote are validated against stored evidence.
- Preserve conflicts as competing accounts. Describe gaps only as “not found in uploaded material.”
- Do not alter prior completed results if a later analysis fails.

---

## Substage 3.1 — Schema, RLS, and analysis lifecycle

### Purpose

Create the data model and status flow before any AI request can run.

### Backend work

1. Create one Supabase migration with:
   - `cases.lawyer_context text null`, constrained to 4,000 characters after trimming.
   - `analysis_runs` with `id`, `case_id`, `status`, `lawyer_context_snapshot`, `error_message`, `started_at`, `completed_at`, `created_at`, and `updated_at`.
   - `case_fields` for extracted values and lawyer review state: `pending`, `confirmed`, `rejected`.
   - `timeline_events` for cited events and date confidence.
   - `findings` for `conflict` and `gap` records.
   - `tasks` for AI-proposed work in `proposed` state.
   - Citation storage using either a normalized citation table or JSONB validated citation arrays. Choose one approach and document it in the migration and API response types.
2. Add indexes for case-scoped reads, current analysis run lookup, and analysis-result retrieval.
3. Enable owner-based RLS on every new table through the parent case owner.
4. Add atomic security-invoker RPCs for:
   - starting an analysis run and storing the current context plus immutable snapshot;
   - recording a safe analysis-started activity event;
   - completing a run and persisting validated outputs;
   - failing a run with a safe error;
   - preventing overlapping active runs for the same case.
5. Define statuses:
   - Analysis: `queued`, `processing`, `completed`, `failed`.
   - Case after a run starts: `processing`; after success: `review`; a failed rerun leaves prior completed review data intact.

### Tests

- User B cannot read or mutate User A’s runs or outputs.
- A blank or whitespace context saves as `null`; more than 4,000 characters returns `422`.
- A second active run for the same case returns `409`.
- Starting analysis without ready documents returns `422`.
- A run snapshot remains unchanged after the current case context changes on a later run.

### Exit check

The migration is applied, RLS passes a two-user test, and a no-AI mocked run can move from `queued` to `completed` or `failed`.

---

## Substage 3.2 — Groq client and strict structured-output boundary

### Purpose

Establish a replaceable, server-only AI integration that produces parseable output without writing directly to the database.

### Backend work

1. Add `GROQ_API_KEY`, `GROQ_MODEL=openai/gpt-oss-20b`, and `GROQ_BASE_URL=https://api.groq.com/openai/v1` to `apps/api/.env.example`, Railway configuration, and deployment documentation. Never add any of them to frontend configuration.
2. Create `integrations/groq_client.py` using Groq’s OpenAI-compatible chat-completions API with JSON-object mode and Pydantic validation.
3. Set connection/read timeouts, one bounded retry for temporary provider failures, and structured error mapping.
4. Define Pydantic models for the complete AI response before making the request:
   - document summaries;
   - case fields;
   - key parties;
   - timeline events;
   - findings;
   - proposed tasks;
   - citations containing document ID, passage ID, and quote.
5. Use a JSON-only system prompt and reject invalid JSON, missing required fields, values outside allowed enums, and output above sensible size limits.
6. Build prompts with two explicit sections:
   - **Uploaded evidence**: ready documents and stable passages only.
   - **Lawyer-provided context — not document evidence**: optional context snapshot.
7. Include the evidence rules from [AI Pipeline](ai-pipeline.md) in the prompt and code-level response validation.

### Tests

- Client sends the expected model, messages, timeout, and JSON response-format request.
- Invalid JSON, provider timeout, and malformed structured response become safe analysis failures.
- The context text is sent in its separately labeled section.
- No model response is persisted in this substage.

### Exit check

A mocked Groq response is parsed into typed in-memory output; malformed output fails safely without database writes. The live synthetic smoke fixture also returns validated cited output before this substage is marked verified.

---

## Substage 3.3 — Evidence assembly and citation validation

### Purpose

Build the trust boundary between AI suggestions and persisted legal-workspace data.

### Backend work

1. Load only ready documents and their ordered passages for the owned active case.
2. Build deterministic Groq evidence text with document ID/name, passage ID, label, optional page number, and passage content. Documents are ordered by creation time and passages by sequence number.
3. Enforce `MAX_EVIDENCE_CHARS = 180_000`. If the complete payload exceeds the limit, fail safely without truncating or omitting passages. Batching is deferred.
4. Validate every model citation:
   - passage exists in the assembled owned-case evidence;
   - normalized non-empty quote is a substring of normalized stored passage text;
   - a document-summary citation belongs to that summary’s document;
   - citations target the fixed case-summary reference `case_summary` or a generated output reference.
5. Require a valid citation for the case summary and every factual output, including proposed tasks. Reject the complete result if the case summary is uncited; drop other uncited outputs and tasks whose cited finding was dropped.
6. Retain only citations attached to retained outputs. Never silently invent a replacement citation.
7. Validate context boundaries: context may guide the prompt, but never becomes a citation source or factual-output source.

### Database compatibility

Stage 3.3 adds two ordered Supabase migrations. The first adds `case_summary` to `citation_target_type`; the second adds `analysis_run_id` as the case-summary citation parent, updates checks, policies, indexes, and `complete_analysis_run_with_outputs`. Earlier output targets and the RPC signature remain unchanged.

### Tests

- Ready-only reads and deterministic document/passage ordering are preserved.
- The exact evidence limit passes; one character beyond it fails safely.
- Citation for another case, another document, missing passage, or wrong quote is rejected.
- Unicode and whitespace-normalized matching accepts a valid quote without weakening passage ownership.
- An uncited case summary rejects the result; uncited outputs and tasks depending on dropped findings are removed.
- Context-derived factual claims are rejected without supporting evidence.

### Exit check

Given mixed valid/invalid AI output, only correctly grounded review data reaches the persistence layer, including case-summary citations attached to the analysis run.

---

## Substage 3.4 — Analysis command, background processing, and polling

### Purpose

Expose one explicit analysis action and predictable client-visible lifecycle.

### APIs

| Endpoint | Behavior |
| --- | --- |
| `POST /v1/cases/{caseId}/analysis` | Validates case and ready documents, trims/saves optional context, creates queued run, schedules background work, returns `202`. |
| `GET /v1/cases/{caseId}/analysis` | Returns the latest run status, safe error, timestamps, and whether the case has completed review outputs. |

### Backend work

1. Add analysis module: router, schemas, repository, service, pipeline, and tests.
2. Validate request body `{ "lawyer_context": "optional text" }`; use `null` for blank input.
3. Start an atomic run with the snapshot and activity event.
4. Use `BackgroundTasks` for the hackathon implementation:
   - set run to `processing`;
   - assemble evidence;
   - call Groq;
   - validate and persist outputs;
   - mark run/case successful or failed.
5. Record activity actions such as `analysis_started`, `analysis_completed`, and `analysis_failed` without writing sensitive prompt content to activity details.
6. Return `409` for a duplicate active run and `422` where no ready document exists.
7. Keep the frontend polling period at 2–3 seconds while status is `queued` or `processing`; stop on `completed` or `failed`.

### Tests

- `POST` returns `202` for an owned active case with ready evidence.
- Missing token is `401`; unowned/archived case is `404`; no ready evidence is `422`; active run conflict is `409`.
- One failed document is ignored while ready documents are analyzed.
- A provider failure marks only the new run failed and leaves prior review data visible.
- Polling response does not leak context/prompt content or provider secrets.

### Exit check

A mocked end-to-end analysis starts, reaches a terminal status, and exposes the expected polling response.

---

## Substage 3.5 — Persisted overview and review-read APIs

### Purpose

Give the frontend stable read contracts without yet implementing lawyer mutations.

### APIs

| Endpoint | Behavior |
| --- | --- |
| `GET /v1/cases/{caseId}/overview` | Case summary, separate saved lawyer context, confirmed/pending fields, key parties, counts, latest issues, and pending tasks. |
| `GET /v1/cases/{caseId}/timeline` | Ordered, cited timeline events. |
| `GET /v1/cases/{caseId}/issues` | Cited conflicts and gaps. |
| `GET /v1/cases/{caseId}/tasks` | AI-proposed tasks in `proposed` state. |
| `GET /v1/cases/{caseId}/activity` | Case activity history including analysis lifecycle actions. |

### Backend work

1. Normalize every response through Pydantic schemas shared with generated OpenAPI types.
2. Return citation objects with document ID, passage ID, document name, passage label, optional page number, and short quote.
3. Return context in a dedicated `lawyer_context` field, never inside a citation or extracted field.
4. Return a clear empty state before first completed analysis.
5. Exclude archived and unowned cases with `404`.

### Tests

- Overview groups confirmed/pending fields separately and exposes context separately.
- Timeline/issues fields always contain valid persisted citations.
- No output from a failed run replaces outputs from the last completed run.
- User B receives `404` for every read route.

### Exit check

The frontend can render every Stage 3 review screen from read APIs without reading Supabase tables directly.

---

## Substage 3.6 — Frontend integration handoff and demo verification

### Frontend work package

1. Enable **Analyze Case** only when document list has at least one `ready` file and no analysis is active.
2. Send textarea value only on analysis start; retain it after a failed request.
3. Poll status while active and render queued, processing, completed, and failed states.
4. Render overview data with context visibly separated from sourced evidence.
5. Render citations as source links that open the correct document and stable passage.
6. Render conflicts without deciding the true account; show gaps as “not found in uploaded material.”
7. Render tasks as Proposed only. Task approve/reject/done actions belong to Stage 4.

### Demo verification

Use the fictional property-dispute packet to confirm:

1. A possession conflict cites seller notice and buyer email separately.
2. Payment evidence appears in the timeline with a passage citation.
3. Missing signed handover acknowledgment is framed as not found in uploaded material.
4. “Request the signed handover acknowledgment” appears as a proposed task.
5. The sample lawyer context appears separately and is never cited as evidence.

### Exit check

The full fictional packet produces reviewable, cited results in the UI, and every Stage 3 check is recorded in [Verification Checklist](verification-checklist.md).

## Recommended build order

1. Substage 3.1 — database and lifecycle.
2. Substage 3.2 — Groq client and typed output.
3. Substage 3.3 — evidence assembly and citation gate.
4. Substage 3.4 — analysis command and status polling.
5. Substage 3.5 — overview/read APIs.
6. Substage 3.6 — frontend integration and demo verification.

Do not begin a substage until its predecessor exit check passes. Update [Project Status](project-status.md) whenever a substage moves to In Progress, Ready for Review, or Verified.


## 3.5 — Persisted review read APIs

Implemented read-only FastAPI routes for overview, timeline, issues, tasks, and activity. They select the latest completed run only, resolve normalized citations to stored document passages, and return explicit empty states before a completion. Lawyer-provided context is returned separately from evidence. Field and task mutations remain Stage 4.


## Implementation status — 2026-09-27

Substages 3.1–3.6 are verified. The final QA covered the complete browser workflow, review-route security/empty states, source navigation, failed-rerun preservation, and dashboard metrics. The implemented browser flow is: Create Case → Upload → document readiness → Analyze Case → polling → Overview. It includes private PDF/DOCX preview, stable passage navigation for TXT/DOCX, separate lawyer context, evidence-linked review tabs, and dashboard counts derived from latest completed runs.

Stage 3 deliberately ends with read-only review data. Confirm/edit/reject fields, task changes, manual tasks, and chat do not exist until later stages.
