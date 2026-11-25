# 3. Feasibility and MVP scope

*Phase 1 · Feasibility and scope (6 marks)* · **Owner:** ______________ · **Reviewed by:** ______________

## 3.1 MVP scope (bounded)

**In scope:** one district with one sub-county and two parishes (plus a second district for comparison), ten roles, and the full loan cycle:
- eligibility check
- profiling with a mock identity check
- LC I verification
- group application
- appraisal and the maker-checker decision
- payout and repayments
- arrears and 90-day default
- SMS (simulated) and USSD
- complaints with escalation, appeals and success stories
- dashboards, reports, audit trail and public parish pages

**Out of scope:** real payments or mobile money integration; a real NIRA identity link; a live USSD short code (it needs a telecom contract); offline mobile apps; integration with IFMS; monitoring visits with photos.

## 3.2 Assumptions

- Officials have a phone or computer with occasional internet; households need only a basic phone (USSD).
- The PRF rules used are a ceiling of UGX 1,000,000, 6% a year flat, a term of 3 to 24 months and default at 90 days overdue **[verify against the PRF guidelines]**.
- All data is fictitious; the identity check uses a mock register.

## 3.3 Feasibility

| Dimension | Assessment |
| --- | --- |
| **Technical** | Feasible. A standard web stack (Django 5.2, PostgreSQL 16, Bootstrap) built and deployed by one developer in 10 days; USSD and SMS through Africa's Talking (code ready; sandbox optional). 291 automated tests pass. |
| **Operational** | Feasible with training. Screens follow the roles people already have; each user sees only their own work. USSD and Luganda serve households without smartphones. A help desk at the parish (the USSD help-desk screen) supports those who struggle. |
| **Economic** | Low cost. The prototype runs on free tiers. A national deployment would need hosting (estimate **UGX 2–5 million a month [estimate]**), a USSD short code and SMS (about **UGX 30 per SMS [verify with providers]**), and training. This is small next to the fund (about UGX 1 trillion a year across all parishes **[verify]**). |
| **Schedule** | Feasible. The prototype was built from 17 to 25 November 2026 following a day-by-day plan (`docs/PROGRESS.md`, `docs/ROADMAP.md`). A pilot in one district could follow in about three months. |

## 3.4 Success measures

| Measure | Baseline (current) | Target | How the prototype measures it |
| --- | --- | --- | --- |
| Time from submission to decision | 3–6 weeks [assumption] | Under 7 days | `submitted_at` and `decided_at` on each loan |
| Refusals with a written reason | Under 50% [assumption] | 100% | Enforced by the form; checked in tests |
| Household trips to ask about status | 2–4 [assumption] | 0 (USSD and SMS) | SMS log; USSD sessions |
| Complaints answered within 7 days | Not recorded | Over 80% | Complaint dates; escalation count |
| Decisions made by someone other than the appraiser | Not enforced | 100% | Maker-checker rule; audit log |
| Arrears visible to the ministry | Quarterly, on paper | Daily | Dashboard, portfolio at risk |
