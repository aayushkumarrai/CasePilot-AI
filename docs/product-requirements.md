# Product Requirements

## Goal

Help lawyers prepare a property dispute by organizing uploaded evidence into a source-linked case workspace. The lawyer remains responsible for assessing facts, making legal decisions, and taking any external action.

## Users

The prototype serves one signed-in lawyer. Each user owns and can access only their own cases.

## Main flow

1. Sign up or sign in using email and password.
2. Create a case by entering only a Case ID and case name.
3. Upload PDF, DOCX, or TXT documents.
4. Optionally add lawyer-provided context beside the upload controls.
5. Select **Analyze case** after at least one document is ready.
6. Review generated outputs and supporting passages; Stage 4 records lawyer confirmation, edits, rejections, and task workflow decisions separately from AI evidence.
7. Use citations to inspect the referenced private document or extracted passage.
8. Ask case questions after evidence is ready; cited answers are distinguished from general guidance.

## Delivered Stage 2 evidence foundation

- The user receives a signed URL and uploads supported files directly to the private Storage bucket.
- FastAPI registers each upload, extracts text asynchronously, and exposes document status and reader data.
- PDF passages retain page numbers; DOCX/TXT passages retain stable labels and IDs.
- Failed and unsupported files remain visible without preventing other files from becoming ready.
- Stage 2 does not save or send lawyer-provided context, call AI, or create analysis outputs.

## Required behavior

| Area | Requirement |
| --- | --- |
| Case creation | Require a unique Case ID per owner and a case name. Do not ask the user for other case details. |
| Files | Limit a case to 50 files and each file to 50 MB. PDF, DOCX, and TXT are supported. |
| Lawyer-provided context | Allow one optional 4,000-character statement per case. It is saved when analysis starts, shown separately from evidence, and may guide AI focus without becoming document evidence. |
| Analysis | Run only on explicit user request. Generate all workspace outputs together. |
| Case details | Extract client, parties, property/location details, dates, payment amounts, and facts as pending suggestions. |
| Evidence | Every factual result includes document and stable passage identifiers; PDFs include page number where available. |
| Context boundary | Lawyer-provided context cannot support factual claims, receive document citations, resolve conflicts, or become a confirmed extracted detail without supporting uploaded evidence. |
| Gaps | Use the phrase “not found in uploaded material.” Do not claim the missing record does not exist. |
| Conflicts | Show competing accounts and their sources. Do not select one as true. |
| Tasks | Stage 4 groups AI and manual tasks by proposed, approved, done, and rejected. AI wording remains immutable; manual wording is editable while open. |
| Chat | Persist successful user/assistant pairs by case. Evidence answers require validated passage citations; uncited answers begin with “General guidance — not based on case documents.” |
| Failure | Mark an unreadable/unsupported document and continue with documents that are usable. |

## Out of scope for version one

- OCR for scans, image files, spreadsheets, and unsupported formats.
- Case sharing, team roles, invitations, or client access.
- Automatic sending of emails, notices, or requests.
- Legal research, case-law search, legal conclusions, or autonomous legal advice.
- Due dates, priorities, and task assignments.

## Acceptance criteria

Stage 5 is ready for final QA when chat history survives reload, evidence answers navigate to stored passages, general guidance is visibly labeled, failures restore the draft without partial persistence, and cross-user/archived access returns `404`.


## Current Stage 3 experience

After case creation, the lawyer lands on a dedicated Upload page. It contains the document picker, optional lawyer-provided context, readiness state, and the only Analyze Case action. Once analysis completes, the application opens Overview. PDF and DOCX originals render through short-lived private preview URLs; TXT and DOCX citations use stable extracted passages.
