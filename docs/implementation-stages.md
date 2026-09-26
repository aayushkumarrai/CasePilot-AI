# CasePilot AI Implementation Stages

This document is the team’s working order for the hackathon. Complete each stage’s exit checks before marking it ready in [Project Status](project-status.md).

## Stage 0 — Project Setup and Shared Contract

**Goal:** Give every team member a stable project, shared vocabulary, and API contract before feature work begins.

### Work plan

1. **Repository and branch setup** — Team
   - Confirm the repository remote, default branch, `.gitignore`, and contribution workflow.
   - Create `frontend`, `backend`, and `integration` working branches or follow a clear pull-request naming convention.
2. **Supabase project** — Sharad
   - Create the project, enable email/password Auth, create the private `case-documents` Storage bucket, and apply owner-only RLS rules.
   - Store project URL and anonymous key in the frontend environment; store service credentials only in Railway/FastAPI.
3. **Application scaffolds** — Aayush and Sharad
   - Create Next.js/React/TypeScript/Tailwind and FastAPI projects in the agreed monorepo paths.
   - Add local environment examples and health checks.
4. **API contract freeze** — Sharad, Akshata, Aayush
   - Review [API Handover](api-handover.md) together.
   - Freeze response shapes for case, document, citation, field, task, timeline event, finding, and chat message before frontend integration.

### Exit checks

- A developer can run frontend and backend locally.
- Supabase sign-up/sign-in works.
- FastAPI `/health` works.
- Frontend can call one protected test endpoint with a Supabase access token.
- All owners mark Stage 0 as Verified in `project-status.md`.

---

## Stage 1 — Identity, Cases, and Dashboard Foundation

**Goal:** A signed-in lawyer can create, find, and open an empty case.

### Backend subplan — Sharad

1. Create `profiles` and `cases` schema plus Row Level Security.
2. Implement `GET /dashboard`, `GET /cases`, `POST /cases`, and `GET /cases/{caseId}`.
3. Enforce unique Case ID for each owner.
4. Add activity event when a case is created.

### Frontend subplan — Aayush and Akshata

1. Build sign-up, sign-in, sign-out, and protected-route behavior.
2. Build dashboard loading, empty, error, and ready states.
3. Build Create Case form with only Case ID and case name.
4. Build the shared case workspace shell and route navigation.

### Exit checks

- User A cannot see User B’s case.
- A lawyer can create `PROP-001 — Rao v Mehta`.
- Dashboard shows the new case as Draft.
- Case workspace routes render their empty states.

---

## Stage 2 — Document Upload and Evidence Foundation

**Goal:** A case can securely hold documents that the user can inspect inside the app.

### Backend subplan — Sharad

1. Implement private Storage upload flow: request signed URL, direct browser upload, document registration.
2. Enforce 50-document and 50-MB limits.
3. Support PDF, DOCX, and TXT; flag unsupported types without blocking the rest of the case.
4. Add document status, retry, signed reading URL, and activity events.
5. Extract text and create stable passages with document/page/paragraph labels.

### Frontend subplan — Akshata

1. Build upload drop zone, file picker, client-side file validation, progress, and errors.
2. Reserve an optional 4,000-character Lawyer-provided context textarea beside multi-file uploads. It is not sent during upload and must state that it is not document evidence.
3. Build document list with status, failure reason, retry, and selected-document state.
4. Build PDF reader using temporary signed URL.
5. Build extracted text viewer for DOCX/TXT with passage labels.
6. Reserve a side panel for AI document summary.

### Exit checks

- User can upload PDF, DOCX, and TXT to a private case.
- Unsupported image file shows an understandable status without breaking the page.
- User can read an uploaded PDF without downloading it.
- Passage identifiers are stable and can be linked from other screens.

### Completion record — 2026-09-26

**Verified.** Private PDF, DOCX, and TXT uploads, background extraction, PDF reading, stable passages, unsupported-file visibility, retry, and two-user owner isolation passed live Postman checks. The optional context control remains frontend-only until Stage 3.

---

## Stage 3 — Analysis Pipeline and AI Validation

**Goal:** Explicit analysis transforms usable documents into reviewable, source-linked case outputs.

### Backend subplan — Sharad

1. Implement `POST /analysis` and analysis status polling.
2. Add nullable current lawyer context to the case and immutable context snapshot to each analysis run. Validate a maximum of 4,000 characters.
3. Configure NVIDIA API through Railway environment variables; keep key server-side.
4. Build structured prompts for per-document extraction and cross-case analysis, with lawyer context in a separate non-evidence section.
5. Generate document summaries, pending fields, key parties, timeline events, findings, and proposed tasks.
6. Validate each returned citation against stored passages before persistence.
7. Continue analysis when one document fails; record the failure clearly.
8. Store analysis run, outputs, and activity history.

