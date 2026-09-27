# API Handover — Stages 1 Through 3.6

Base URL: `https://<railway-service>/v1` in production and `http://localhost:8000/v1` locally.

## Authentication

Every request except `GET /health` and `GET /health/ready` uses `Authorization: Bearer <supabase-access-token>`. A missing or invalid token returns `401`. A valid token without ownership of the case returns `404` to avoid revealing the case exists.

## Shared conventions

- IDs are UUID strings.
- Errors use `{ "detail": "Human-readable message" }`.
- Case status: `draft`, `processing`, `review`, `ready`.
- Document status: `uploaded`, `processing`, `ready`, `failed`, `unsupported`.
- Field status: `pending`, `confirmed`, `rejected`.
- Task status: `proposed`, `approved`, `done`, `rejected`.
- Citation shape:

```json
{
  "document_id": "uuid",
  "passage_id": "uuid",
  "document_name": "seller-notice.pdf",
  "page_number": 2,
  "passage_label": "Page 2, Passage 3",
  "quote": "Possession and keys were handed over..."
}
```

## Implemented endpoints

The ordered maintainer verification path for all implemented work through Stage 3.3 is `postman/CasePilot-AI-Full-Pipeline-Stage-3.3.postman_collection.json`. The focused Stage 1 and Stage 2 collections remain available as references.

| Method and path | Use |
| --- | --- |
| `GET /health` | Liveness check; does not call Supabase. |
| `GET /health/ready` | Readiness check; verifies Supabase configuration and connectivity. |
| `GET /me` | Current authenticated user and profile. |
| `GET /dashboard` | Dashboard cards, recent cases, metrics, and activity. |
| `GET /cases` | Case list. |
| `POST /cases` | Create `{ "case_id": "PROP-001", "case_name": "Rao v Mehta" }`. Returns `201`. |
| `GET /cases/{caseId}` | Case header and status. |
| `PATCH /cases/{caseId}` | Change Case ID and/or case name. |
| `DELETE /cases/{caseId}` | Soft-delete a case. Returns `204`. |
| `POST /cases/{caseId}/restore` | Restore a soft-deleted case. |
| `POST /cases/{caseId}/documents/upload-url` | Creates a one-hour signed URL for one supported private upload. |
| `POST /cases/{caseId}/documents` | Registers a completed upload or records an unsupported file. Returns `201`. |
| `GET /cases/{caseId}/documents` | Lists documents newest first. |
| `GET /documents/{documentId}` | Returns document metadata, stable DOCX/TXT passages, and a short-lived private read URL for ready PDF or DOCX files. |
| `POST /documents/{documentId}/retry` | Reprocesses a failed supported document. Returns `202`. |
| `POST /cases/{caseId}/analysis` | Starts explicit Groq-backed analysis for a ready owned case. Returns `202`. |
| `GET /cases/{caseId}/analysis` | Returns safe latest-run polling status and completed-output availability. |
| `GET /cases/{caseId}/overview` | Latest completed analysis overview, current lawyer context, grouped fields, parties, cited summaries, issues, proposed tasks, and counts. |
| `GET /cases/{caseId}/timeline` | Latest completed run timeline, chronologically sorted with citations. |
| `GET /cases/{caseId}/issues` | Latest completed conflicts and gaps with citations. |
| `GET /cases/{caseId}/tasks` | Latest completed AI tasks plus case-scoped manual tasks, with source, workflow status, and citations for AI tasks only. |
| `GET /cases/{caseId}/activity` | Latest 50 safe activity events for the case. |

## Stage 2 document upload flow

The frontend must use this sequence for every supported file:

1. Call `POST /cases/{caseId}/documents/upload-url` with `file_name`, canonical `content_type`, and `size_bytes`.
2. Upload the raw file directly to the returned `upload_url`; do not send the file through FastAPI.
3. Call `POST /cases/{caseId}/documents` with the same metadata and returned `storage_path`.
4. Poll `GET /cases/{caseId}/documents` while any document has `uploaded` or `processing` status.

Supported type pairs are PDF/`application/pdf`, DOCX/`application/vnd.openxmlformats-officedocument.wordprocessingml.document`, and TXT/`text/plain`. Each file is limited to 50 MB and each case has a maximum of 50 registered documents. A non-supported file is registered through step 3 with `storage_path: null`; it remains visible with `status: "unsupported"`.

