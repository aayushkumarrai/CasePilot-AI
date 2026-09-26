# Frontend Tasks — Stage 2 Document Intake

## Goal

Connect the existing Documents screen to the verified Stage 2 API so a signed-in lawyer can securely upload, inspect, retry, and understand case documents. This task does not include AI analysis, case context persistence, summaries, timeline, tasks, or chat.

## Prerequisites

1. Pull the Stage 2 backend update and run the FastAPI server at `http://localhost:8000`.
2. Confirm `NEXT_PUBLIC_API_BASE_URL` ends with `/v1` and Supabase sign-in returns a session.
3. Read [API Handover](api-handover.md), [Frontend Handover](frontend-handover.md), and the Stage 2 Postman collection.
4. Keep the existing shared API client responsible for retrieving the fresh Supabase access token before every API request.

## Task group 1 — Types and document API client

Create typed request/response helpers in `apps/web/lib/` using the FastAPI OpenAPI contract.

1. Add types for `DocumentStatus`, `Document`, `DocumentPassage`, `DocumentDetail`, and signed-upload response.
2. Add helpers for:
   - `POST /cases/:caseId/documents/upload-url`
   - `POST /cases/:caseId/documents`
   - `GET /cases/:caseId/documents`
   - `GET /documents/:documentId`
   - `POST /documents/:documentId/retry`
3. Use the existing token-aware API client for every FastAPI call.
4. Add a separate direct `PUT` helper for `upload_url`. Send the raw `File` body and its MIME type. Do not attach the Supabase access token or API base URL to this request.
5. Preserve the standard error handling: `401` signs out, `404` shows the normal case/document not-found state, `409` shows a limit or retry-state message, `422` shows input feedback, and `503` offers retry.

### Completion check

- No browser code contains a Storage secret or service-role key.
- The `upload_url` is used only for one direct upload and is never stored in browser persistence or app data.

## Task group 2 — Upload controls and validation

Build a multi-file picker and optional drop zone in the Documents route.

1. Allow PDF, DOCX, TXT, and any unsupported file the user selects.
2. Before upload, block a batch that would exceed 50 selected/registered documents or any file over 50 MB. Show which file failed validation.
3. For supported files, require these exact type pairs:

| Extension | Content type |
| --- | --- |
| `.pdf` | `application/pdf` |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| `.txt` | `text/plain` |

4. For each supported file, use this exact sequence:
   1. Request an upload URL with `file_name`, `content_type`, and `size_bytes`.
   2. Upload the raw file to returned `upload_url` with `PUT`.
   3. Register it with the returned `storage_path` and the original metadata.
5. For unsupported files, skip the signed upload and register metadata with `storage_path: null`. The API creates a visible `unsupported` list item.
6. Handle files independently. If one file fails, keep processing the others and show the failed file’s error.
7. Disable duplicate submission for a file while it is in the local upload queue.

### Completion check

- A valid TXT/PDF/DOCX can be uploaded without routing its bytes through FastAPI.
- JPG appears as unsupported instead of silently disappearing.
- An upload failure leaves the rest of the batch and the screen usable.

## Task group 3 — Document list and background status

1. Fetch `GET /cases/:caseId/documents` on entering the Documents route and after registration completes.
2. Render name, extension/type, file size, created time, status, and safe `error_message`.
3. Show clear status labels for `uploaded`, `processing`, `ready`, `failed`, and `unsupported`.
4. Poll every 2–3 seconds only if at least one record is `uploaded` or `processing`.
5. Stop polling once all records are terminal: `ready`, `failed`, or `unsupported`.
6. Preserve the visible list if a refresh fails and show a retryable refresh error.
7. Render a Retry button only for `failed` documents. On click, call `POST /documents/:documentId/retry`, update the returned item to `processing`, and resume polling.

### Completion check

- A newly registered document visibly transitions from `uploaded` to `processing` to `ready`.
- A failed document can be retried; ready and unsupported documents have no retry action.

## Task group 4 — Document reader

1. Selecting a list row fetches `GET /documents/:documentId`.
2. For a ready PDF, render `read_url` in the existing PDF viewer/iframe. Treat the URL as temporary; refetch detail if it expires or fails.
3. For a ready DOCX/TXT, render `passages` in order. Each passage must show its label, optional PDF page number, and content.
4. Preserve the selected document during polling unless it is deleted by a future API stage.
5. Give reader loading, empty, failed, and unsupported states their own clear UI.
6. Reserve the right-side AI summary panel as an inactive “Available after analysis” state. Do not fabricate a summary from extracted text.

### Completion check

- A ready PDF opens without exposing a permanent object URL.
- A ready DOCX/TXT shows stable passage labels that later citation links can target.

## Task group 5 — Lawyer-provided context placeholder

1. Place a 4,000-character textarea beside the upload controls.
2. Label it **Lawyer-provided context (optional)**.
3. Show: “Add relevant background, questions, or facts provided by the lawyer. This is not document evidence.”
4. Preserve its typed local value during upload failures and route-level rerenders if practical.
5. Do **not** call any API with this value in Stage 2. Do not show it in the document list or reader as document evidence.

## Manual verification sequence

1. Sign in as a regular test user and open an owned case.
2. Upload a TXT containing two blank-line-separated paragraphs; confirm two numbered passages after status reaches Ready.
3. Upload a PDF and confirm the embedded signed reader works.
4. Upload a DOCX and confirm paragraph labels render.
5. Register a JPG and confirm Unsupported status and explanation.
6. Use an intentionally unreadable supported file, confirm Failed status, and use Retry.
7. Confirm polling stops after all documents are terminal.
8. Sign in as another user and confirm the first user’s case/document URLs render the normal not-found state.

Record successful checks in [Project Status](project-status.md). Stage 2 is already backend-verified; mark frontend document integration Verified only after this sequence passes against the live API.
