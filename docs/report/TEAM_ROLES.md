# Team roles for the presentation and defence

Each of the ten members has three things: a **segment to present** in the 12-minute slot, **documents they own** (and must be able to explain), and **questions to prepare** for the 8-minute defence. Each also backs up a neighbour, so that if one member is absent or stuck, the backup takes over.

**How the demo runs:** Alvin drives the laptop throughout, which keeps the clicks quick and avoids changing seats. Each member stands, says their lines, and tells Alvin what to click. Timings follow the [12-minute plan in DEMO.md](../DEMO.md).

A printable version of this page, with each member's script, screenshots, diagrams and model answers, is [PDM-Presentation-Briefing.pdf](PDM-Presentation-Briefing.pdf).

Names are from the team slide. Where possible, each member's segment is close to the slides they presented at the proposal stage (for example, Stephen presented the fund flow and now presents disbursement and repayment). The [role matrix](APPENDIX_B_ROLE_MATRIX.md) matches this page.

## Summary

| # | Member | Presents (time) | Owns | Backs up |
| --- | --- | --- | --- | --- |
| 1 | **Balirwa Alvin Daniel** | Introduction (team names, 15 s), drives the demo, answers the code questions | Prototype code, deployment, [DEMO.md](../DEMO.md) | everyone (demo) |
| 2 | **Kaitesi Lillian** | 0:00–1:00 Problem, stakeholders, process bottleneck | design/01, design/02 | 3 |
| 3 | **Ogenrwot Churchill** | 1:00–2:00 Architecture and security | design/09, design/11 §11.1 and §11.4 (backup) | 2 |
| 4 | **Kabeho Samantha** | 2:00–3:15 Eligibility check, ID check, LC I verification | design/03, design/06 (personas, traceability) | 5 |
| 5 | **Riak James Ngong** | 3:15–4:45 Loan application, appraisal, maker-checker | design/10 (ERD, validation rules) | 4 |
| 6 | **Ssuubi Stephen** | 4:45–6:15 Approval, disbursement, repayment, receipt | design/07 (test cases) | 7 |
| 7 | **Nalweyiso Samalie Ruth** | 6:15–7:30 Household view, USSD in Luganda | design/04 (journey map), design/08 (accessibility) | 6 |
| 8 | **Kutosi Pius** | 7:30–9:30 Appeal, complaints, bribery report | design/05 (service model, public value) | 9 |
| 9 | **Kato Sharif Achen** | 9:30–11:00 National dashboard, audit log | design/11 §11.2–11.3 (threats, privacy) | 8 |
| 10 | **Okello Emmanuel** | 11:00–12:00 Close: results, lessons, what is next | [REPORT.md](REPORT.md) (editor), references, Appendix A | 1 |

Every phase of the exam has at least two people who can defend it:

| Exam phase | Defended by |
| --- | --- |
| 1. Problem analysis | 2, 4 |
| 2. Service design and model | 4, 7, 8 |
| 3. Prototype and testing | 1, 5, 6, 7 |
| 4. Architecture, data and security | 3, 5, 9 |
| 5. Report and defence | 10, 1 |

---

## 1. Balirwa Alvin Daniel (M24B13/026): technical lead and demo driver

