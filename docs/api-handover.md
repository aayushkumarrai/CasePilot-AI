# API Handover — Stage 1

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

These are the only endpoints available in Stage 1 and are the routes included in the Postman collection at `postman/CasePilot-AI-Stage-1.postman_collection.json`.

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

## Planned endpoints — do not integrate yet

The following routes are part of later document-processing and AI stages. They are retained here as roadmap references only; calling them now returns `404`.

| Method and path | Planned use |
| --- | --- |
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

## Stage 1 frontend behavior

- Show API errors near the action that failed and retain unsaved form values.
- Regenerate TypeScript types from FastAPI `/openapi.json` whenever API schemas change.
