#!/bin/bash

# Exit on any error
set -e

echo "Starting SAHA-AI deployment..."

# Set Django settings
export DJANGO_SETTINGS_MODULE=core.settings_production

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create cache table if using database cache
echo "Creating cache table..."
python manage.py createcachetable

# Start the application
echo "Starting Gunicorn server..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120 --max-requests 1000 --max-requests-jitter 100
