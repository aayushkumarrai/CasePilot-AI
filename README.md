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
| AI | Groq OpenAI-compatible API using `openai/gpt-oss-20b` |

## Current implementation

Stages 1 and 2 are verified with real Supabase Auth, Postgres RLS, and private Storage. Stage 3.1 analysis storage/lifecycle and Stage 3.2 Groq structured-output validation are also verified. Stage 3.3 evidence assembly and citation validation are implemented locally and await the linked Supabase migration and live fixture verification. The working backend includes authentication, dashboard and case lifecycle APIs, signed direct uploads for PDF/DOCX/TXT, background text extraction, stable evidence passages, temporary PDF read URLs, unsupported-file visibility, retries, and owner isolation. Public analysis-run APIs begin in Stage 3.4.

## Documentation

- [Product requirements](docs/product-requirements.md)
- [Architecture](docs/architecture.md)
- [Frontend handover](docs/frontend-handover.md)
- [Frontend Stage 1 integration tasks](docs/frontend-stage1-tasks.md)
- [Frontend Stage 2 document tasks](docs/frontend-stage2-tasks.md)
- [Frontend Auth and database-schema handover](docs/frontend-auth-and-schema-handover.md)
- [API handover](docs/api-handover.md)
- [Postman testing guide](docs/postman-testing.md)
- [AI pipeline](docs/ai-pipeline.md)
- [Test plan](docs/test-plan.md)
- [Verification checklist](docs/verification-checklist.md)
- [Demo script](docs/demo-script.md)
- [Project status](docs/project-status.md)
- [Stage-by-stage implementation plan](docs/implementation-stages.md)
- [Stage 3 analysis breakdown](docs/stage3-analysis-breakdown.md)
- [Development setup](docs/development-setup.md)
- [Deployment configuration](docs/deployment.md)

The importable Stage 1 and Stage 2 Postman collections and safe environment template are in [`postman/`](postman/).

## Team

- **Sharad Siddanagoudar:** system architecture, FastAPI backend, Supabase, document processing, AI orchestration.
- **Akshata Patil:** frontend case creation, uploads, document/source viewing, documentation.
- **Aayush Kumar Rai:** frontend dashboard, case workspace, timeline, issues, tasks, AI chat, documentation and demo preparation.

## Reference material

- [Initial screening proposal](submission/CasePilot_Initial_Screening_Proposal.docx)
- [Concept wireframe](submission/CasePilot_Wireframe.png)
