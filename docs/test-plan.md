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
| DOC-08 | Read a ready DOCX/TXT | Detail includes ordered stable passages; ready DOCX also includes a temporary private read URL for in-app preview. |
| DOC-09 | Retry a failed supported document | Returns `202`, clears/replaces old passages during processing, and can reach `ready`. Ready and unsupported documents return `409`. |
| DOC-10 | Use User B token for User A document/list/retry/storage object | Every API/Storage access is denied or obscured as `404`; User B cannot access the private object. |

## Stage 3.1 analysis-foundation tests

| ID | Scenario | Expected result |
| --- | --- | --- |
| ANA-01 | Start a run with an owned active case and ready evidence | A queued run stores a trimmed immutable context snapshot and sets the case to `processing`. |
| ANA-02 | Start a run without ready evidence or on an archived/unowned case | Ready-evidence failure is rejected; unowned/archived access returns no row. |
| ANA-03 | Start a second queued/processing run for the same case | Partial unique index rejects it. |
| ANA-04 | Complete a processing run with fixture outputs and valid passage citation | Run becomes completed, case becomes review, outputs/citation share the same run scope. |
| ANA-05 | Complete a run with another case’s document or passage | Transaction fails and writes no partial outputs. |
| ANA-06 | Fail a first run, then fail a rerun after a completed run | Case returns to draft for the first failure and review for the later failure; completed results remain. |
| ANA-07 | Query runs after multiple completions | Latest completed run is first when ordered by `completed_at desc`; older outputs remain stored. |
| ANA-08 | User B reads or mutates User A run, output, citation, or RPC | RLS blocks the access or returns no rows. |

## Stage 3.2 Groq client tests

| ID | Scenario | Expected result |
| --- | --- | --- |
| GROQ-01 | Valid JSON-object response | Parses into typed in-memory analysis output; no database write occurs. |
| GROQ-02 | Missing key or model | Fails before making a provider request. |
| GROQ-03 | Context supplied or absent | Context appears only under its separate non-evidence prompt section, or is omitted entirely. |
| GROQ-04 | Timeout, connection error, `408`, `429`, or `5xx` | Retries once, then returns safe temporary-provider error. |
| GROQ-05 | Other provider `4xx` | Returns safe provider-rejection error without retry. |
| GROQ-06 | Invalid JSON, shape, enum, confidence, output count, or output reference | Returns safe invalid-output error with no persistence. |
| GROQ-07 | Live synthetic smoke fixture | `openai/gpt-oss-20b` returns validated cited output without Supabase access or persistence. |

## Stage 3.3 evidence-assembly and citation-gate tests

| ID | Scenario | Expected result |
| --- | --- | --- |
| EVD-01 | Assemble an owned active case with ready and non-ready documents | Only ready documents are included, ordered by document creation and passage sequence. |
| EVD-02 | Complete payload equals or exceeds 180,000 characters | The exact limit is accepted; an over-limit payload raises a safe error without dropping passages. |
| EVD-03 | Citation points to another case, a missing passage, another document’s summary, or a wrong quote | Citation is discarded. |
| EVD-04 | Quote differs only by Unicode form or whitespace | Normalized matching retains the citation when the stored passage contains it. |
| EVD-05 | Case summary has no valid citation | Entire result is rejected before persistence. |
| EVD-06 | Other output has no valid citation | Output is omitted; a task whose referenced finding was omitted is also omitted. |
| EVD-07 | Valid mixed output is transformed for the completion RPC | Only grounded outputs/citations remain; case-summary citations map to `analysis_run_id`. |
| EVD-08 | Lawyer context is supplied | It appears only in the prompt’s non-evidence section and is never a citation source. |

## Stage 3.4 public analysis tests

| ID | Scenario | Expected result |
| --- | --- | --- |
| CMD-01 | Start analysis for an owned active case with ready evidence | Returns `202` with a queued safe run response; background work reaches a terminal run state. |
| CMD-02 | Poll before a run and while a run is active | Returns `200` with `run: null` before analysis; polling exposes only safe run metadata. |
| CMD-03 | Start with whitespace context, oversized context, no ready evidence, unowned case, archived case, or an active run | Normalizes blank context to `null`; returns `422`, `404`, or `409` as applicable without creating an invalid run. |
| CMD-04 | Groq or grounding failure | New run becomes `failed` with a safe message. A prior completed run remains available and keeps the case in review. |
| CMD-05 | Successful mocked provider response | Validated outputs persist through the lifecycle RPC and the case becomes review. |
| CMD-06 | Public responses | Never include lawyer context, prompts, raw provider payloads, or provider secrets. |

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
7. Confirm pending details and key parties are displayed as source-linked, read-only review output.
8. Open the possession conflict and inspect both cited sources.
9. Confirm the missing handover acknowledgment is presented as absent only from uploaded material.
10. Open the proposed task and its citations.

Stage 4 acceptance covers field/party review, manual tasks, task transitions, original-suggestion retention, safe activity events, owner isolation, and dashboard open-task metrics. Case chat remains Stage 5.

## Exit rule

Mark a workflow Verified only after its automated test passes, the manual verification item passes, and the evidence is linked in `project-status.md`.

## Stage 3.5 persisted review reads

Verify the overview, timeline, issues, tasks, and activity routes with a completed Stage 3.4 analysis. Confirm latest-completed-run selection survives a later failed or processing rerun; citation responses resolve to the expected document name, passage label, page number, quote, and stable passage ID; timeline dates sort exact/month/year before unknown text; and lawyer-provided context remains visually and semantically separate from cited evidence. Verify `401` without a bearer token and `404` for an unowned or archived case on every review route.

## Stage 3.6 frontend integration

Verify in a browser: a ready document enables Analyze Case; context is sent only on analysis start; queued and processing states poll every 2.5 seconds; completed output refreshes all review tabs; a failed rerun keeps earlier output visible with a retry warning; citations open the selected document and highlight extracted-text passages; PDFs show the evidence-focus fallback; and dashboard task/issue metrics match latest completed outputs.

## Upload route, previews, and extraction correction

Verify Create Case routes to Upload; ready documents enable explicit analysis; completion routes to Overview; ready PDFs render through PDF.js; ready DOCX files render sanitized Mammoth HTML; expired preview URLs can be refreshed; and a property-dispute rerun returns citation-grounded Rao/Mehta parties and payment/possession fields. Confirm an unavailable corrective Groq call preserves the first grounded result.

## Stage 4 lawyer workflow

- Confirm, edit, and reject fields and parties; assert original AI values and citations remain unchanged.
- Verify rejected fields and parties cannot be changed again.
- Create, edit, approve, reject, and complete manual tasks; reject invalid and terminal transitions.
- Verify AI task text edits return `422`, while valid AI status transitions succeed.
- Verify activity records only IDs/action metadata, never lawyer replacements, prompts, context, or provider data.
- Verify User B receives `404` for User A's fields, parties, AI tasks, manual tasks, and workflow RPCs.
- Verify dashboard counts proposed and approved AI/manual tasks only.
