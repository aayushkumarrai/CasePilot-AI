# CasePilot AI

CasePilot AI is a source-linked legal case-preparation assistant for lawyers and legal teams. It turns a collection of case documents into a structured brief, timeline, key issues, and proposed follow-up tasks for lawyer review.

The project is a 24-hour Build for Billions Agentic AI prototype by Team MIB, KLE Technological University.

## Core principle

CasePilot supports document organization and preparation. It does not make legal decisions, give autonomous legal advice, or perform external actions. Every factual AI output should link to supporting case material, while conflicts and missing information remain visible for lawyer review.

## Prototype scope

- Create a case with a Case ID and case name.
- Upload up to 50 PDF, DOCX, or TXT documents, each up to 50 MB.
- Generate a case summary, pending extracted details, key parties, document summaries, timeline, issues, and tasks after the user selects **Analyze case**.
- Review documents inside the application and inspect cited source passages.
- Confirm, edit, or reject extracted case details.
- Create, edit, approve, reject, and complete tasks.
- Hold a persisted case-specific AI chat, with citations for evidence-based answers.

## Stack

| Area | Choice |
| --- | --- |
| Frontend | Next.js, React, TypeScript, Tailwind CSS, Vercel |
| Backend | Python, FastAPI, Railway |
| Data and authentication | Supabase Postgres, Storage, Auth, Row Level Security |
| AI | NVIDIA API Catalog through an OpenAI-compatible backend integration |

## Current implementation

Stage 1 is verified with real Supabase Auth and Row Level Security. It includes email/password sign-up and sign-in, authenticated profile lookup, dashboard data, case creation and updates, soft archive/restore, activity history, and Postman coverage. Document upload and AI analysis begin in later stages.

## Documentation

- [Product requirements](docs/product-requirements.md)
- [Architecture](docs/architecture.md)
- [Frontend handover](docs/frontend-handover.md)
- [Frontend Stage 1 integration tasks](docs/frontend-stage1-tasks.md)
- [Frontend Auth and database-schema handover](docs/frontend-auth-and-schema-handover.md)
- [API handover](docs/api-handover.md)
- [Postman testing guide](docs/postman-testing.md)
- [AI pipeline](docs/ai-pipeline.md)
- [Test plan](docs/test-plan.md)
- [Verification checklist](docs/verification-checklist.md)
- [Demo script](docs/demo-script.md)
- [Project status](docs/project-status.md)
- [Stage-by-stage implementation plan](docs/implementation-stages.md)
- [Development setup](docs/development-setup.md)
- [Deployment configuration](docs/deployment.md)

The importable Stage 1 Postman collection and its safe environment template are in [`postman/`](postman/).

## Team

- **Sharad Siddanagoudar:** system architecture, FastAPI backend, Supabase, document processing, AI orchestration.
- **Akshata Patil:** frontend case creation, uploads, document/source viewing, documentation.
- **Aayush Kumar Rai:** frontend dashboard, case workspace, timeline, issues, tasks, AI chat, documentation and demo preparation.

## Reference material

- [Initial screening proposal](submission/CasePilot_Initial_Screening_Proposal.docx)
- [Concept wireframe](submission/CasePilot_Wireframe.png)
