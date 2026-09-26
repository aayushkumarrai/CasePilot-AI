# AI Pipeline and Evidence Rules

## Purpose

The AI turns extracted case passages into reviewable suggestions. It never writes a final legal conclusion, decides which conflicting account is true, or performs an external action.

## Stages

1. **Document intake:** verify type/size; record unsupported files without stopping the case run.
2. **Text extraction:** split each file into stable passages. PDFs preserve page number when possible; DOCX uses paragraph labels; TXT uses passage labels.
3. **Per-document extraction:** identify parties, claims, dates, amounts, property details, and a concise document summary.
4. **Case analysis:** combine cited evidence to create a case summary, pending details, timeline events, conflicts, gaps, and proposed tasks. Optional lawyer-provided context may guide focus but remains a separate non-evidence assertion.
5. **Citation validation:** keep only citations that reference an existing passage belonging to the stated document and contain a matching quote.
6. **Lawyer review:** present valid outputs as suggestions, record every confirmation/rejection/edit, and keep activity history.

## Required structured output

The model response must use an application JSON schema equivalent to:

```json
{
  "document_summaries": [{ "document_id": "uuid", "summary": "...", "citations": [] }],
  "case_fields": [{ "field_key": "client", "label": "Client", "value": "...", "confidence": 0.0, "citations": [] }],
  "timeline": [{ "event_date": "YYYY-MM-DD or unknown", "title": "...", "description": "...", "citations": [] }],
  "findings": [{ "kind": "conflict or gap", "title": "...", "description": "...", "citations": [] }],
  "tasks": [{ "title": "...", "description": "...", "finding_reference": "..." }]
}
```

The backend must validate the schema, discard invalid citations, and mark an output as needing review if it has no valid source.

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
- NVIDIA failure or invalid JSON: mark analysis run failed with an actionable error; preserve earlier completed results.
- Invalid citation: omit that output or mark it ungrounded for review; never display it as supported evidence.
