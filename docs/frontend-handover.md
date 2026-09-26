# Frontend Handover

## Visual direction

Use a professional legal workspace: calm neutral surfaces, high contrast text, restrained status colors, dense but readable evidence cards, and obvious source links. Do not use a marketing-dashboard visual style inside a case workspace.

## Routes and responsibilities

| Route | Screen | Primary API |
| --- | --- | --- |
| `/signin`, `/signup` | Email/password authentication | Supabase Auth |
| `/dashboard` | Case list, metrics, activity, Create Case | `GET /dashboard`, `GET /cases` |
| `/cases/new` | Case ID and case name form | `POST /cases` |
| `/cases/:caseId/overview` | Summary, case fields, parties, quick issues/tasks | `GET /overview` |
| `/cases/:caseId/documents` | Upload, list, preview, summary, source passage | Document endpoints |
| `/cases/:caseId/timeline` | Cited event list | `GET /timeline` |
| `/cases/:caseId/issues` | Conflicts and gaps | `GET /issues` |
| `/cases/:caseId/tasks` | Read-only proposed AI tasks | `GET /tasks` |
| `/cases/:caseId/chat` | Saved case conversation | Chat endpoints |

`/cases` is intentionally not a standalone screen. It redirects to `/dashboard`, which is the only case-list page.

## Shared case shell

Render the Case ID, case name, status badge, document count, Analyze Case button, and navigation tabs on every case route. Keep selected tab state in the route, not component-only state.

## Page requirements

### Dashboard

- Metrics: total cases, cases in review, pending tasks, unresolved issues.
- Case table/cards: case name, Case ID, preparation status, document count, last updated.
- Recent activity and a visible empty state with Create Case action.

### Overview

- AI summary with generation state.
- Confirmed details separate from **Pending lawyer review** details.
- Each pending field shows value, confidence if available, citation, and Confirm/Edit/Reject controls.
- Key parties, latest issues, and pending tasks link to their full tabs.

### Documents

- Upload drop zone and file picker with 50-file/50-MB validation before upload.
- Place an optional **Lawyer-provided context** textarea beside the multi-file upload controls. Limit it to 4,000 characters and show: “Add relevant background, questions, or facts provided by the lawyer. This is not document evidence.”
- Keep upload and analysis separate: upload first; enable **Analyze Case** only after at least one document is ready; send the current context only when analysis starts.
- **Stage 3.4:** send the textarea value only through `POST /cases/{caseId}/analysis`. Use the returned run metadata, then poll `GET /cases/{caseId}/analysis` every 2–3 seconds while status is `queued` or `processing`. Do not send context to upload or document endpoints.
- For each supported file, call the signed-upload URL endpoint, use `PUT` to upload the raw file to `upload_url`, then register the completed object. Register unsupported files with `storage_path: null` so users can see why they cannot be analyzed.
- Poll the document-list route every 2–3 seconds only while a document is `uploaded` or `processing`. Stop polling when every document is `ready`, `failed`, or `unsupported`.
- A selected ready PDF uses `read_url` in the PDF viewer. A selected ready DOCX/TXT renders the `passages` returned by document detail. Render `passage_label` and page number with each passage; treat each passage ID as stable for later citations.
- Show `error_message` for failed or unsupported files. Render Retry only for `failed`; it calls the retry endpoint and must return the list item to a processing state.
- Rows show name, format, status, error message/retry, and AI summary availability.
- PDF uses an embedded signed URL; DOCX/TXT uses normalized extracted text.
- Reader and AI summary appear side by side on desktop and stack on small screens.
- Source-link actions scroll to or highlight the cited text; if precise highlighting is unavailable, show the passage label and quote.

### Timeline and Key Issues

- Every item shows title, plain-language description, source citation, and a button to open its evidence.
- Conflict cards show separate source statements rather than a merged conclusion.
- Gap cards use “not found in uploaded material.”

### Lawyer-provided context

- Show the saved value in Overview under **Lawyer-provided context**.
- Keep it visually separate from citations, extracted fields, AI summary, timeline events, and findings.
- Preserve the textarea value if upload or analysis fails so the user can retry.

### Tasks

- Columns or grouped lists for Proposed, Approved, Done, and Rejected.
- AI tasks show source finding; manual tasks show Manual source.
- Edit is available before/during approval. Mark Done only after approval.
- Every status transition refreshes activity history.

### AI Chat

- Load stored messages on entry and append user/assistant messages after send.
- Evidence response displays citations beneath the answer.
- General guidance response shows a clear “General guidance — not based on case documents” label.
- Never imply a chat response is a legal decision.

## Required UI states

Every data view needs loading, empty, error, and ready states. Documents and analysis additionally need uploading/processing/failed/unsupported. Preserve data already shown if a background refresh fails.

## Ownership

- Akshata: auth, case creation, upload, document reader, citation navigation.
- Aayush: dashboard, case shell, overview, timeline, issues, tasks, chat.
- Sharad: API contract, backend status semantics, Supabase integration, and integration support.

## Stage 3.5 review-read integration

The workspace now reads persisted results only through FastAPI: `GET /v1/cases/{caseId}/overview`, `/timeline`, `/issues`, `/tasks`, and `/activity`. Use Overview for the case summary, current **Lawyer-provided context** label, grouped fields, parties, issue/task previews, counts, and document-summary panel. Treat `lawyer_context` as a visually separate assertion, never as evidence. Render each citation using `document_name`, `passage_label`, optional `page_number`, and `quote`; navigate to `passage_id` in the document reader. During analysis polling, retain the previous review result until a newer run completes. All routes produce explicit empty states before the first completed run.

## Stage 3.6 integration status

The frontend now uses FastAPI for analysis start/polling and for Overview, Timeline, Issues, Tasks, and Activity. Citations navigate to the Documents route with `document` and `passage` query parameters; extracted-text passages scroll and highlight, while PDFs show an Evidence focus notice. Chat and task/field actions remain deferred to Stages 4–5.

## Upload route and native document previews

After case creation, route lawyers to `/cases/{caseId}/upload`. Keep uploads, context, and Analyze Case there; Documents is the reading/evidence destination. PDFs render through PDF.js. DOCX files are fetched through a short-lived private URL, converted in-browser with Mammoth, sanitized, then rendered. Existing analysis runs are immutable, so rerun analysis after the extraction-quality update to obtain improved fields and parties.


## Current implementation status — 2026-09-27

The Stage 3 frontend integration is complete locally. Use the dedicated `/cases/{caseId}/upload` route for file upload, lawyer context, and explicit analysis start. Do not place upload controls, analysis submission, or context editing in the Documents view. The workspace header links to Upload only before a case has documents; after upload, Documents remains a reader/history view.

The upload card, document list, and reader share one responsive workspace alignment. Long filenames truncate in the list and expose the full name on hover. PDFs render with PDF.js in a scrollable in-app reader; DOCX files render sanitized Mammoth HTML from a temporary private URL; TXT and DOCX citations navigate to stable extracted passages.

Stage 3 views are read-only: do not add field confirmation, task status controls, manual task creation, or chat submission until their Stage 4/5 backend routes exist.
