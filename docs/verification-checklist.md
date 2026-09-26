# Pre-Demo Verification Checklist

Use this checklist on the final demo environment. Record the date, person, and evidence URL or screenshot in `project-status.md`.

## Setup

- [ ] GitHub repository contains current documentation and implementation branch.
- [ ] Supabase Auth email/password flow works.
- [ ] Supabase Storage bucket is private.
- [ ] Railway API health endpoint returns success.
- [ ] Vercel uses the deployed Railway API URL.
- [ ] NVIDIA key is present on Railway only and never in frontend environment variables.

## Case flow

- [ ] Create Case accepts only Case ID and case name.
- [ ] Dashboard shows created case and correct status.
- [ ] Upload accepts PDF, DOCX, and TXT.
- [ ] Upload blocks a file over 50 MB and more than 50 documents.
- [ ] Unsupported file is visible and explains why it was not analyzed.
- [ ] Analyze Case starts only after explicit user action.
- [ ] Completed analysis changes the case to Review.

## Evidence and review

- [ ] Overview shows summary, pending details, and confirmed details separately.
- [ ] Every displayed factual finding has a working citation.
- [ ] PDF citation opens the right page or passage label.
- [ ] DOCX/TXT citation opens the right extracted passage.
- [ ] Conflict view shows both source accounts.
- [ ] Gap wording says “not found in uploaded material.”
- [ ] Confirm/Edit/Reject field actions persist after refresh.

## Tasks and chat

- [ ] AI-proposed task begins as Proposed.
- [ ] Manual task creation works.
- [ ] Approve, Reject, and Done actions persist and appear in activity history.
- [ ] Evidence chat answer displays a valid citation.
- [ ] General chat answer displays the required general-guidance label.
- [ ] Chat history remains after page refresh.

## Presentation readiness

- [ ] The fictional property-dispute packet is uploaded and analyzed in the demo account.
- [ ] Browser has the deployed application open and signed in.
- [ ] A fallback screen recording or screenshots are prepared.
- [ ] Demo script was rehearsed once without backend errors.
- [ ] Project readiness is marked Ready in `project-status.md`.
