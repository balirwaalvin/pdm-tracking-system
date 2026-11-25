# User guide

A short guide for each PDM role. Sign in at **https://pdm.treez.tech** with the account your office gave you. Your **workspace** (the first page after signing in) lists the work waiting for you, with live counts; click a card to go straight to it. The menu on the left shows only the pages your role can open, and you only ever see records in your own area.

Prototype with sample data only: the demo accounts all use the password `pdm12345`.

**Everyone:** change your password from the menu under your name (top right). Your workspace shows your previous sign-in; if it was not you, change your password. After 5 wrong passwords in 15 minutes an account locks for 15 minutes. You are signed out after 30 minutes without activity.

---

## Household (demo: `household`)

- **My household** shows your record, whether your LC I has verified you, your enterprise group and SACCO, your loan, the repayment schedule, receipts and the SMS alerts sent to you.
- **Raise a complaint** if something is wrong with your PDM service. You get a reference number by SMS. If nobody resolves it in 7 days, it goes to the next office up.
- **USSD** in the menu shows the PDM phone menu with your own number: the same one you reach by dialling the PDM USSD code on any phone. 1 status, 2 loan, 3 report a problem, 4 track a complaint, 0 Luganda or English.
- PDM services are free. Report anyone who asks you for money (option 3, then 5).

## LC I Chairperson (demo: `lc1`)

- **Households** lists the households in your village. Open one that is *Waiting for LC I* and choose **Confirm household** or **Reject**. A rejection needs a reason, which the household can see.
- **USSD** lets you try the household menu, to help residents who ask.

## Enterprise group executive (demo: `groupexec`)

- **Loans → New application**: choose a verified member of your group, the amount (UGX 10,000 to 1,000,000), the enterprise, a short plan and the term (3 to 24 months). Save it as a draft, check it, then **Submit to the SACCO**.
- A household can have only one open loan. Follow each application on its page; the progress bar shows where it is.

## Parish Chief (demo: `parishchief`)

- **Households → Register a household**: the NIN must be 14 letters and digits and not already registered; the phone number must be unique, because USSD and SMS find households by it.
- **Complaints**: answer complaints that are with the parish office. Choose *Being handled* (the 7-day clock restarts) or *Resolved*. The household gets your message by SMS.
- **Stories → Draft a story**: write up a household's success, read it back to them and record how they consented and whether they may be named. Then **Submit to the PDC**.
- **Dashboard**, **Loans** and **Arrears** show progress in your parish.

## Parish Development Committee (demo: `pdc`)

- **Stories**: open a story *Waiting for the PDC*. The household's records are shown beside it. Check them, tick the box to confirm, and **Approve and publish**, or send it back with a reason.
- **Dashboard**, **Loans**, **Arrears** and **Complaints** let you oversee PDM in the parish.

## PDM SACCO official (demo: `sacco` appraises, `saccochair` decides)

- **SACCOs**: tick the eligibility checklist. The SACCO can receive the fund only when every requirement is met.
- **Loans**: open a *Submitted* application → **Appraise** (three scores of 1 to 5, a recommendation and reasons).
- **Decide**: an appraised loan must be approved or rejected by **a different SACCO official** (maker-checker). A rejection needs a reason.
- **Record disbursement** when the money is paid out (not more than approved, nor more than the SACCO's confirmed funds). **Record repayment** for each payment; the household gets an SMS with the receipt number, and the loan closes when fully repaid.
- **Arrears** lists overdue loans; a loan is flagged as defaulted at 90 days overdue.

## Sub-county Chief and CDO (demo: `subcounty`)

- **Groups → Register a group**: it is linked automatically to its parish's PDM SACCO.
- **Complaints**: answer complaints with the sub-county office, including bribery reports (they come straight to you) and complaints escalated from the parish.
- **Stories**, **Dashboard**, **Reports** and **USSD** as for the parish, across your sub-county.

## District official (demo: `district`)

- **SACCOs**: confirm each fund release once the money reaches the SACCO's account.
- **Complaints**: answer complaints escalated to the district.
- **Dashboard** and **Reports** (quarterly, printable to PDF) for the district, with CSV downloads.

## PDM Secretariat and MoFPED (demo: `national`)

- **SACCOs**: record fund releases to eligible SACCOs (refused if a SACCO is not eligible).
- **Dashboard** and **Reports** compare districts; loans, arrears and complaints are readable nationally. Household records with NINs stay with the parish and sub-county.

## Auditor (demo: `auditor`)

- **Audit log**: every change to every record, who made it and when, with filters and a CSV download. **Sign-ins**: every sign-in attempt, including failed ones.
- You can read every record in the country and change nothing.

---

## Administrator (demo: `admin`)

- **Reset demo data** (menu under your name): puts the sample data back to its starting state before a rehearsal. It deletes everything done during demos, including the audit trail, so it is for sample data only.
- The Django admin is at `/admin/`.
