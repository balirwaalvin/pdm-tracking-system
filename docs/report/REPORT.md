# PDM Tracking System: an e-government service for the Parish Development Model

**Course:** MGT3151 E-Business, E-Commerce and E-Governance · **Lecturer:** Madam Brenda Lamwaka
**Institution:** Uganda Christian University, Faculty of Engineering, Design and Technology
**Group:** ten members (Appendix B): Nalweyiso Samalie Ruth, Balirwa Alvin Daniel, Kaitesi Lillian, Kabeho Samantha, Ssuubi Stephen, Kato Sharif Achen, Riak James Ngong, Kutosi Pius, Ogenrwot Churchill, Okello Emmanuel · **Date:** ______ Nov 2026

**Live prototype:** https://pdm-tracking-system.onrender.com · **Repository:** https://github.com/balirwaalvin/pdm-tracking-system (access given to the lecturer on request)

> **Draft.** Sections marked **[verify]** contain figures written from memory that must be checked against the cited source before submission. Each section names its owner, who checks it and must be able to defend it.

---

## Executive summary

*Owner: Okello Emmanuel*

The Parish Development Model (PDM) channels the Parish Revolving Fund to households through parish PDM SACCOs. Today most of the cycle — profiling, verification, applications, decisions, repayment and complaints — runs on paper registers and phone calls, so households cannot see where their application is, officials cannot see arrears early, and oversight bodies receive late, unverifiable reports.

We built a working **e-government (G2C, G2B and G2G) prototype** covering the whole cycle for every stakeholder, from the household and the LC I chairperson to the PDM Secretariat and auditors. Households use **USSD and SMS** on any phone, in English or Luganda; officials use a role-based web portal limited to their own area. Every change is logged for audit. The service is free at the point of use and has **no e-commerce features**.

The prototype runs live with fictitious data, passes **291 automated tests**, and meets WCAG 2 A/AA on the 14 pages checked.

## 1. Problem analysis (Phase 1)

*Owner: Kaitesi Lillian (01, 02) and Kabeho Samantha (03)* · Full detail: [design/01](../design/01-problem-and-stakeholders.md), [02](../design/02-process-models.md), [03](../design/03-feasibility-and-scope.md)

- **Context.** PDM is Uganda's main programme for moving subsistence households into the money economy, with about UGX 100 million a year for each parish's revolving fund **[verify: MoFPED 2022]**.
- **Problem.** Paper-based processing gives long and invisible waiting times, ghost or ineligible beneficiaries, unrecorded refusals, late repayment follow-up and complaints that never reach anyone with authority.
- **Current vs proposed process.** Swimlane diagrams in design/02 show the paper process and the digital one. The measured bottleneck is the time from application to decision, which we estimate falls from weeks to days (assumptions stated in design/02).
- **Stakeholders.** Ten roles, from household to auditor, with their needs and constraints.
- **Feasibility and scope.** Technical, economic, operational and legal feasibility; MVP scope and success measures in design/03.

## 2. Service design and model (Phase 2)

*Owner: Kabeho Samantha, Nalweyiso Samalie Ruth and Kutosi Pius* · Full detail: [design/04](../design/04-journey-map.md), [05](../design/05-service-model.md), [06](../design/06-personas-and-traceability.md)

- **Journey map.** Ten stages (register → oversee) with pain points, emotions and exceptions such as rejection, appeal, arrears and complaints.
- **Service model.** G2C (household status, complaints, appeals), G2B (SACCOs and enterprise groups) and G2G (parish → national reporting and fund releases), with a public-value canvas. It is funded by government and free to households.
- **Personas.** Florence (61, farmer, feature phone, Luganda), Ruth (34, SACCO manager) and David (45, district official).
- **Accessibility and inclusion.** USSD for feature phones, Luganda, plain language, and screen-reader labels.
- **Traceability.** Each need is traced to a feature and to the test that proves it (design/06).

## 3. Prototype (Phase 3)

*Owner: Riak James Ngong and Ssuubi Stephen (demo: Balirwa Alvin Daniel)* · Demo script: [DEMO.md](../DEMO.md) · Screenshots: [screenshots](../screenshots/README.md) · Tests: [design/07](../design/07-test-cases.md), [08](../design/08-usability-and-accessibility.md)

**Workflow implemented end to end:** check eligibility → register (Parish Chief, with a mock national ID check) → verify (LC I) → group (CDO) → apply (group executive) → appraise (SACCO) → decide (a second SACCO official, maker-checker) → disburse → repay (6% flat schedule, receipts, arrears, 90-day default) → check status (USSD, SMS) → complain or appeal (escalation after 7 days; appeal decided by the sub-county) → publish verified success stories → dashboards, quarterly report and audit trail.

