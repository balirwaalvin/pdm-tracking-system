# CLAUDE.md: PDM Tracking System

You are continuing development of the **PDM Tracking System** (Parish Development Model Tracking System). It is a working Django prototype that is already in a GitHub repository and deployed. Read this whole brief at the start of every session. On the first session, follow the "First steps" section.

## 1. Who I am and what this is

- I am **Balirwa Alvin Daniel** (GitHub: `balirwaalvin`). I am a BSIT Year 3 student at Uganda Christian University (UCU), Faculty of Engineering, Design & Technology.
- This is the end-of-unit group project for the course unit **E-Commerce, E-Business & E-Governance**. The lecturer is **Madam Brenda Lamwaka**.
- The group has ten members, but **I am building the prototype alone**.
- **Deadline:** a functional prototype within **10 days, 14 at most**. Day 1 was Tue 17 Nov 2026, Day 10 is Thu 26 Nov 2026, and the buffer runs to Mon 30 Nov 2026. Days 1–4 are done and Day 5 is part done.
- The idea has been presented and approved. The supervisor asked us to add **verified success stories**, which are in scope.

## 2. Scope rules (from the lecturer: do not break these)

- **This is e-governance only.** It covers the whole PDM and every stakeholder, from village to ministry: households, LC I chairpersons, enterprise groups, Parish Chiefs, Parish Development Committees (PDCs), PDM SACCOs, sub-county and district officials, the national PDM Secretariat and MoFPED, and auditors.
- **No e-commerce features:** no marketplace, no buying or selling, no farmer-to-buyer trading, and no payment gateway.
- It is free at the point of use. **Never charge households or charge per transaction.**
- It is a prototype with **sample data only**: no real people, no real NINs, no real phone numbers. The site already shows a notice that it is a prototype and not an official government system. Keep it.

## 3. Repository, deploy and environment

- **Repo:** https://github.com/balirwaalvin/pdm-tracking-system (private). It has 84 commits so far, and the branch is `main`.
- **Live site:** https://pdm-tracking-system.onrender.com, on Render's free tier.
  - Render deploys from `render.yaml` as a Blueprint: one web service, `pdm-tracking-system`, and one free PostgreSQL database, `pdm-tracker-db`.
  - `build.sh` runs `pip install`, `collectstatic`, `migrate` and `seed_demo` on every deploy.
  - **Every push to `main` redeploys automatically.**
  - The free instance sleeps when idle, so the first request can take about 50 seconds.
- **CI:** GitHub Actions (`.github/workflows/tests.yml`) runs `manage.py check` and `manage.py test` against a Postgres 16 service on every push and pull request. Keep CI green.
- **Git identity.** My GitHub email is private, so pushes made with a real email are rejected (error GH007). Use exactly:
  ```
  git config user.name "Balirwa Alvin Daniel"
  git config user.email "159263723+balirwaalvin@users.noreply.github.com"
  ```
- **Local setup:**
  1. Copy `.env.example` to `.env`. Set `DEBUG=True`, a `SECRET_KEY`, `ALLOWED_HOSTS=localhost,127.0.0.1`, and `DATABASE_URL=postgres://<user>:<password>@localhost:5432/pdm_tracker`.
  2. Create the `pdm_tracker` database in PostgreSQL.
  3. Run `pip install -r requirements.txt`, then `python manage.py migrate`, then `python manage.py seed_demo`, then `python manage.py runserver`.
  4. Africa's Talking variables (`AT_USERNAME=sandbox`, `AT_API_KEY`, `AT_SENDER_ID`) are needed only from Day 7. I still have to create the sandbox account. **Never commit `.env` or any key.**

## 4. Stack and conventions

- **Python and Django:** Python 3.12, Django 5.2, server-rendered templates, and Bootstrap 5.3.3 from a CDN. No React or SPA.
- **Packages:**
  - forms: `django-crispy-forms` and `crispy-bootstrap5`
  - audit trail: `django-auditlog`
  - static files: `whitenoise` with `CompressedStaticFilesStorage`. Do not use the Manifest variant, which breaks tests.
  - config and server: `dj-database-url`, `python-dotenv`, `gunicorn`, `psycopg[binary]`
  - USSD and SMS: `africastalking`
