# Demo Script

## Demo case

**Case:** `PROP-001 — Rao v Mehta`  
**Type:** Fictional property possession and final-payment dispute.

Use six short fictional documents:

1. Sale agreement — parties, property description, payment schedule, possession terms.
2. Payment receipt — initial payment.
3. Bank transaction record — later payment evidence.
4. Seller notice — says keys and possession were handed over on 10 June.
5. Buyer email — says keys had not arrived by 15 June.
6. Property annexure — includes a property-area discrepancy.

Do not include a signed handover acknowledgment. The system should flag it as not found in uploaded material.

## Three-minute story

1. **Dashboard:** “CasePilot organizes scattered evidence into a lawyer-reviewable workspace.” Create or open `PROP-001`.
2. **Create and upload:** Create the case using only its Case ID and name. The app opens Upload. Add the packet, then enter: “The buyer says possession was never handed over. Focus on payment and key-handover records.” Explain that this context guides review but is not evidence.
3. **Analysis:** Select **Analyze case** after a document is ready. Show queued/processing state, then the automatic move to Overview.
4. **Overview:** Show the separately labeled lawyer context, cited summary, pending details, key parties, conflict, and proposed task. Open a citation to show that every factual claim can be traced to source material.
5. **Documents:** Select the seller notice or agreement. Show the built-in PDF/DOCX/TXT reader and, for a citation, the evidence focus/passage highlight.
6. **Timeline and issues:** Show payment and possession-related events in chronological order. Open the possession conflict and compare seller and buyer sources. Show the missing acknowledgment wording.
7. **Tasks and activity:** Show the read-only proposed task and safe activity timeline. Explain that approval and completion controls are the next workflow stage.
8. **Close:** “CasePilot does not decide the case. It gives the lawyer an organized, traceable basis for review.”

## Fallback plan

- Keep a pre-analyzed case available as a fallback even though the verified Groq synthetic check completed in 1.262 seconds.
- Keep screenshots of Overview, Documents, Key Issues, Tasks, and Chat.
- If deployment fails, run the local app with the same fictional case packet.
- Never use real client documents or credentials in the presentation.

## Stage 3.6 frontend walkthrough

1. Open the fictional property-dispute case and upload the source documents.
2. Wait until at least one document is ready, enter lawyer-provided context, then select **Analyze case**.
3. Show queued and processing status, then the refreshed Overview with separate lawyer context, summary, conflict, and proposed task.
4. Open Timeline, Issues, and Tasks to show cited persisted review output.
5. Select a citation to open the matching document and highlighted passage. For PDFs, show the Evidence focus notice and the source quote.
6. Return to Dashboard and show that pending-task and unresolved-issue metrics reflect the latest completed run.