### Frontend subplan — Aayush

1. Add Analyze Case action and processing state to the case shell.
2. Send the optional lawyer-provided context only when Analyze Case is selected; preserve it after failures and show the saved value separately in Overview.
3. Poll analysis status every 2–3 seconds only while the run is active.
4. Display analysis errors and retry guidance without deleting prior completed results.

### Exit checks

- Analyze Case is unavailable until at least one document is ready.
- Analysis creates all planned outputs from the fictional packet.
- Each factual output includes a valid document/passage citation.
- Invalid or unsupported AI output never appears as verified evidence.

---

## Stage 4 — Lawyer Review Workspace

**Goal:** The lawyer can inspect, correct, and act on the AI’s suggestions.

### Overview subplan — Aayush

1. Render case summary, confirmed details, pending fields, key parties, recent issues, and pending tasks.
2. Add Confirm/Edit/Reject actions for each pending field.
3. Keep pending and confirmed values visually separate.

### Timeline and Issues subplan — Aayush

1. Render chronological timeline with date confidence and source actions.
2. Render conflict cards with both competing accounts and citations.
3. Render gaps using “not found in uploaded material.”

### Tasks subplan — Aayush

1. Render Proposed, Approved, Done, and Rejected task states.
2. Support manual task creation and task editing.
3. Support Proposed → Approved → Done and Proposed → Rejected.
4. Record every action in Activity History.

### Integration support — Sharad and Akshata

1. Verify API responses match the frontend contract.
2. Ensure every citation opens the correct reader/document state.

### Exit checks

- A pending detail can be confirmed, corrected, or rejected and remains correct after refresh.
- A possession conflict shows seller and buyer evidence separately.
- The handover-acknowledgment gap follows the required wording.
- A proposed task can be approved and completed.

---

## Stage 5 — Case AI Chat

**Goal:** The lawyer can ask questions while CasePilot keeps conversation and evidence scoped to the current case.

### Backend subplan — Sharad

1. Store user and assistant chat messages by case.
2. Retrieve relevant case passages, confirmed case details, and recent conversation before each AI call.
3. Classify answers as `evidence` or `general_guidance`.
4. Require valid citations for `evidence` responses.
5. Label general responses: “General guidance — not based on case documents.”

### Frontend subplan — Aayush

1. Build chat history, prompt box, send/loading/error state, and message grouping.
2. Render citations beneath evidence responses.
3. Render the general-guidance label prominently.
4. Preserve chat history after route changes and reloads.

### Exit checks

- A possession question returns cited case evidence.
- A general preparation question returns the required label.
- The conversation remains isolated to the selected case.

---

## Stage 6 — Testing, Integration, and Deployment

**Goal:** Turn individual features into a reliable deployed demo.

### Work plan

1. **Backend tests** — Sharad
   - Execute all API scenarios from [Test Plan](test-plan.md).
   - Test ownership, limits, document failure continuation, citations, field review, task lifecycle, and chat labels.
2. **Frontend tests** — Aayush and Akshata
   - Test all loading, empty, error, processing, and ready states.
   - Verify source navigation, task state changes, and chat rendering.
3. **Integration run** — Team
   - Run the end-to-end property-dispute scenario on one shared preview environment.
   - Fix API mismatches before visual polishing.
4. **Deployment** — Sharad, Aayush, Akshata
   - Deploy FastAPI to Railway and Next.js to Vercel.
   - Set CORS and production environment variables.

### Exit checks

- Automated tests pass.
- All critical items in [Verification Checklist](verification-checklist.md) pass.
- Every release-blocking item is marked Verified in `project-status.md`.
- The deployed app runs the demo scenario without local-only dependencies.

---

## Stage 7 — Demo Rehearsal and Final Freeze

**Goal:** Deliver a confident, resilient demonstration.

### Work plan

1. Seed the final fictional property-dispute case and verify all expected findings.
2. Rehearse the three-minute sequence in [Demo Script](demo-script.md).
3. Prepare fallback screenshots or a short recording of all major screens.
4. Remove test/placeholder labels from the presentation environment.
5. Freeze API response shapes and avoid new features after final verification.

### Exit checks

- Every team member can explain their component in the demo.
- Demo account is signed in and loaded before presentation.
- Fallback assets are available.
- `project-status.md` reads **Demo readiness: Ready**.

## Daily working rhythm

1. Update `project-status.md` before starting and after completing a work item.
2. Share API schema changes before merging them.
3. Mark work Ready for Review only after a developer has tested it locally.
4. Mark work Verified only after the owner completes the relevant checklist item.
5. Do not start a later stage if its required source data or API contract is still blocked.
