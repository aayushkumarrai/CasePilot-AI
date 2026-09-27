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
- Review source-linked AI fields and parties, then create and manage AI or manual follow-up tasks.
- Inspect PDFs, DOCX files, and extracted TXT passages inside the application.

Stage 4 lawyer review and task workflow is verified. Case chat remains a later stage.

## Stack

| Area | Choice |
| --- | --- |
| Frontend | Next.js, React, TypeScript, Tailwind CSS, Vercel |
| Backend | Python, FastAPI, Railway |
| Data and authentication | Supabase Postgres, Storage, Auth, Row Level Security |
| AI | Groq OpenAI-compatible API using `openai/gpt-oss-20b` |

## Current implementation

Stages 1–4 are feature-complete locally. Stage 4 provides owner-safe lawyer review of source-linked fields and parties, manual task creation, and task workflow while preserving AI suggestions and citations.

The browser uses FastAPI for all case, document, analysis, and review data; it never reads Supabase analysis tables or calls lifecycle RPCs directly. AI outputs are retained per completed run, and every displayed factual output is grounded in a stored document passage. A corrective Groq pass can fill clearly evidenced missing parties or core fields without treating lawyer context as evidence.

Stage 4 adds lawyer field/party review actions, manual tasks, and task status transitions while retaining AI suggestions and citations. Stage 5 will add persisted evidence-grounded case chat. Stage 6 covers full end-to-end regression, deployment, and demo rehearsal.

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
