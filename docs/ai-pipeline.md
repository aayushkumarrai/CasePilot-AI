# AI Pipeline and Evidence Rules

## Purpose

The AI turns extracted case passages into reviewable suggestions. It never writes a final legal conclusion, decides which conflicting account is true, or performs an external action.

## Stages

1. **Document intake:** verify type/size; record unsupported files without stopping the case run.
2. **Text extraction:** split each file into stable passages. PDFs preserve page number when possible; DOCX uses paragraph labels; TXT uses passage labels.
3. **Per-document extraction:** identify parties, claims, dates, amounts, property details, and a concise document summary.
4. **Case analysis:** combine cited evidence to create a case summary, pending details, timeline events, conflicts, gaps, and proposed tasks. Optional lawyer-provided context may guide focus but remains a separate non-evidence assertion.
5. **Citation validation:** keep only citations whose normalized non-empty quote occurs in an existing stored passage. Every factual output, including the case summary and a proposed task, needs at least one retained citation.
6. **Lawyer review and workflow:** present grounded AI outputs as suggestions. Stage 4 stores field/party decisions separately from AI output and citations, while tasks move through a lawyer-controlled workflow without another AI call.

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

Stage 5 retrieves only ready passages for the active owned case. Ranking uses deterministic question-token overlap, phrase matching, and document-name matching; a no-match question receives the first 10 ordered passages. The request is capped at 20 passages and 60,000 evidence characters. The prompt also includes the latest 20 messages and confirmed reviewed fields/parties in a separate non-document section. Lawyer-provided upload context is not added to chat evidence.

Groq returns typed JSON. Evidence citations are accepted only when the passage was retrieved for this request and the normalized quote occurs in stored passage content. A general-guidance answer must have no citations and begin with the required label. Provider, schema, grounding, or persistence failure returns a safe error and saves neither message.

## Failure handling

- Unsupported type: mark document `unsupported`, show why, continue.
- Extraction failure: mark `failed`, retain error message, allow retry, continue.
- Groq failure or invalid JSON: mark analysis run failed with an actionable error; preserve earlier completed results.
- Invalid analysis citation: omit that output or fail the analysis when the case summary is ungrounded.
- Invalid chat citation: reject the complete exchange and persist nothing.
