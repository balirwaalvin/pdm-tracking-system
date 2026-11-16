# PDM Tracking System

An e-governance prototype for tracking the **Parish Development Model (PDM)** in Uganda, from the household to the ministry.

Every PDM stakeholder (households, LC I chairpersons, Parish Chiefs, Parish Development Committees, PDM SACCOs, sub-county, district and national officers, and auditors) works from one shared record. Selections, approvals and payments are signed by named officials, reports come from live data, and citizens can check their status and raise complaints by USSD.

> Student project for the course unit *E-Commerce, E-Business & E-Governance*, BSIT Year 3, Uganda Christian University. This is a prototype that uses sample data only. It is not an official government system.

## Status

Under active development: a functional prototype within 10 days.

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
python manage.py runserver
```

Open http://127.0.0.1:8000.

## Deploy

The repository includes a Render blueprint (`render.yaml`). In Render, choose **New → Blueprint**, connect this repository, and Render creates the web service and a free PostgreSQL database.

## Tech stack

Django 5 · PostgreSQL · Bootstrap 5 · django-auditlog · Africa's Talking (USSD and SMS)
