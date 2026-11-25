# Demo script: the PDM customer journey

For the presentation on **Thu 26 Nov 2026**. About **15 minutes**. One household, **Florence Atim** of Seeta Central village, goes through the whole journey live; the sample data covers the rest.

Live site: **https://pdm.treez.tech** · every password is **`pdm12345`**. To see the account list on the sign-in page, open **https://pdm.treez.tech/accounts/login/?demo** (it is hidden otherwise, so the portal looks like a real one).

## Before you start (15 minutes before)

1. Sign in as **`admin`**, open the user menu (top right) → **Reset demo data**, type `RESET`. On the live site this takes 30 to 40 seconds; wait for the green message and do not click twice. It puts every record back to the starting state below, with loan and complaint numbers starting at 1.
2. Sign out. The keep-awake ping keeps the site warm on 25 and 26 Nov; if it was asleep, the first page takes about 50 seconds, so do this early.
3. Use a private (incognito) window for the demo, so you can sign out and in quickly. Zoom the browser to 110–125% for the projector.
4. Have the local copy ready as a fallback (`python manage.py runserver`, then http://127.0.0.1:8000).

If a password is mistyped five times, that account locks for 15 minutes. Use another account for the same role (for example `saccochair` instead of `sacco`), or reset the demo.

## The starting state after a reset

| Record | State |
| --- | --- |
| Florence Atim (Seeta Central, Seeta Poultry Farmers) | Waiting for LC I verification, no loan |
| Loan 1: Grace Nakato, UGX 800,000 | Appraised by `sacco`, waiting for a second official to decide |
| Loan 3: Ronald Lubega, UGX 700,000 | Approved, waiting to be paid out |
| Loan 6: Henry Mubiru | Repaying, in arrears |
| Loan 7: Joyce Nalwoga | Defaulted (90+ days overdue) |
| Complaints PDM-000001 to PDM-000005 | Open, being handled, resolved, escalated, and a bribery report |
| Story "A sty built by the group" (Ronald) | Waiting for the PDC's check |
| Fund release 2026/27, UGX 50,000,000 | Recorded by the national office, not yet confirmed by the district |

## The journey

### 0. Opening (1 min): signed out

- Open **pdm.treez.tech**. Point out the ten stages on the landing page: this is the journey you will show.
- Click **See your parish** → **Seeta parish**. Say: *anyone can see these figures without signing in; there are no names or NINs, and only stories the PDC has checked.*

### 1. Register (1 min): `parishchief`

- Sign in. Point out the **workspace**: only this role's work, counted live ("Households waiting for LC I", "Complaints for your office").
- **Households → Register a household**. Type Grace's NIN, `CF85001234ABCD`, and save: the system refuses a duplicate NIN and names the household that has it. Cancel.
- Say: *the Parish Chief profiles households; the NIN and the phone number must be unique.*

### 2. Verify (1 min): `lc1`

- Sign in. The workspace shows **1 household waiting for you to verify**. Click it.
- Open **Florence Atim** → **Confirm household**. Say: *the LC I can only see and verify households in his own village; a rejection needs a reason.*

### 3. Group (30 s): `subcounty`

- **Groups**: show that Seeta Poultry Farmers is linked to Seeta PDM SACCO. Say: *when the CDO registers a group, the system links it to its parish SACCO automatically.*

### 4. Apply (1 min): `groupexec`

- **Loans → New application**: household **Florence Atim**, amount `600000`, enterprise `Layer chickens`, a one-line plan, term `12`. Save, then **Submit to the SACCO**.
- Say: *only verified members can be chosen, the ceiling is UGX 1,000,000, and one open loan per household.* Point at the progress bar: **Submitted**.

### 5. Appraise (1 min): `sacco` (Ruth)

- The workspace shows **Applications to appraise**. Open Florence's loan → **Appraise**: scores 4, 4, 4, recommend **Approve**, a reason. Save.
- Notice the decision form is **not** offered: *"you appraised this loan, so another SACCO official must decide."*

### 6. Decide and pay out (1.5 min): `saccochair` (Josephine), then `sacco`

- Sign in as **`saccochair`**. Open Florence's loan → **Approve** → **Record decision**. Say: *maker-checker, a second official decides; the system refuses the appraiser.*
- Still as `saccochair` (any SACCO official can pay out): **Record disbursement** → amount `600000`, today, mobile money, reference `DEMO-001`.
- Point out **SMS alerts to the household**: the approval and payout texts. The progress bar now shows **Paid out**.

### 7. Repay (1 min): same account

- **Record repayment**: `53000`, today, cash, receipt reference `R-001`. The loan moves to **Repaying** by itself; the schedule marks instalment 1 as paid; open the **receipt** (RCPT number).
- Then **Arrears** in the menu: Henry and Joyce. Say: *the system flags defaults at 90 days overdue.*

### 8. Check by USSD (2 min): `household`, then `parishchief`

- Start with the household's own view: sign in as **`household`** (Grace) → **USSD** → **Dial** → `2`. She can only dial with her own number. Say: *the household is the main stakeholder; this is what they see on any phone.*
- Then as **`parishchief`**, the **USSD help desk**: dial as **Florence Atim** → `2` (My loan): balance and next instalment.
- Dial again → `0` switches to **Luganda** → `2` again. Say: *any phone, no data needed, free; the language is remembered.*
- Dial again → `3` Report a problem → `5` *Asked for a bribe* → type `Someone asked me for 20000`. Note the reference (**PDM-000006**). Say: *bribery reports skip the parish and go straight to the sub-county.*

### 9. Speak up (2 min): `subcounty`, then `pdc`

- As **`subcounty`**: **Complaints** → PDM-000006 → respond *Resolved* with a short message (the household gets an SMS). Show **PDM-000004**: it went up from the parish because nobody resolved it in 7 days.
- As **`pdc`**: the workspace shows **Success stories to check**. Open Ronald's story: the household's records sit beside the story. Tick *I checked this story against the household's records* → **Approve and publish**.
- Sign out and open **Parish pages → Seeta**: the new story is public, and Ronald is shown only as "Ronald of Bajjo" because he did not agree to be named.

### 10. Oversee (2 min): `district`, `national`, `auditor`

- As **`district`**: **SACCOs → Seeta PDM SACCO** → confirm the 2026/27 release of UGX 50,000,000.
- As **`national`**: **Dashboard**: two districts compared, portfolio at risk, charts. **Reports**: the quarterly report, *Print or save as PDF*.
- As **`auditor`**: **Audit log**, search `Florence`: every step today, with the name of the official who did it. **Sign-ins**: every sign-in, including failed ones. Say: *the auditor can read everything and change nothing.*

### Closing (30 s)

- Back on any workspace: *each of the ten roles sees only its own work in its own area; 264 automated tests check this on every change.*

## Rehearsal record

- **Mon 23 Nov 2026, live site:** the whole script was run in a browser on https://pdm.treez.tech, from a reset, every step clicked as written above. All ten stages passed. Pages answered in 1 to 2 seconds; a reset took about 35 seconds; the first visit after a sleep took about 33 seconds. The demo was reset again afterwards. Screenshots: [screenshots/](screenshots/).
- The same script also runs as an automated test (`dashboards/test_demo_script.py`) on every push.

## Likely questions

- **Is it free for households?** Yes. No fees, no payments through the system; it tracks the government's Parish Revolving Fund.
- **What if someone has no smartphone?** USSD works on any phone, in English or Luganda.
- **What stops a SACCO official approving their own friend's loan?** Maker-checker: the appraiser cannot decide, and every decision is in the audit log with a name.
- **Is the data real?** No. Sample people, NINs and phone numbers only; the site says so on every page.
