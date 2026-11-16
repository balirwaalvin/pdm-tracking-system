#!/usr/bin/env bash
# Build script for Render: install packages, collect static files, run migrations.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
