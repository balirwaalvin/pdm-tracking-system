# 6. Personas, accessibility and traceability

*Phase 2 · User and stakeholder fit (4 marks)* · **Owner:** Kabeho Samantha · **Reviewed by:** Balirwa Alvin Daniel, Riak James Ngong (sign when checked)

## 6.1 Personas (fictitious)

### Florence Atim, 61, household head, Seeta Central

- Raises poultry on a small plot; household of five; has a disability (walks with a stick).
- Has a basic phone, no smartphone, no data bundle; reads Luganda better than English.
- **Goals:** a small loan for layer chickens; to know where her application is without walking to the office.
- **Frustrations:** walked to the parish office three times to ask about her file; was told a "facilitation fee" would speed it up.
- **Needs:** USSD in Luganda; SMS updates; a reason if refused; a safe way to report a bribe.

### Ruth Nabirye, 34, PDM SACCO official, Seeta

- Manages appraisals and repayments for about 400 member households with one assistant.
- Uses a laptop and a smartphone; good English.
- **Goals:** appraise fairly and quickly; see who is in arrears; show auditors a clean record.
- **Frustrations:** paper files; pressure from people she knows; arrears discovered late.
- **Needs:** scored appraisals; a second official to decide (so no one can accuse her); repayment schedules and an arrears list.

### David Ouma, 45, Sub-county Chief and CDO, Goma (third, optional)

- Supervises two parishes; handles complaints that the parish cannot resolve.
- **Needs:** to see problems across parishes; to decide appeals and bribery reports independently.

## 6.2 Accessibility considerations

| Need | How the prototype addresses it |
| --- | --- |
| No smartphone or data | USSD menu on any phone; SMS alerts |
| Language | Luganda and English on USSD, remembered per household |
| Low literacy | Short menus; plain words; status shown as badges and a progress bar |
| Disability or mobility | No need to travel to ask about status; the parish help desk can dial for a resident |
| Screen readers and keyboards | Labelled form fields, visible focus outline, `aria` labels on icons and charts (checks in section 8) |
| Small screens | Responsive layout; tested at phone width |

## 6.3 Traceability: need → feature → test

| Need (persona) | Feature | Where in the system | Test evidence |
| --- | --- | --- | --- |
| Know my status without travelling (Florence) | USSD, SMS alerts, My household | `ussd/menu.py`, `loans/notifications.py`, `/my-household/` | `ussd/tests.py` (every path), `LoanAlertTests` |
| Use my own language (Florence) | Luganda USSD | `ussd/texts.py` | `LugandaTests` |
| A reason for any refusal (Florence) | Required reasons; appeal | Decision form, `feedback/appeals.py` | `DecisionTests`, `AppealTests` |
| Report a bribe safely (Florence) | Bribery complaints start at the sub-county | `feedback/models.py` (starting level) | `test_bribery_complaints_skip_the_parish` |
| Know if I qualify (Florence) | Eligibility check and checklist | `/eligibility/`, `registry/eligibility.py` | `EligibilityTests` |
| Decide fairly and be protected (Ruth) | Maker-checker | `loans/workflow.py` | `MakerCheckerTests` |
| See arrears early (Ruth) | Schedule, arrears list, default flag | `loans/schedule.py`, `/loans/arrears/` | `RepaymentTests`, `DefaultTests` |
| A clean record for auditors (Ruth) | Audit log, sign-in log | `/audit/`, `/accounts/sign-ins/` | `AuditLogTests`, `SignInTests` |
| Independent review (David) | Appeals and escalations to the sub-county | `/complaints/appeals/`, `escalate_complaints` | `AppealTests`, `EscalationTests` |
| Only my own work and area (all) | Role-based access and area scoping | `accounts/access.py`, `accounts/scoping.py` | `AccessMatrixTests`, `CrossParishTests` |
