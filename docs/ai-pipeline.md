# AI Pipeline and Evidence Rules

## Purpose

The AI turns extracted case passages into reviewable suggestions. It never writes a final legal conclusion, decides which conflicting account is true, or performs an external action.

## Stages

1. **Document intake:** verify type/size; record unsupported files without stopping the case run.
2. **Text extraction:** split each file into stable passages. PDFs preserve page number when possible; DOCX uses paragraph labels; TXT uses passage labels.
3. **Per-document extraction:** identify parties, claims, dates, amounts, property details, and a concise document summary.
4. **Case analysis:** combine cited evidence to create a case summary, pending details, timeline events, conflicts, gaps, and proposed tasks. Optional lawyer-provided context may guide focus but remains a separate non-evidence assertion.
5. **Citation validation:** keep only citations whose normalized non-empty quote occurs in an existing stored passage. Every factual output, including the case summary and a proposed task, needs at least one retained citation.
6. **Stage 3 lawyer review:** present valid outputs as read-only suggestions and activity history. Stage 4 adds confirmation/rejection/edit and task workflow actions.

## Required structured output

The model response must use an application JSON schema equivalent to:

```json
{
  "case_summary": "...",
  "document_summaries": [{ "ref": "document_summary_1", "document_id": "uuid", "summary": "..." }],
  "case_fields": [{ "ref": "field_1", "field_key": "client", "label": "Client", "value": "...", "confidence": 0.0 }],
  "citations": [{ "target_type": "case_summary", "target_ref": "case_summary", "passage_id": "uuid", "quote": "..." }]
}
```

Output-specific `ref` values let the backend normalize citations separately. The case summary always uses the fixed reference `case_summary`. The backend drops uncited non-summary outputs, rejects an uncited case summary, and never sends lawyer-provided context as citation material.

## Provider boundary

The Stage 3.2 backend client sends prepared evidence and optional context to Groq's OpenAI-compatible chat-completions endpoint using `openai/gpt-oss-20b`. JSON-object mode, hidden low-effort reasoning, and Pydantic validation keep the response machine-readable. The client retries one temporary provider failure, rejects malformed JSON or invalid response shape, and does not persist or expose provider output until later analysis stages validate evidence citations.

## Prompt rules

- Use only supplied passage text for factual statements.
- Pass lawyer-provided context in a separate prompt section titled **Lawyer-provided context — not document evidence**.
- The model may use that context to prioritize questions or follow-up tasks, but may not cite it, convert it into a confirmed fact, or use it to resolve a conflict.
- Cite every factual claim using the provided document and passage IDs.
- For a disagreement, preserve both statements and label it a potential conflict.
- For absent information, say “not found in uploaded material.”
- Return `unknown` rather than guessing names, dates, amounts, or legal meaning.
- Proposed tasks must be review actions, for example “Request the signed handover acknowledgment.”
- Do not send messages, create filings, advise a legal outcome, or select a side in a dispute.

## Case chat policy

Classify every assistant response as one of:

| Type | Requirement |
| --- | --- |
| `evidence` | Answer based on uploaded case material and include one or more valid citations. |
| `general_guidance` | May give general preparation advice, but starts with “General guidance — not based on case documents.” |

If the evidence cannot answer the question, the assistant should say so and suggest what record to review or request.

## Failure handling

- Unsupported type: mark document `unsupported`, show why, continue.
- Extraction failure: mark `failed`, retain error message, allow retry, continue.
- Groq failure or invalid JSON: mark analysis run failed with an actionable error; preserve earlier completed results.
- Invalid citation: omit that output or mark it ungrounded for review; never display it as supported evidence.
