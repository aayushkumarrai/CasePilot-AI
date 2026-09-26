# Test Plan

## Test environments

- **Local:** FastAPI test server, test Supabase project or isolated schema, frontend development server.
- **Preview:** Vercel preview connected to a Railway staging service and Supabase staging project.
- **Demo:** production-style Vercel/Railway/Supabase configuration with fictional documents only.

## Automated backend tests

| ID | Scenario | Expected result |
| --- | --- | --- |
| API-01 | Create a case with Case ID and name | Returns `201`; case starts as `draft`. |
| API-02 | Duplicate Case ID for same owner | Returns `409`. |
| API-03 | Access another owner’s case | Returns `404`. |
| API-04 | Register 51st document or file over 50 MB | Returns validation error. |
| API-05 | Register JPG/image | Creates record marked `unsupported`. |
| API-06 | Run analysis without documents | Returns `422`. |
| API-07 | Run analysis with valid text document | Produces pending field, cited timeline event, issue, and proposed task. |
| API-08 | One document fails and others succeed | Successful documents still produce analysis. |
| API-09 | Invalid AI citation | Backend excludes it from supported output. |
| API-10 | Confirm/edit/reject field | Field state and activity event persist. |
| API-11 | Task lifecycle | Proposed → approved → done works; rejected is terminal. |
| API-12 | Evidence chat | Assistant response contains valid citations. |
| API-13 | No evidence chat | Response is labeled `general_guidance`. |
| API-14 | Lawyer-provided context | Empty context becomes `null`; values over 4,000 characters return `422`; each analysis run stores an immutable snapshot. |
| API-15 | Context evidence boundary | AI output never cites context or turns it into a document-backed fact without valid passages. |

## Stage 2 document-intake tests

| ID | Scenario | Expected result |
| --- | --- | --- |
| DOC-01 | Request an upload URL for a valid PDF, DOCX, or TXT under 50 MB | Returns a private user/case-prefixed storage path and expiring upload URL. |
| DOC-02 | Register a supported upload whose object is absent or whose path belongs to another user/case | Returns `422`; no document record is created. |
| DOC-03 | Register a supported direct upload | Record begins `uploaded`, background extraction transitions it through `processing` to `ready`, and activity is recorded. |
| DOC-04 | Register JPG metadata with `storage_path: null` | Returns visible `unsupported` document with a safe explanation. |
| DOC-05 | Parse PDF, DOCX, and TXT | Produces ordered stable passages; PDF passages retain page number and all content blocks are at most 1,500 characters. |
| DOC-06 | Parse empty, scanned, malformed, or non-UTF-8 material | Document becomes `failed` with a safe error; unrelated documents still process. |
| DOC-07 | Read a ready PDF | Detail has a temporary `read_url`; no passage content is returned. |
| DOC-08 | Read a ready DOCX/TXT | Detail includes ordered passages with labels and IDs. |
| DOC-09 | Retry a failed supported document | Returns `202`, clears/replaces old passages during processing, and can reach `ready`. Ready and unsupported documents return `409`. |
| DOC-10 | Use User B token for User A document/list/retry/storage object | Every API/Storage access is denied or obscured as `404`; User B cannot access the private object. |

## Frontend tests

| ID | Scenario | Expected result |
| --- | --- | --- |
| WEB-01 | Dashboard loading, empty, error, ready | Each state is understandable and actionable. |
| WEB-02 | Create Case form | Validates required Case ID/name and shows duplicate error. |
| WEB-03 | Upload limits | Blocks files exceeding count/size and reports unsupported type. |
| WEB-04 | Processing state | Analyze button becomes non-duplicative; status polling ends on completion/failure. |
| WEB-05 | Citation navigation | Opens selected document and referenced passage/page. |
| WEB-06 | Field review | Confirm/Edit/Reject updates visible field grouping. |
| WEB-07 | Task state | Moving task updates its section and activity history. |
| WEB-08 | Chat | Cited and general-guidance labels render correctly. |
| WEB-09 | Lawyer-provided context | Textarea is beside uploads, preserves input after failure, sends only on Analyze Case, and displays separately from evidence. |

## End-to-end acceptance test

1. Sign in with the demo lawyer account.
2. Create `PROP-001 — Rao v Mehta`.
3. Upload the six fictional documents.
4. Enter lawyer-provided context: “The buyer says possession was never handed over. Focus on payment and key-handover records.”
5. Select Analyze Case and wait for `review` state.
6. Confirm the saved context remains visibly separate from document evidence.
7. Confirm one pending party/detail field and edit another.
8. Open the possession conflict and inspect both cited sources.
9. Confirm the missing handover acknowledgment is presented as absent only from uploaded material.
10. Approve and complete the suggested task.
11. Ask a case-specific AI question and inspect its citation.
12. Ask a general-preparation question and confirm its label.

## Exit rule

Mark a workflow Verified only after its automated test passes, the manual verification item passes, and the evidence is linked in `project-status.md`.