- **Settings:** values come from the environment (SECRET_KEY, DEBUG, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, DATABASE_URL). `AUTH_USER_MODEL = "accounts.User"`, `TIME_ZONE = "Africa/Kampala"` and `LANGUAGE_CODE = "en-gb"`. Login redirects to `home` and logout to `login`.
- **Apps:** `accounts`, `registry`, `saccos`, `loans`, `feedback`, `dashboards`, `ussd`.
  - `feedback` and `ussd` are still empty stubs.
  - `dashboards` has only `HomeView` at `""`, named `home`.
- **URL namespaces:** `registry:`, `saccos:`, `loans:` and `accounts/`.
  - Project templates are in `templates/`: `base.html`, `403.html`, `404.html`, `_pagination.html` and `registration/login.html`.
  - App templates are in `<app>/templates/<app>/`.
  - Static CSS is in `static/css/app.css`.
- **Every model is registered with auditlog.** Do the same for new models. On the User model, exclude `password` and `last_login`.
- **Code style:** plain and readable. Each module gets a short docstring saying what it is for. Write clear user-facing messages in British English.
- **Testing:** use `HTTP_HOST="localhost"` in test clients and smoke tests.

## 5. What exists (Days 1–4 done, Day 5 part done)

- **Roles** (`accounts/roles.py`) are ten Django Groups, created by migration `accounts/0002`:
  - `HOUSEHOLD`
  - `GROUP_EXECUTIVE` ("Enterprise group executive")
  - `LC1_CHAIRPERSON`
  - `PARISH_CHIEF`
  - `PDC`
  - `SACCO_OFFICIAL` ("PDM SACCO official")
  - `SUBCOUNTY_OFFICIAL` ("Sub-county Chief and CDO")
  - `DISTRICT_OFFICIAL`
  - `NATIONAL_OFFICIAL` ("PDM Secretariat and MoFPED")
  - `AUDITOR`

  `NATIONAL_ROLES` and `READ_ONLY_ROLES` are also defined there.
- **User** (`accounts/models.py`) extends AbstractUser with `phone` and `admin_unit`. Its properties and methods are `role`, `has_role(*names)`, `is_national` and `scope_unit_ids()`, which returns `None` for national users.
- **Area scoping** (`accounts/scoping.py`, `accounts/mixins.py`):
  - functions: `scope_queryset(qs, user, unit_field)`, `unit_in_scope`, and `check_unit_in_scope`, which raises PermissionDenied
  - mixins and decorator: `RoleRequiredMixin(allowed_roles)`, `ScopedQuerysetMixin(unit_field)` and the decorator `role_required(*roles)`
  - **Every new view must be role-checked and scoped to the user's area.**
- **Registry** (`registry/`):
  - `AdminUnit` has a level (district, subcounty, parish or village), `parent`, `descendant_ids()` and `ancestors()`.
  - `EnterpriseGroup` belongs to a parish and has an optional SACCO.
  - `Household` stores the NIN, validated as `^[A-Z0-9]{14}$`, unique and saved in upper case. It also has the head of household, phone, sex, age group, disability, household size, wealth rank and village.
  - A household's verification is pending, verified or rejected, with `verified_by`, `verified_at` and `verification_note`. The LC I chairperson verifies by POST, and **a rejection needs a note**. Editing the NIN, village or wealth rank resets verification.
  - Views: household list, create, detail and edit; group list, create (sub-county) and detail.
- **SACCOs** (`saccos/`):
  - `Sacco` is linked one-to-one with a parish and has a 7-item `DEFAULT_CHECKLIST` (`SaccoChecklistItem`), `is_eligible` and `total_released`.
  - `FundRelease` is recorded by the national official and confirmed by the district.
  - The SACCO official ticks the checklist, and a release is refused if the SACCO is not eligible.