- **Presents:** introduces the team in 15 seconds, then drives every click. Steps in if any segment runs late. Follows the rule in DEMO.md: drop the appeal first, then the dashboard.
- **Before Thursday:** reset the demo data as `admin`; open the three signed-in windows (`saccochair`, `florence`, `national`); open the site 5 minutes early so it wakes up.
- **Prepare to answer:**
  - How is the code organised? (Seven Django apps; `accounts/access.py` decides who can do what; `loans/workflow.py` is the only place a loan's status changes.)
  - How did you use AI? (Appendix A. Be open about it, and explain one part of the code in your own words.)
  - How is it deployed? (Render Blueprint; every push to `main` runs 291 tests in GitHub Actions and redeploys.)

## 2. Problem and process: Kaitesi Lillian (S24B13/045)

- **Presents (0:00–1:00):** *PDM loans are tracked on paper across ten offices. Households cannot see where their application is, and complaints have no trail.* Shows the current process with its bottleneck, then the proposed one.
- **Owns:** design/01 (problem, evidence, stakeholders) and design/02 (process diagrams).
- **Must do:** check the [verify] figures in design/01 against the MoFPED guidelines.
- **Prepare to answer:**
  - What evidence is there of the problem?
  - What exactly is the bottleneck, and how did you measure it?
  - Who are the stakeholders, and which one matters most? (The household.)

## 3. Architecture and security: Ogenrwot Churchill (M24B13/028)

- **Presents (1:00–2:00):** the architecture slide: *Django and PostgreSQL on Render, HTTPS, role-based access, an audit trail; USSD for phones without data.*
- **Owns:** design/09; design/11 controls (§11.1) and backup (§11.4).
- **Must do:** take a backup of the live database with `pg_dump` before Thursday (Alvin gives you the database URL privately; never put it in a document).
- **Prepare to answer:**
  - Where are the trust boundaries?
  - What happens if the database is lost? (Backup and restore, plus a reset of the sample data.)
  - Why server-rendered pages and not a mobile app? (Feature phones use USSD; one codebase.)
  - How do the pages work on a phone?

## 4. Eligibility and verification: Kabeho Samantha (M24B13/027)

- **Presents (2:00–3:15):** the signed-out eligibility check (*any citizen can check without giving personal data*); then `lc1` confirms a household, pointing at the mock ID check.
- **Owns:** design/03 (feasibility and scope) and design/06 (personas, traceability).
- **Prepare to answer:**
  - How do you stop ghost beneficiaries? (A unique NIN, an ID check, and LC I confirmation; a rejection needs a reason.)
  - Is it feasible: cost, skills, connectivity?
  - Trace one need (for example "Florence wants to know her loan status") to its feature and its test.

## 5. Loan application and appraisal: Riak James Ngong (M24B13/052)

- **Presents (3:15–4:45):** `groupexec` applies for Florence (UGX 600,000) and submits it; `sacco` appraises it (4, 4, 4, approve) and the maker-checker note appears.
- **Owns:** design/10 (ERD, identifiers, validation rules, retention).
- **Prepare to answer:**
  - What stops a loan above UGX 1 million, or a second open loan? (Validation rules.)
  - What is maker-checker, and why does it matter? (One official cannot both appraise and approve.)
  - Explain the ERD: why one SACCO per parish, and one appraisal per loan?
  - What data do you deliberately not collect?

## 6. Decision, disbursement and repayment: Ssuubi Stephen (M24B13/007)

- **Presents (4:45–6:15):** `saccochair` approves, records the disbursement, records a repayment of 53,000 and opens the receipt: *A second official decides; the household gets an SMS at each step.*
- **Owns:** design/07 (the 13 test cases).
- **Must do:** re-run the 13 tests (Alvin shows you the command) and write the date and your name in design/07.
- **Prepare to answer:**
  - How is the schedule worked out? (6% a year, flat, over the term; 600,000 over 12 months gives instalments of about 53,000.)
  - What happens when someone stops paying? (Arrears list; default after 90 days.)
  - Can a SACCO pay out more than it received? (No: disbursement is capped by the confirmed releases.)
  - Show us a test that fails if the rule is broken.

## 7. The household's view and USSD: Nalweyiso Samalie Ruth (M24B13/006)

- **Presents (6:15–7:30):** the `florence` window: loan, schedule, receipt and SMS alerts; then USSD → Dial → `2` → `0` for Luganda: *the same information on any phone.*
- **Owns:** design/04 (journey map) and design/08 (usability and accessibility).
- **Must do:** run the two-person think-aloud test in design/08 and record what you find. Get consent first, and record no personal data.
- **Prepare to answer:**
  - How do households without smartphones or data take part?
  - How did you check accessibility? (axe-core found one problem; it was fixed and all 14 pages passed.)
  - Why the simulator and not a real USSD code? (A real code needs telco approval and costs money; the simulator follows the Africa's Talking format.)
  - Where in the journey are the pain points?

## 8. Citizen voice: appeals and complaints: Kutosi Pius (S25B13/089)

- **Presents (7:30–9:30):** `sylvia` appeals her rejected loan; `subcounty` refers it back to the SACCO, then opens the bribery report that skipped the parish: *Appeals and bribery reports go to the sub-county, away from the officials involved.*
- **Owns:** design/05 (service model: G2C, G2B, G2G and public value). Also explains the success stories and the public parish pages.
- **Prepare to answer:**
  - Why is this e-governance and not e-commerce? (No buying or selling, no fees; the service is free to households.)
  - What happens if nobody answers a complaint? (It moves up a level after 7 days.)
  - Who funds the service, and where is the public value?
  - How is the household's consent recorded for a success story?

## 9. Oversight and audit: Kato Sharif Achen (M24B13/046)

- **Presents (9:30–11:00):** the `national` dashboard (two districts, portfolio at risk), then the `auditor` searching the audit log for *Florence*: *the auditor reads everything and changes nothing.*
- **Owns:** design/11 threat analysis (§11.2) and privacy (§11.3).
- **Prepare to answer:**
  - Name three threats and how the system stops them.
  - Can a Parish Chief see another parish's records? (No; it was tested, TC12.)
  - What does the audit log record? (Who, what, before and after, and when.)
  - What happens after 5 wrong passwords? (The account locks for 15 minutes, and the attempts appear in the sign-in log.)

## 10. Close and report: Okello Emmanuel (M24B13/017)

- **Presents (11:00–12:00):** results (*291 automated tests; every role sees only its own work; sample data only*), the main lessons, and what comes next (a NIRA link, mobile money, a pilot).
- **Owns:** REPORT.md as editor (gathers each owner's section), the references, and Appendix A (AI declaration). Collects every member's contribution statement (Appendix D).
- **Must do:** check that every [verify] has been replaced with a cited source; put the report into the required format.
- **Prepare to answer:**
  - What are the limitations?
  - What would you do differently?
  - How did the group divide the work? (Point to the role matrix and the task log.)

---

## Rehearsal checklist

- [ ] Each member has said their lines out loud with the timer running.
- [ ] One full run-through on the live site, timed under 12 minutes.
- [ ] Each backup knows their partner's segment.
- [ ] Each member has read their documents and can answer the questions above without notes.
