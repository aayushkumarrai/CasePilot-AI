# API Handover

Base URL: `https://<railway-service>/v1` in production and `http://localhost:8000/v1` locally.

## Authentication

Every request except health uses `Authorization: Bearer <supabase-access-token>`. A missing or invalid token returns `401`. A valid token without ownership of the case returns `404` to avoid revealing the case exists.

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

## Endpoint groups

| Method and path | Use |
| --- | --- |
| `GET /dashboard` | Dashboard cards, recent cases, metrics, and activity. |
| `GET /cases` | Case list. |
| `POST /cases` | Create `{ "case_id": "PROP-001", "case_name": "Rao v Mehta" }`. Returns `201`. |
| `GET /cases/{caseId}` | Case header and status. |
| `POST /cases/{caseId}/documents/upload-url` | Request signed upload URL before direct browser upload. |
| `POST /cases/{caseId}/documents` | Register completed upload. |
| `GET /cases/{caseId}/documents` | Document list and statuses. |
| `GET /documents/{documentId}` | Selected document details, summary, and reader metadata. |
| `POST /documents/{documentId}/retry` | Retry a failed document. |
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

## Key request examples

### Request upload URL

```json
POST /cases/{caseId}/documents/upload-url
{
  "file_name": "seller-notice.pdf",
  "content_type": "application/pdf",
  "size_bytes": 280000
}
```

The response provides `storage_path`, temporary `upload_url`, and `expires_in_seconds`. Upload the raw file directly to `upload_url`, then call document registration.

### Register upload

```json
POST /cases/{caseId}/documents
{
  "file_name": "seller-notice.pdf",
  "content_type": "application/pdf",
  "size_bytes": 280000,
  "storage_path": "user-id/case-id/uuid-seller-notice.pdf"
}
```

### Review an extracted field

```json
PATCH /cases/{caseId}/fields/{fieldId}
{ "status": "confirmed", "value": "Ravi Rao" }
```

### Update task state

```json
PATCH /tasks/{taskId}
{ "status": "approved" }
```

## Frontend behavior

- Disable Analyze Case when no document is registered.
- Show processing status and poll only while a run is active.
- Show a failed or unsupported document inside the list; do not hide it.
- Citation buttons open the referenced document and passage/page in Documents.
- Show API errors near the action that failed and retain unsaved form values.
- Regenerate TypeScript types from FastAPI `/openapi.json` whenever API schemas change.