- **Loans** (`loans/`):
  - Constants: `LOAN_CEILING = 1_000_000`, `ANNUAL_INTEREST_RATE = 0.06`, `DEFAULT_AFTER_DAYS = 90`.
  - `LoanApplication` statuses: DRAFT, SUBMITTED, APPRAISED, APPROVED, REJECTED, DISBURSED, REPAYING, CLOSED and DEFAULTED. Fields include `decided_by`, `decided_at` and `decision_reason`.
  - `Appraisal` gives viability, repayment and group scores of 1–5, a recommendation and reasons, and has `total_score`.
  - `loans/workflow.py`:
    - `TRANSITIONS` maps (from, to) to the role allowed to make that change. SYSTEM changes are made by the system itself.
    - `can_move()` checks a change; `move(application, target, user=None, reason="")` makes it and raises `TransitionError` or `PermissionDenied` when not allowed.
    - **All status changes must go through `move()`.**
  - Forms:
    - Applications are only for verified households in a group that has a SACCO, scoped by village.
    - The amount is 10,000 up to the ceiling, and the term is 3–24 months.
    - A household can have only one open loan.
  - Views:
    - list, create (group executive), submit and appraise
    - detail, which shows the history using `auditlog.models.LogEntry.objects.get_for_object(loan)`. Do not use `loan.history`; it does not exist.
- **Demo data** (`python manage.py seed_demo`, safe to run again; it uses `get_or_create` so loan progress is not reset):
  - **Places:** district Mukono › sub-county Goma › parishes Seeta (villages Seeta Central, Kitega and Bajjo) and Nantabulirwa (villages A and B).
  - **Users:** `household`, `groupexec`, `lc1`, `parishchief`, `pdc`, `sacco`, `subcounty`, `district`, `national`, `auditor` and `admin`. All have the password `pdm12345`.
  - **Groups and households:** 3 groups and 9 households. Grace (CF85001234ABCD) and Isaac (CM92004567EFGH) are verified.
  - **SACCOs and funding:** "Seeta PDM SACCO" is eligible. "Nantabulirwa PDM SACCO" is missing "Supervisory Board in place". There is a confirmed fund release of 100M for 2025/26.
  - **Loans:** Grace's 800,000 is APPRAISED and Isaac's 500,000 is SUBMITTED.
  - Extend the seed for every new feature so that the demo always has something to show.
- **Tests:** there are 51 and all pass: registry 19, loans 13, accounts 10 and saccos 9. Add tests with every feature.
- **Navigation:** `base.html` hides links for the Household and LC I roles where those roles would get a 403. Keep the navigation in line with the permissions.

## 6. What to build next (the plan, day by day)

Tick each item in `docs/PROGRESS.md` as you finish it (see section 7).

**Day 5: loan decisions (finish this first)**
- [ ] Approve, and reject with reasons. Only the SACCO official may decide, and only from APPRAISED. A rejection reason is required. Use `move()`.
- [ ] Disbursement record: a model with amount, date, method and reference, recorded by the SACCO official. It moves the loan APPROVED → DISBURSED and must not exceed the approved amount or the SACCO's confirmed releases.
- [ ] Finish the tests for the loan workflow: approve, reject, disburse, wrong role and wrong status.

**Day 6: repayment**
- [ ] Repayment schedule at 6% a year over `term_months`. Show the instalments on the loan page.
- [ ] Record repayments, which moves the loan DISBURSED → REPAYING → CLOSED through SYSTEM changes. Add an arrears list.
- [ ] 90-day default flag: a management command, such as `flag_defaults`, that moves loans to DEFAULTED.
- [ ] Tests for interest, the schedule and default.

