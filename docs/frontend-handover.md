# Frontend Handover

## Visual direction

Use a professional legal workspace: calm neutral surfaces, high contrast text, restrained status colors, dense but readable evidence cards, and obvious source links. Do not use a marketing-dashboard visual style inside a case workspace.

## Routes and responsibilities

| Route | Screen | Primary API |
| --- | --- | --- |
| `/login`, `/signup` | Email/password authentication | Supabase Auth |
| `/dashboard` | Case list, metrics, activity, Create Case | `GET /dashboard`, `GET /cases` |
| `/cases/new` | Case ID and case name form | `POST /cases` |
| `/cases/:caseId/overview` | Summary, case fields, parties, quick issues/tasks | `GET /overview` |
| `/cases/:caseId/documents` | Upload, list, preview, summary, source passage | Document endpoints |
| `/cases/:caseId/timeline` | Cited event list | `GET /timeline` |
| `/cases/:caseId/issues` | Conflicts and gaps | `GET /issues` |
| `/cases/:caseId/tasks` | Task review and manual task form | Task endpoints |
| `/cases/:caseId/chat` | Saved case conversation | Chat endpoints |

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
- Rows show name, format, status, error message/retry, and AI summary availability.
- PDF uses an embedded signed URL; DOCX/TXT uses normalized extracted text.
- Reader and AI summary appear side by side on desktop and stack on small screens.
- Source-link actions scroll to or highlight the cited text; if precise highlighting is unavailable, show the passage label and quote.

### Timeline and Key Issues

- Every item shows title, plain-language description, source citation, and a button to open its evidence.
- Conflict cards show separate source statements rather than a merged conclusion.
- Gap cards use “not found in uploaded material.”

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