```json
POST /cases/{caseId}/documents/upload-url
{
  "file_name": "buyer-notice.pdf",
  "content_type": "application/pdf",
  "size_bytes": 184231
}
```

```json
{
  "storage_path": "<user-id>/<case-id>/<generated-id>-buyer-notice.pdf",
  "upload_url": "https://...",
  "expires_in_seconds": 3600
}
```

After direct upload:

```json
POST /cases/{caseId}/documents
{
  "file_name": "buyer-notice.pdf",
  "content_type": "application/pdf",
  "size_bytes": 184231,
  "storage_path": "<returned-storage-path>"
}
```

`GET /documents/{documentId}` returns stable `passages` for ready DOCX/TXT files. Ready PDFs and DOCX files also include a one-hour `read_url` for the in-app private preview; TXT remains passage-based. All passages have stable UUIDs, labels, sequence numbers, and (for PDFs) page numbers. Failed documents have a safe `error_message`; only a `failed` supported document may be retried.

The API returns `401` for a missing/invalid token, `404` for an absent, unowned, or archived parent case/document, `409` for the case document limit or invalid retry state, `422` for invalid metadata/path/size, and `503` when Supabase Storage is unavailable.

## Stage 3.4 public analysis command

`POST /cases/{caseId}/analysis` is now available. It accepts the optional lawyer context only when the lawyer explicitly starts analysis:

```json
POST /cases/{caseId}/analysis
{
  "lawyer_context": "Focus on payment and possession records."
}
```

Whitespace-only context becomes `null`; input longer than 4,000 characters returns `422`. The API requires an owned active case with at least one ready document. It returns `202` with safe lifecycle metadata and does not expose prompt text, lawyer context, provider output, or provider credentials.

```json
{
  "id": "uuid",
  "status": "queued",
  "started_at": null,
  "completed_at": null,
  "error_message": null
}
```

`GET /cases/{caseId}/analysis` is the polling route. Poll every 2–3 seconds only while `run.status` is `queued` or `processing`; stop on `completed` or `failed`. Before any run, it returns a `200` empty state. A failed rerun retains `has_completed_outputs: true` when an earlier completed run exists.

```json
{
  "run": null,
  "has_completed_outputs": false
}
```

The backend runs Groq, evidence assembly, citation validation, and persistence in an in-process background task. Groq is server-only. The frontend must call FastAPI and must not call Supabase lifecycle RPCs directly.

### Internal analysis foundation

Stages 3.1–3.3 provide run-scoped output storage, immutable context snapshots, the Groq client, deterministic evidence assembly, and citation validation. The existing `postman/CasePilot-AI-Full-Pipeline-Stage-3.3.postman_collection.json` remains the internal persistence verification record. Use `postman/CasePilot-AI-Stage-3.4-Public-Analysis.postman_collection.json` to verify the new public command and polling routes.

## Stage 3.5 persisted review reads

All five review routes validate active ownership first, then select only the latest `completed` analysis run. A queued, processing, or failed rerun never replaces the completed workspace output. Before the first completed run, overview returns `analysis_run: null`, a null `case_summary`, empty collections and zero counts; timeline, issues, tasks, and activity return `[]`.

Each sourced item includes citations resolved to the document name, stable passage ID and label, optional page number, and stored quote. `lawyer_context` is the current case value and is displayed separately: it has no citations and is not evidence. The overview includes document summaries for the Documents page. Stage 3.5 has no review/task mutations.

The Postman collection is `postman/CasePilot-AI-Stage-3.5-Review-Reads.postman_collection.json`; use an active `case_uuid` with a completed analysis run.

## Stage 5 evidence-grounded chat

| Method and path | Use |
| --- | --- |
| `GET /cases/{caseId}/chat` | Return the latest 100 persisted messages in chronological order with resolved citations. |
| `POST /cases/{caseId}/chat` | Send `{ "message": "..." }`, wait for Groq, validate grounding, and return the atomically persisted pair with `201`. |

Messages are trimmed and limited to 2,000 characters. Evidence answers include one to five document citations. General guidance is citation-free and begins with `General guidance — not based on case documents.` Authentication failures return `401`; absent, archived, or unowned cases return `404`; invalid input returns `422`; safe provider, output-validation, grounding, or persistence failures return `503` and save no partial exchange.

