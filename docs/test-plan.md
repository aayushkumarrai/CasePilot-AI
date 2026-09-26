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

## End-to-end acceptance test

1. Sign in with the demo lawyer account.
2. Create `PROP-001 — Rao v Mehta`.
3. Upload the six fictional documents.
4. Select Analyze Case and wait for `review` state.
5. Confirm one pending party/detail field and edit another.
6. Open the possession conflict and inspect both cited sources.
7. Confirm the missing handover acknowledgment is presented as absent only from uploaded material.
8. Approve and complete the suggested task.
9. Ask a case-specific AI question and inspect its citation.
10. Ask a general-preparation question and confirm its label.

## Exit rule

Mark a workflow Verified only after its automated test passes, the manual verification item passes, and the evidence is linked in `project-status.md`.
