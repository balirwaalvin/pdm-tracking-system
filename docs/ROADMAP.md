# Roadmap to the presentation (revised 17 Nov 2026)

The final presentation is on **Thu 26 Nov 2026**, so the old buffer (27–30 Nov) no longer exists. This roadmap replaces Days 9–14 of `PROGRESS.md` from today. Days 1–8 are done.

**Must** items make the demo work. **Should** items make it stronger. **Could** items happen only if a day finishes early. If time runs short, cut Could, then Should, never Must.

## Wed 18 Nov: citizen voice, part 1 (Must)

- [x] Complaints in the `feedback` app: category, description, reference number (for example `PDM-2611-0042`), status (open, in progress, resolved) and responses.
- [x] Raise a complaint by USSD (new option "3. Report a problem") and from the household's "My household" page. Send an SMS with the reference number.
- [x] Complaint list and response page for the officials who handle them (Parish Chief, then sub-county CDO, then district), scoped to their area.
- [x] Automatic escalation (moved up from the buffer): a complaint not answered in 7 days moves up one level. It runs in the same daily job as `flag_defaults`.
- [x] Track a complaint by its reference number on USSD.

## Thu 19 Nov: citizen voice, part 2 (Must)

- [x] Success stories: the Parish Chief or CDO drafts one, the household's consent is recorded, and the PDC checks it against the household's records and approves or rejects it. Only approved stories are shown.
- [x] Public parish page with no login: anonymised totals (households, loans paid out, repayment rate) and approved stories, with no names or NINs unless consent covers them.
- [x] Open data download: a CSV of anonymised parish totals for the public page. *(Should)*

## Fri 20 Nov: governance and IAM hardening (Should, new)

Found during development.

- [x] **Maker-checker on loans.** The official who appraised a loan cannot also approve it. Add a second SACCO demo user (the SACCO Board chair) to approve.
- [x] **Unique household phone numbers.** USSD and SMS find a household by phone, so a duplicate would expose another household's loan.
- [x] **Sign-in log for the auditor.** Record successful and failed sign-ins, with time and address, next to the audit log.
- [x] **Password change page** for every user, and sessions that end after 30 minutes idle.

## Sat 21 Nov: reporting (Should)

- [x] CSV exports, scoped to the user's area: households, loans, arrears and complaints.
- [x] Quarterly report page for district and national officials (figures for the quarter, printable to PDF from the browser). This replaces "quarterly report export as PDF and CSV".
- [x] Second sample district in the seed, so the national dashboard compares more than one district.

## Sun 22 Nov: slack day (Could)

Use it for whatever slipped. Otherwise:

- [x] USSD menu in Luganda as well as English (language choice on the first screen). This shows inclusion for households who do not read English.
- [x] Repayment receipts: a numbered receipt page for each repayment, printable from the browser.

## Mon 23 Nov: walkthrough and security (Must)

Results: [SECURITY_CHECK.md](SECURITY_CHECK.md).

- [x] Walk through the system as each of the ten roles, following the customer journey.
- [x] Security check: logged-out access, cross-parish access, wrong-role posts, CSRF on every form, and production settings (`DEBUG=False`, secure cookies, HTTPS redirect).
- [x] Fix the bugs found.

## Tue 24 Nov: demo readiness (Must)

- [x] `reset_demo` command that puts the sample data back to its starting state before each rehearsal and the presentation.
- [x] Keep-awake ping: a scheduled GitHub Action that opens the site every 10 minutes on presentation day, so Render's free instance does not sleep.
- [x] Final seed data and deploy.
- [x] Demo script (`docs/DEMO.md`) following the ten-stage customer journey, with the account to use at each step.
- [x] Short user guide, one page per role. *(Should)*

## Wed 25 Nov: rehearsal and code freeze (Must)

- [x] Full rehearsal on the live site, timed (see the rehearsal record in DEMO.md).
- [x] Update the project report and take screenshots for the slides ([screenshots/](screenshots/)).
- [x] Code freeze: the rehearsed build is commit `8ffa07e` on `main` (23 Nov 2026); tag it `v1.0-presentation` on GitHub (Releases → Draft a new release → new tag on that commit). From now until the presentation, change only what is broken in the demo or the Luganda wording, and run the tests before every push.
  - If a late change goes wrong, go back to the rehearsed build: in the Render dashboard open the deploy for commit `8ffa07e` and choose **Rollback**, or run `git revert` on the bad commit and push.

## Thu 26 Nov: presentation

- [ ] `reset_demo` in the morning, then open https://pdm.treez.tech a few minutes before presenting.

## Dropped, with reasons

- **Monitoring visits with photos and GPS.** Render's free tier keeps no uploaded files across deploys, so the photos would disappear, and doing this properly needs paid storage. Mention it as future work.
- **Africa's Talking sandbox.** We decided to demonstrate USSD and SMS on our own simulator. The callback is ready if the sandbox is added later.
- **Long written project report.** Replaced by the project report page and the demo script. Write a short version only if the course requires it.