## Stage 1 request examples

### Update a case

```json
PATCH /cases/{caseId}
{ "case_id": "PROP-002", "case_name": "Rao v Mehta Updated" }
```

Both fields are optional, but the request must include at least one. A Case ID conflict with another active case owned by the same lawyer returns `409`.

### Create a case

```json
POST /cases
{ "case_id": "PROP-001", "case_name": "Rao v Mehta" }
```

The response is `201` with the internal UUID in `id`. Use that UUID as `{caseId}` in all case routes.

## Lawyer-provided context — Stage 3.4

The public analysis command accepts optional lawyer context. It is trimmed, limited to 4,000 characters, saved on the case, and snapshotted on the analysis run. It reaches Groq only as a labeled lawyer assertion, never as uploaded evidence or a citation source.

## Stage 1 frontend behavior

- Show API errors near the action that failed and retain unsaved form values.
- Regenerate TypeScript types from FastAPI `/openapi.json` whenever API schemas change.

## Stage 3.6 dashboard metrics

`GET /dashboard` counts `pending_tasks` as proposed and approved AI tasks from the latest completed run plus proposed and approved manual tasks. `unresolved_issues` remains findings from the latest completed analysis run. Historic runs and queued, processing, or failed reruns do not affect either metric.

## Dedicated upload and document previews

New cases navigate to `/cases/{caseId}/upload`. That frontend route owns document upload, lawyer-provided context, and explicit analysis start. `GET /documents/{documentId}` now returns a short-lived `read_url` for ready PDFs and DOCX files; the browser uses it only for private in-app preview. TXT remains passage-based for stable evidence navigation.

## Stage 3.6 browser integration status

The current frontend is integrated with every implemented Stage 3 route. Case creation routes to `/cases/{caseId}/upload`; that route is the only place that uploads evidence, edits lawyer-provided context, and starts analysis. Completion routes to Overview. Documents is a reading-only evidence destination with PDF.js PDF preview, sanitized Mammoth DOCX preview, and stable TXT/DOCX passage navigation.

Stage 4 adds field/party review actions and task workflow controls. The frontend preserves the original AI suggestion and its citations next to any lawyer-reviewed value; only manual task wording is editable.

## Stage 4 lawyer review and task workflow

Stage 4 keeps analysis outputs and citations immutable. Lawyer decisions are separate review values; activity events contain record IDs and action metadata only. All workflow routes require ownership of an active case. Missing authentication returns `401`; absent, archived, or unowned records return `404`; invalid review input or status transitions return `422`.

| Method and path | Use |
| --- | --- |
| `PATCH /cases/{caseId}/fields/{fieldId}` | Confirm, edit, or reject a latest-run AI field. An edit requires `value`. |
| `PATCH /cases/{caseId}/parties/{partyId}` | Confirm, edit, or reject a latest-run AI party. An edit requires `name` and/or `role`. |
| `POST /cases/{caseId}/tasks` | Create an owner-scoped manual task in `proposed` state. Returns `201`. |
| `PATCH /tasks/{taskId}` | Transition any task, or edit title/description for an open manual task only. |

```json
PATCH /cases/{caseId}/fields/{fieldId}
{ "action": "edit", "value": "INR 475000" }
```

The response includes `suggested_value`, nullable `reviewed_value`, and effective `value`. Party responses similarly expose suggested and reviewed name/role. A rejected field or party is terminal.

```json
POST /cases/{caseId}/tasks
{ "title": "Obtain bank statement", "description": "Request the buyer's statement for 10 June 2026." }
```

Task status flow is `proposed → approved`, `proposed → rejected`, and `approved → done`. Done and rejected tasks are terminal. AI task wording is immutable; manual task wording may be edited while proposed or approved. `GET /cases/{caseId}/tasks` returns current latest-run AI tasks plus all manual tasks, with `source: "ai" | "manual"`; only AI tasks have citations. `GET /dashboard` counts proposed and approved tasks from both sources as open work.

Use `postman/CasePilot-AI-Stage-4-Review-Workflow.postman_collection.json` after importing `postman/CasePilot-AI-Local.postman_environment.json`.
