# API Handover — Stages 1 and 2

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

Stage 1 is covered by `postman/CasePilot-AI-Stage-1.postman_collection.json`. Stage 2 document intake is covered by `postman/CasePilot-AI-Stage-2.postman_collection.json`.

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
| `GET /documents/{documentId}` | Returns document metadata, DOCX/TXT passages, or a short-lived PDF read URL. |
| `POST /documents/{documentId}/retry` | Reprocesses a failed supported document. Returns `202`. |

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

`GET /documents/{documentId}` returns `passages` only for ready DOCX/TXT files. A ready PDF instead includes `read_url`, valid for one hour. All passages have stable UUIDs, labels, sequence numbers, and (for PDFs) page numbers. Failed documents have a safe `error_message`; only a `failed` supported document may be retried.

The API returns `401` for a missing/invalid token, `404` for an absent, unowned, or archived parent case/document, `409` for the case document limit or invalid retry state, `422` for invalid metadata/path/size, and `503` when Supabase Storage is unavailable.

## Planned endpoints — do not integrate yet

### Stage 3.1 internal foundation

Stage 3.1 has applied the run-scoped analysis schema, owner RLS, lawyer-context snapshot, normalized citation storage, and internal Supabase lifecycle RPCs. It intentionally adds **no FastAPI route**; `POST /cases/{caseId}/analysis` and `GET /cases/{caseId}/analysis` remain unavailable until Substage 3.4. The frontend must not call Supabase RPCs directly.

Maintainers can verify the lifecycle with `postman/CasePilot-AI-Stage-3.1-Internal.postman_collection.json` using a case that has a ready document and a valid `passage_uuid` from Stage 2 document detail.

### Stage 3.2 internal Groq client

Stage 3.2 adds the server-only Groq client using `openai/gpt-oss-20b`. It has no public API route and does not persist output. It accepts prepared evidence/context text and returns validated typed output only to the later analysis orchestrator. Frontend code must never call Groq or receive `GROQ_API_KEY`.

Stage 3.3 adds the internal evidence assembler and citation gate. It loads only an owned active case’s ready passages, creates deterministic provider text, rejects evidence over 180,000 characters, and filters provider output so every retained factual item has passage-grounded support. The fixed case-summary citation target is internal (`target_type: case_summary`, `target_ref: case_summary`) and persists against the analysis run. It adds no HTTP endpoint; frontend behavior remains unchanged until Stage 3.4.

The following routes are part of later document-processing and AI stages. They are retained here as roadmap references only; calling them now returns `404`.

| Method and path | Planned use |
| --- | --- |
| `POST /cases/{caseId}/analysis` | Start analysis; returns `202`. |
| `GET /cases/{caseId}/analysis` | Poll every 2–3 seconds while processing. |
| `GET /cases/{caseId}/overview` | Summary, confirmed fields, pending fields, parties, and counters. |
| `PATCH /cases/{caseId}/fields/{fieldId}` | Confirm, reject, or edit an extracted field. |
| `GET /cases/{caseId}/timeline` | Timeline events with citations. |
| `GET /cases/{caseId}/issues` | Conflict/gap findings with citations. |
| `GET/POST /cases/{caseId}/tasks` | List or create task. |
| `PATCH /tasks/{taskId}` | Edit text or set task state. |
| `GET/POST /cases/{caseId}/chat` | Load/save case chat messages. |
| `GET /cases/{caseId}/activity` | Case audit history. |

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

## Planned analysis context — Stage 3

The planned analysis request accepts an optional lawyer-provided context field. It is unavailable until Stage 3 and currently returns `404` with the rest of the planned analysis routes.

```json
POST /cases/{caseId}/analysis
{
  "lawyer_context": "The buyer says possession was never handed over. Focus on payment and key-handover records."
}
```

- The value is optional, trimmed, and limited to 4,000 characters.
- An empty value is stored as `null`.
- The API saves the current case value and snapshots it on the analysis run.
- It is sent to AI as a labeled lawyer assertion, never as uploaded evidence or a citation source.

## Stage 1 frontend behavior

- Show API errors near the action that failed and retain unsaved form values.
- Regenerate TypeScript types from FastAPI `/openapi.json` whenever API schemas change.
