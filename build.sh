#!/usr/bin/env bash
# Build script for Render: install packages, collect static files, run migrations.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

# Load or refresh the sample parish and demo users (safe to run on every deploy).
python manage.py seed_demo

# Flag loans with an instalment 90 or more days overdue as defaulted.
python manage.py flag_defaults
