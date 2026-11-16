# Progress

The day-by-day plan for the PDM Tracking System prototype. Each item is ticked in the commit that finishes it.

Day 1 was Tue 17 Nov 2026; Day 10 is Thu 26 Nov 2026; the buffer runs to Mon 30 Nov 2026.

## Days 1–4: foundations (done)

- [x] Project setup, settings from the environment, Render blueprint and CI
- [x] Ten PDM roles, the user model and area scoping
- [x] Registry: administrative units, enterprise groups and households
- [x] Household verification by the LC I chairperson
- [x] SACCOs: eligibility checklist and fund releases
- [x] Loan applications, the workflow rules and appraisal
- [x] Demo data (`seed_demo`) and 51 tests

## Day 5: loan decisions

- [x] Approve, and reject with reasons. Only the SACCO official may decide, and only from APPRAISED. A rejection reason is required. Use `move()`.
- [x] Disbursement record: a model with amount, date, method and reference, recorded by the SACCO official. It moves the loan APPROVED → DISBURSED and must not exceed the approved amount or the SACCO's confirmed releases.
- [x] Finish the tests for the loan workflow: approve, reject, disburse, wrong role and wrong status.

## Day 6: repayment

- [ ] Repayment schedule at 6% a year over `term_months`. Show the instalments on the loan page.
- [ ] Record repayments, which moves the loan DISBURSED → REPAYING → CLOSED through SYSTEM changes. Add an arrears list.
- [ ] 90-day default flag: a management command, such as `flag_defaults`, that moves loans to DEFAULTED.
- [ ] Tests for interest, the schedule and default.

## Day 7: USSD and SMS (Africa's Talking sandbox)

- [ ] USSD callback view in `ussd` (CSRF-exempt POST with `sessionId`, `phoneNumber` and `text`) and the menu flow.
- [ ] USSD menus: "My PDM status" and "My loan", with the household found by phone number.
- [ ] SMS alerts on approval, disbursement and repayment. Wrap them in one service function, and log rather than crash when there are no keys.
- [ ] Test every USSD path with the Django test client. Use the simulator when the sandbox exists.

## Day 8: dashboards and audit

- [ ] Dashboard queries for each level, from parish to national, scoped by `scope_unit_ids()`.
- [ ] Dashboard page with totals and Chart.js charts from a CDN.
- [ ] Audit log page for the auditor role (read-only).

## Day 9: citizen voice (Should)

- [ ] Complaints by USSD with a reference number, in the `feedback` app.
- [ ] Complaint list and response page.
- [ ] Success stories: a Parish Chief or CDO drafts a story, the PDC checks it against the household's records and approves it, and the household's consent is recorded. Only approved stories are shown.
- [ ] Public parish page with no login: anonymised totals and approved stories.

## Day 10: finish

- [ ] Walk through the system as each of the ten roles.
- [ ] Security check: logged-out access and cross-parish access must be refused.
- [ ] Fix the bugs found.
- [ ] Final seed data and deploy.
- [ ] Write a demo script (`docs/DEMO.md`) that follows the customer journey.

## Days 11–14: buffer (Should and Could)

- [ ] Short user guide.
- [ ] Project report.
- [ ] Automatic complaint escalation.
- [ ] Monitoring visits with photos and GPS.
- [ ] Quarterly report export as PDF and CSV.
