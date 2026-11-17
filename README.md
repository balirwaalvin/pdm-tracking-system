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
- **Audit trail:** every change is logged with who made it and when.

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
| `subcounty` | Sub-county Chief and CDO | Goma sub-county |
| `district` | District official | Mukono district |
| `national` | PDM Secretariat and MoFPED | Whole country |
| `auditor` | Auditor | Whole country |
| `admin` | Administrator (Django admin) | Whole country |

The seed also adds 14 sample households, 3 enterprise groups, 2 SACCOs (Seeta is eligible; Nantabulirwa still lacks its Supervisory Board) and a loan at each stage: submitted, appraised, approved, rejected, disbursed, repaying with arrears, and defaulted.

These are sample people and places for demonstration only.

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