| Evidence | Where |
| --- | --- |
| 13 documented test cases (7 positive, 3 validation, 3 access control), all passing | design/07 |
| 291 automated tests in GitHub Actions on every push | `.github/workflows/tests.yml` |
| Accessibility: axe-core WCAG 2 A/AA, 14 pages clean after one fix | design/08 |
| Responsive layout at phone width | screenshot 24 |

*Insert 6–8 screenshots here: home page by role, loan page with schedule, USSD in Luganda, dashboard, complaint escalation, appeal.*

## 4. Architecture, data and security (Phase 4)

*Owner: Ogenrwot Churchill and Kato Sharif Achen* · Full detail: [design/09](../design/09-architecture.md), [10](../design/10-data-design.md), [11](../design/11-security-privacy-continuity.md)

- **Architecture.** Web, USSD and SMS channels → a Django application with seven modules → PostgreSQL, on Render, with CI in GitHub Actions. Four trust boundaries are described in design/09.
- **Data.** An ERD of 17 entities with cardinalities; the NIN and phone number are unique; validation rules are listed; data is minimised (no photos, GPS or bank details); a retention proposal is given.
- **Security.** Least-privilege access policy, area scoping, maker-checker, account lockout, HTTPS with HSTS, CSRF protection and a full audit log. A STRIDE analysis covers 8 threats.
- **Continuity.** `pg_dump` backup and restore, a one-command reset of the sample data, and recovery targets for a real deployment.

## 5. Evaluation and lessons

*Owner: Okello Emmanuel*

| What worked | What we would change |
| --- | --- |
| One access-policy file made role checks consistent and testable | Test with real households and officials (think-aloud) before building more |
| Automated tests caught regressions on every change | A real USSD short code needs telco approval and costs; we used a simulator |
| USSD in Luganda reaches households without smartphones | Have the Luganda wording reviewed by a native speaker |
| The audit trail and maker-checker answer the main fraud risks | Integrate with NIRA and mobile money APIs instead of mocks |

**Limitations.** Fictitious data only. A mock identity register stands in for NIRA. The free hosting has no automatic backups and sleeps when idle. The system has not been piloted with real users.

## 6. Setup and reproducibility

Follow the [README](../../README.md): clone, copy `.env.example` to `.env`, then `pip install -r requirements.txt`, `python manage.py migrate`, `python manage.py seed_demo`, `python manage.py runserver`. Every demo account uses the password `pdm12345`. Run `python manage.py test` to repeat the 291 tests.

## References

*Owner: Okello Emmanuel. Check every entry, add access dates, and use one style (APA 7th) throughout.*

1. Ministry of Finance, Planning and Economic Development. (2022). *Parish Development Model: Implementation guidelines*. Kampala: MoFPED. **[verify title and year]**
2. Ministry of Finance, Planning and Economic Development. (2022). *Parish Revolving Fund operational guidelines*. **[verify]**
3. Republic of Uganda. (2019). *Data Protection and Privacy Act, 2019*.
4. National Information Technology Authority – Uganda. *E-Government interoperability / service standards*. **[verify exact document]**
5. United Nations Department of Economic and Social Affairs. (2024). *UN E-Government Survey 2024*. New York: United Nations.
6. Heeks, R. (2006). *Implementing and managing eGovernment: An international text*. London: SAGE.
7. Moore, M. H. (1995). *Creating public value: Strategic management in government*. Cambridge, MA: Harvard University Press.
8. Laudon, K. C., & Traver, C. G. (2023). *E-commerce: Business, technology, society* (18th ed.). Pearson. **[verify edition]**
9. W3C. (2018). *Web Content Accessibility Guidelines (WCAG) 2.1*. https://www.w3.org/TR/WCAG21/
10. OWASP Foundation. (2021). *OWASP Top 10: 2021*. https://owasp.org/Top10/
11. Shostack, A. (2014). *Threat modeling: Designing for security*. Indianapolis: Wiley.
12. Django Software Foundation. (2025). *Django documentation, version 5.2*. https://docs.djangoproject.com/en/5.2/

## Appendices

- **A.** [Use of generative AI](APPENDIX_A_AI_USE.md)
- **B.** [Role matrix](APPENDIX_B_ROLE_MATRIX.md)
- **C.** [Task log](APPENDIX_C_TASK_LOG.md)
- **D.** [Individual contribution statements](APPENDIX_D_CONTRIBUTIONS.md)
- [Team roles for the presentation and defence](TEAM_ROLES.md)
