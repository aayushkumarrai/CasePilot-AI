# CasePilot-AI
# CasePilot AI

## Source-Linked Legal Case Preparation Assistant

CasePilot AI is an agentic AI-powered legal case preparation assistant that helps lawyers turn scattered case documents into a structured, evidence-linked case brief.

Legal case preparation often requires manually reviewing agreements, notices, payment records, emails, and other evidence. CasePilot is designed to reduce this repetitive work by extracting relevant information, reconstructing case timelines, identifying conflicting statements, highlighting missing information, and proposing follow-up tasks for lawyer review.

## What CasePilot Does

Users can create a case and upload text-based PDF, DOCX, or TXT documents. The system processes the uploaded files and generates a structured view of the case.

The workflow is:

Upload Documents  
→ Extract Text  
→ Extract Evidence  
→ Analyze the Case  
→ Validate Source References  
→ Lawyer Review

Key capabilities include:

- Evidence-linked case summaries
- Automatic case timeline generation
- Identification of conflicting accounts
- Detection of information missing from the uploaded documents
- Source references to relevant pages or passages
- AI-generated follow-up tasks
- Human review and approval of AI suggestions
- Activity history of AI suggestions and user decisions

A core principle of CasePilot is that AI-generated findings remain traceable to their supporting evidence. Conflicting accounts are presented to the lawyer rather than being silently resolved by the system.

## Agentic AI Approach

CasePilot uses a controlled agent workflow to connect document understanding with case preparation.

The system extracts facts, parties, claims, and events from the uploaded documents, analyzes the information for potential conflicts and gaps, validates the generated source references, and presents the results to the lawyer for review.

The system distinguishes between:

- Statements directly supported by the uploaded documents
- AI-generated analysis or inference
- Information that was not found in the uploaded material

This evidence-first approach helps keep the lawyer in control of the final interpretation and decision-making process.

## Technology Stack

### Frontend
- React
- TypeScript
- Tailwind CSS

### Backend
- Node.js
- TypeScript

### Data and Storage
- Supabase PostgreSQL
- Supabase Storage
- Supabase Auth
- Row-Level Security

### AI
- NVIDIA API Catalog

### Document Processing
- PDF text extraction
- DOCX parsing
- TXT parsing
- JSON schema validation
- Source and citation validation

The planned architecture keeps AI API keys on the backend and uses case ownership checks and access controls to restrict case data. :contentReference[oaicite:1]{index=1}

## Example Use Case

The prototype demonstrates a fictional property possession and payment dispute.

Multiple documents may contain different accounts of when possession was transferred. CasePilot identifies the conflicting statements, links them to their original sources, and proposes a follow-up task for the lawyer to review.

For example:

- One document states that the property keys were delivered on a particular date.
- Another document gives a different account of when possession occurred.
- CasePilot highlights the conflict and allows the lawyer to inspect both sources before deciding what action to take.

## Human-in-the-Loop Design

CasePilot is designed to assist legal professionals rather than replace legal judgment.

AI-generated tasks remain pending until a lawyer reviews them. The lawyer can approve, edit, or reject a suggested task, and the decision is recorded in the activity history.

CasePilot does not autonomously make legal decisions or execute consequential legal actions without human approval. :contentReference[oaicite:2]{index=2}

## Future Scope

The project can be extended to support:

- OCR for scanned documents
- Regional-language document processing
- Larger document collections
- Background processing and queued jobs
- Document chunking and retrieval
- Tenancy, consumer, and contract dispute workflows
- Stronger security and tenant isolation
- Retention and compliance controls
- Testing and validation with legal professionals :contentReference[oaicite:3]{index=3}

## Project Status

CasePilot AI is being developed as an Agentic AI prototype for the Build for Billions challenge.

The initial prototype focuses on a bounded set of fictional case documents and demonstrates the complete workflow from document upload to evidence inspection and lawyer review. :contentReference[oaicite:4]{index=4}

## Team

**Team MIB**  
KLE Technological University

- Sharad Siddanagoudar — System Architecture, Backend, Supabase Integration, Document Processing, AI Orchestration
- Akshata Patil — Frontend, Case Creation, Document Uploads, Source Viewing, Documentation
- Aayush Kumar Rai — Frontend, Case Brief, Timeline, Issue Review, Task Decisions, Documentation and Demo Preparation :contentReference[oaicite:5]{index=5}

## Disclaimer

CasePilot AI is a case-preparation assistant and not a substitute for professional legal judgment.

The prototype uses fictional case data and is intended to assist with document organization, evidence review, and case preparation. It does not provide autonomous legal advice or make final legal decisions.
