# Product Requirements

## Goal

Help lawyers prepare a property dispute by organizing uploaded evidence into a source-linked case workspace. The lawyer remains responsible for assessing facts, making legal decisions, and taking any external action.

## Users

The prototype serves one signed-in lawyer. Each user owns and can access only their own cases.

## Main flow

1. Sign up or sign in using email and password.
2. Create a case by entering only a Case ID and case name.
3. Upload PDF, DOCX, or TXT documents.
4. Select **Analyze case**.
5. Review generated outputs and supporting passages.
6. Confirm, edit, or reject pending case details.
7. Act on suggested tasks and ask case-specific questions in AI Chat.

## Required behavior

| Area | Requirement |
| --- | --- |
| Case creation | Require a unique Case ID per owner and a case name. Do not ask the user for other case details. |
| Files | Limit a case to 50 files and each file to 50 MB. PDF, DOCX, and TXT are supported. |
| Analysis | Run only on explicit user request. Generate all workspace outputs together. |
| Case details | Extract client, parties, property/location details, dates, payment amounts, and facts as pending suggestions. |
| Evidence | Every factual result includes document and stable passage identifiers; PDFs include page number where available. |
| Gaps | Use the phrase “not found in uploaded material.” Do not claim the missing record does not exist. |
| Conflicts | Show competing accounts and their sources. Do not select one as true. |
| Tasks | Allow user-created and AI-created tasks. Track proposed, approved, done, or rejected state. |
| Chat | Persist messages by case. Evidence answers have citations; general preparation guidance is labeled as such. |
| Failure | Mark an unreadable/unsupported document and continue with documents that are usable. |

## Out of scope for version one

- OCR for scans, image files, spreadsheets, and unsupported formats.
- Case sharing, team roles, invitations, or client access.
- Automatic sending of emails, notices, or requests.
- Legal research, case-law search, legal conclusions, or autonomous legal advice.
- Due dates, priorities, and task assignments.

## Acceptance criteria

The prototype is ready when a lawyer can complete the fictional property-dispute demo from upload through source inspection, task approval, and cited case chat without manual database changes.
