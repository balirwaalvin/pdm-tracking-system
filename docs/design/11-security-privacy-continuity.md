# 11. Security, privacy and continuity

*Phase 4 · Security and continuity (4 marks)* · **Owner:** ______________ · **Reviewed by:** ______________

## 11.1 Controls

| Area | Control in the prototype |
| --- | --- |
| Least privilege | Ten roles; one access policy (`accounts/access.py`) decides every page and action; menus show only what a role may use |
| Area scoping | Every list and record limited to the user's own village, parish, sub-county or district |
| Separation of duties | Maker-checker: the official who appraises a loan cannot decide it; national records releases, district confirms |
| Authentication | Passwords hashed (PBKDF2); 5 failed attempts lock the account for 15 minutes; sessions end after 30 minutes idle |
| Transport | HTTPS only, HSTS, secure cookies, `X-Frame-Options: DENY` |
| Input validation | Django forms on every input; CSRF tokens; ORM (no raw SQL) |
| USSD | Shared callback token; a household can only dial with its own registered number |
| Audit | Every change logged with user and time; sign-in log including failures; auditor role is read-only |
| Secrets | Only in environment variables on Render; `.env` never committed |

## 11.2 Threat analysis (STRIDE)

| # | Threat | STRIDE | Example | Mitigation | Residual risk |
| --- | --- | --- | --- | --- | --- |
| T1 | Password guessing | Spoofing | Script tries passwords for `saccochair` | Lockout after 5 failures; sign-in log for the auditor | Low |
| T2 | Official approves own appraisal | Elevation / Tampering | One SACCO official pushes a friend's loan | Maker-checker in `workflow.move()`; audit log | Low |
| T3 | Reading another parish's records | Information disclosure | Parish Chief changes the record number in the URL | Area scoping returns 403/404; tested (TC12) | Low |
| T4 | Fake USSD requests | Spoofing | Someone posts to the callback to read a household's loan | Callback token; registered numbers only | Medium (real gateway IP allow-list needed) |
| T5 | Changing records without trace | Repudiation | Official edits a repayment amount | django-auditlog keeps before/after values and the user | Low |
| T6 | Ghost beneficiaries | Spoofing / Tampering | Invented household profiled | NIN unique; LC I verification; identity check against register | Medium (mock register only) |
| T7 | Bribery for loans | Tampering | Official asks for a fee | Complaint category *bribery* starts at sub-county; escalation after 7 days | Medium (depends on follow-up) |
| T8 | Service unavailable | Denial of service | Free instance sleeps or is overloaded | Keep-awake job; USSD fallback; paid tier for real use | Medium |

## 11.3 Privacy and ethics

- **Sample data only:** every name, NIN and phone number is fictitious (07000000xx numbers); the site says it is a prototype on every page.
- **Consent:** success stories need recorded consent (signed, thumbprint or witnessed) and a separate choice about being named.
- **Free at the point of use:** no payments, no fees, no marketplace.
- A real system must register with the Personal Data Protection Office and follow the Data Protection and Privacy Act 2019 **[verify]**.

## 11.4 Backup and restore

| Item | Prototype | Real deployment |
| --- | --- | --- |
| Database backup | `pg_dump` by hand: `pg_dump "$DATABASE_URL" > pdm-backup.sql` | Daily automatic backups with point-in-time recovery (paid Render plan or government data centre) |
| Restore | `psql "$DATABASE_URL" < pdm-backup.sql`, then `python manage.py migrate` | Tested restore every quarter |
| Sample data | *Reset demo data* (admin) or `python manage.py seed_demo` rebuilds the demo in about 15 seconds | n/a |
| Code | GitHub repository; every version can be redeployed | Same, plus tagged releases |
| Recovery target | Minutes (reseed) | RPO 24 h, RTO 4 h (proposal) |

**Known limit:** Render's free PostgreSQL has no automatic backups and expires after a fixed period **[verify the current limit on render.com]**. Take a `pg_dump` before the presentation.
