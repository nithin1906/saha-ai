#!/bin/bash

# Exit on any error
set -e

echo "Starting SAHA-AI deployment..."

# Set Django settings
export DJANGO_SETTINGS_MODULE=core.settings_production

# Wait for database to be ready
echo "Waiting for database connection..."
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings_production')
django.setup()
from django.db import connection
try:
    connection.ensure_connection()
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
"

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput || echo "Migration failed, continuing..."

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "Static collection failed, continuing..."

# Create cache table if using database cache
echo "Creating cache table..."
python manage.py createcachetable || echo "Cache table creation failed, continuing..."

# Start the application
echo "Starting Gunicorn server..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 300 --max-requests 1000 --max-requests-jitter 100 --log-level debug