**Day 7: USSD and SMS (Africa's Talking sandbox)**
- [ ] USSD callback view in `ussd` (CSRF-exempt POST with `sessionId`, `phoneNumber` and `text`) and the menu flow.
- [ ] USSD menus: "My PDM status" and "My loan", with the household found by phone number.
- [ ] SMS alerts on approval, disbursement and repayment. Wrap them in one service function, and log rather than crash when there are no keys.
- [ ] Test every USSD path with the Django test client. Use the simulator when the sandbox exists.

**Day 8: dashboards and audit**
- [ ] Dashboard queries for each level, from parish to national, scoped by `scope_unit_ids()`.
- [ ] Dashboard page with totals and Chart.js charts from a CDN.
- [ ] Audit log page for the auditor role (read-only).

**Day 9: citizen voice (Should)**
- [ ] Complaints by USSD with a reference number, in the `feedback` app.
- [ ] Complaint list and response page.
- [ ] Success stories: a Parish Chief or CDO drafts a story, the PDC checks it against the household's records and approves it, and the household's consent is recorded. Only approved stories are shown.
- [ ] Public parish page with no login: anonymised totals and approved stories.

**Day 10: finish**
- [ ] Walk through the system as each of the ten roles.
- [ ] Security check: logged-out access and cross-parish access must be refused.
- [ ] Fix the bugs found.
- [ ] Final seed data and deploy.
- [ ] Write a demo script (`docs/DEMO.md`) that follows the customer journey below.

**Days 11–14: buffer (Should and Could)**
- [ ] Short user guide.
- [ ] Project report.
- [ ] Automatic complaint escalation.
- [ ] Monitoring visits with photos and GPS.
- [ ] Quarterly report export as PDF and CSV.

**Rule if time runs short:** take time from Day 9 first, then from the buffer. Never take it from Days 2–6, which hold the core cycle.

## 7. How I want you to work

1. **Make many small commits.** I want many commits on my GitHub profile, so make one focused commit per logical step: model, migration, form, view, template, tests, seed and docs each get their own commit. Use clear, imperative commit messages, such as "Add disbursement model". **Push to `main` often**, after each small group of commits, once the tests pass.
2. **Run the tests before every push** (`python manage.py test`), and never push a red build. Run `python manage.py check` and `makemigrations --check` as well.
3. **Tick progress.**
   - Create `docs/PROGRESS.md` from the checklist in section 6, with Days 1–4 marked done. Tick each item (`- [x]`) in the same commit that finishes it.
   - At the end of each session, give me a short list of the items finished, so that I can tick them in my claude.ai task tracker and development plan.
4. **Keep the README current:** setup steps, demo accounts and new features.
5. Work through the plan in order without stopping to ask, unless a decision is costly to undo or really ambiguous. When you make a judgment call, say so in one line.
6. **Never commit secrets,** real personal data or `.env`. Do not add e-commerce features.
7. After changes that affect the live site, remind me that the push redeploys Render. If a deploy might break (for example, a new environment variable), tell me first what to set in the Render dashboard.

## 8. The customer journey the prototype must show (also on the slides)

The first five stages work today; stages 6–10 are being built.

1. **Register.** The Parish Chief profiles a household (web: NIN checked, wealth rank recorded).
2. **Verify.** The LC I chairperson confirms or rejects it; a rejection needs a reason.
3. **Group.** The CDO registers an enterprise group linked to an eligible SACCO.
4. **Apply.** The group executive submits a loan of up to UGX 1M, for verified members only.
5. **Appraise.** The SACCO scores the application, signed by a named official.
6. **Decide.** The SACCO approves and disburses, and keeps the reasons for refusals.
7. **Repay.** The system builds a schedule at 6% a year and flags arrears and 90-day default.
8. **Check.** The household dials the USSD code for its status and gets SMS alerts.
9. **Speak up.** Citizens raise complaints, which escalate if unanswered, and verified success stories are published.
10. **Oversee.** Dashboards from sub-county to national level, and an audit trail for the auditor.

## 9. First steps (first session; later sessions start at step 3 with `git pull`)

1. Clone the repo (or `git pull` if it is already cloned) and set the git identity from section 3.
2. Set up `.env` and the database, then run `migrate`, `seed_demo` and `test`. Confirm that all 51 tests pass.
3. Read `loans/workflow.py`, `loans/views.py`, `loans/forms.py`, `accounts/mixins.py` and `accounts/scoping.py` to learn the patterns.
4. Create `docs/PROGRESS.md` (commit it), then start **Day 5: approve and reject with reasons**.
