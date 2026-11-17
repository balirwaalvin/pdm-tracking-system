# PDM Tracking System

An e-governance prototype for tracking the **Parish Development Model (PDM)** in Uganda, from the household to the ministry.

Every PDM stakeholder (households, LC I chairpersons, Parish Chiefs, Parish Development Committees, PDM SACCOs, sub-county, district and national officers, and auditors) works from one shared record. Selections, approvals and payments are signed by named officials, reports come from live data, and citizens can check their status and raise complaints by USSD.

> Student project for the course unit *E-Commerce, E-Business & E-Governance*, BSIT Year 3, Uganda Christian University. This is a prototype that uses sample data only. It is not an official government system.

## Status

Under active development: a functional prototype within 10 days. See [docs/PROGRESS.md](docs/PROGRESS.md) for the day-by-day checklist.

## Features so far

- **Registry:** the Parish Chief profiles households (NIN checked, wealth rank recorded); the LC I chairperson verifies or rejects them, with a reason for every rejection.
- **Enterprise groups:** the sub-county CDO registers groups and links them to the parish PDM SACCO.
- **SACCOs:** a seven-point eligibility checklist; the national office records fund releases and the district confirms them.
- **Loans:** the group executive applies (up to UGX 1,000,000, verified members only); the SACCO appraises, approves or rejects with reasons, and records the disbursement. A payout cannot exceed the approved amount or the SACCO's confirmed funds.
- **Repayment:** a monthly schedule at 6% a year (flat over the term) on every paid-out loan. The SACCO records repayments; the system moves the loan to Repaying and then Closed, lists arrears, and flags a loan as Defaulted once an instalment is 90 days overdue (`python manage.py flag_defaults`, also run on every deploy).
- **USSD and SMS (Africa's Talking):** a household dials the PDM short code to see its verification and loan status (balance, next instalment, arrears). It gets an SMS when its loan is approved or rejected, paid out, and repaid. Every SMS is kept on the loan page. Officials can try the menu at **USSD** in the navigation (`/ussd/simulator/`), only as households in their own area.
- **Complaints:** households raise complaints by USSD ("3. Report a problem") or on the web, get a reference number by SMS, and track them by USSD. The Parish Chief responds first; a complaint not resolved within 7 days moves to the sub-county and then the district (`python manage.py escalate_complaints`, also run on every deploy). Bribery complaints start at the sub-county.
- **Success stories:** the Parish Chief or CDO drafts a story and records the household's consent (and whether they may be named); the PDC checks it against the household's records and approves it or sends it back with a reason.
- **Public parish pages** (`/parishes/`, no sign-in): anonymised totals (households, loans paid out, on-time repayment rate, complaints resolved), approved stories, and the same figures as an open data CSV.
- **Dashboards:** totals and Chart.js charts for the user's own area, split one level down (national by district, district by sub-county, sub-county by parish, parish by village): households and verification, inclusion, money paid out, repaid and in arrears, and portfolio at risk.
- **Audit trail:** every change is logged with who made it and when. The auditor has a read-only audit log page (`/audit/`) with filters and a CSV download.

Every page checks the user's role and shows only records in the user's own area.

## Run it locally

Requirements: Python 3.12+ and PostgreSQL 16.

```bash
git clone https://github.com/balirwaalvin/pdm-tracking-system.git
cd pdm-tracking-system
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # then edit DATABASE_URL if needed
createdb pdm_tracker
python manage.py migrate
python manage.py seed_demo     # sample parish and one user per role
python manage.py runserver
```

Open http://127.0.0.1:8000.

## Demo accounts

`seed_demo` creates a sample parish (Mukono › Goma › Seeta) and these users. Every password is `pdm12345` unless you pass `--password`.

| Username | Role | Area |
| --- | --- | --- |
| `household` | Household | Seeta Central village |
| `groupexec` | Enterprise group executive | Seeta parish |
| `lc1` | LC I Chairperson | Seeta Central village |
| `parishchief` | Parish Chief | Seeta parish |
| `pdc` | Parish Development Committee | Seeta parish |
| `sacco` | PDM SACCO official | Seeta parish |
| `saccochair` | PDM SACCO official (Board chair: approves or rejects loans that `sacco` appraised) | Seeta parish |
| `subcounty` | Sub-county Chief and CDO | Goma sub-county |
| `district` | District official | Mukono district |
| `national` | PDM Secretariat and MoFPED | Whole country |
| `auditor` | Auditor | Whole country |
| `admin` | Administrator (Django admin) | Whole country |

The seed also adds 14 sample households, 3 enterprise groups, 2 SACCOs (Seeta is eligible; Nantabulirwa still lacks its Supervisory Board) and a loan at each stage: submitted, appraised, approved, rejected, disbursed, repaying with arrears, and defaulted.

These are sample people and places for demonstration only.

## Access by role

Access follows least privilege. One policy table, `accounts/access.py`, decides which role may open each page and take each action. The menu, each user's home page and every view read from it, and a test checks the whole matrix (every allowed page opens, every other page is refused). On top of this, everyone sees only records in their own area.

| Role | My household | Dashboard | Households | Groups | SACCOs | Loans | Arrears | USSD | Audit log | Can do |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | --- |
| Household | ✓ |  |  |  |  |  |  |  |  | read only |
| Enterprise group executive |  |  | ✓ | ✓ |  | ✓ |  |  |  | start a loan application |
| LC I Chairperson |  |  | ✓ |  |  |  |  | ✓ |  | verify households |
| Parish Chief |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | register a household |
| Parish Development Committee |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  | read only |
| PDM SACCO official |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |  | update the sacco checklist, appraise, decide and pay out loans |
| Sub-county Chief and CDO |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | register an enterprise group |
| District official |  | ✓ |  |  | ✓ | ✓ | ✓ |  |  | confirm fund releases |
| PDM Secretariat and MoFPED |  | ✓ |  |  | ✓ | ✓ | ✓ |  |  | record fund releases |
| Auditor |  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  | ✓ | read only |

After signing in, each user lands on their own workspace: the work waiting for their role (for example, loans to appraise for the SACCO, or households to verify for the LC I chairperson), the pages and actions they may use, and what is outside their role. A household user sees only their own household, loan and SMS alerts.

## Africa's Talking (USSD and SMS)

The USSD callback is `POST /ussd/callback/` (no login; Africa's Talking sends `sessionId`, `serviceCode`, `phoneNumber` and `text`). In the Africa's Talking sandbox, create a USSD channel and set its callback URL to `https://pdm.treez.tech/ussd/callback/`.

SMS alerts need `AT_USERNAME`, `AT_API_KEY` and (optionally) `AT_SENDER_ID`. Without `AT_API_KEY` the alerts are saved and logged but not sent, so the system works fully without an account.

## Run the tests

```bash
python manage.py test
```

## Deploy

Live at **https://pdm.treez.tech** (custom domain; the Render address https://pdm-tracking-system.onrender.com also works). The DNS is a CNAME in Cloudflare, set to DNS only so Render can issue the TLS certificate.

The repository includes a Render blueprint (`render.yaml`). In Render, choose **New → Blueprint**, connect this repository, and Render creates the web service and a free PostgreSQL database.

## Tech stack

Django 5 · PostgreSQL · Bootstrap 5 · django-auditlog · Africa's Talking (USSD and SMS)
