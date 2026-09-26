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
2. **Overview:** Show that the user supplied only the Case ID and name. Point to AI-extracted details waiting for confirmation, with source links.
3. **Documents:** Upload the packet, then add: “The buyer says possession was never handed over. Focus on payment and key-handover records.” Point out the Lawyer-provided context label and explain that it guides review but is not evidence. Select the seller notice. Show the built-in preview/extracted reader and concise AI summary.
4. **Timeline:** Show payment and possession-related events in chronological order, each supported by document passages rather than the lawyer-provided context.
5. **Key Issues:** Open the possession conflict. Compare the seller notice and buyer email source passages. Then show the missing acknowledgment wording.
6. **Tasks:** Approve “Request the signed handover acknowledgment,” then mark it done. Show activity history.
7. **AI Chat:** Ask “What evidence discusses possession handover?” and show cited reply. Ask “How should I organize follow-up evidence?” and show its general-guidance label.
8. **Close:** “CasePilot does not decide the case. It gives the lawyer an organized, traceable basis for review.”

## Fallback plan

- Keep a pre-analyzed case available if live NVIDIA analysis is slow.
- Keep screenshots of Overview, Documents, Key Issues, Tasks, and Chat.
- If deployment fails, run the local app with the same fictional case packet.
- Never use real client documents or credentials in the presentation.
