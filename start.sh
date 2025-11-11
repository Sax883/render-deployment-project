#!/usr/bin/env bash
Exit immediately if a command exits with a non-zero status
set -e
Run the database setup script to create tables/schema (REQUIRED)
echo "Running database schema setup..."
python database_setup_psql.py
Start the Gunicorn server (production server)
The format is gunicorn [module_name]:[flask_app_object_name]
echo "Starting Gunicorn server..."
gunicorn app:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120