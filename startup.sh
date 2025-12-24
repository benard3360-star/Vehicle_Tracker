#!/bin/bash

# Install dependencies
pip install -r requirements-azure.txt

# Collect static files
python vehicle_intelligence/manage.py collectstatic --noinput

# Run migrations
python vehicle_intelligence/manage.py migrate

# Start Gunicorn
cd vehicle_intelligence
gunicorn --bind 0.0.0.0:8000 vehicle_intelligence.wsgi:application