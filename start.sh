#!/bin/bash

# Exit on any error
set -e

echo "Starting SAHA-AI deployment..."

# Set Django settings
export DJANGO_SETTINGS_MODULE=core.settings_production

# Test Django setup first
echo "Testing Django setup..."
python test_django.py || echo "Django test failed, continuing anyway..."

# Run database migrations (with retry)
echo "Running database migrations..."
for i in {1..3}; do
    echo "Migration attempt $i..."
    if python manage.py migrate --noinput; then
        echo "Migrations successful"
        break
    else
        echo "Migration attempt $i failed, retrying..."
        sleep 5
    fi
done || echo "Migrations failed after 3 attempts, continuing..."

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "Static collection failed, continuing..."

# Create cache table if using database cache
echo "Creating cache table..."
python manage.py createcachetable || echo "Cache table creation failed, continuing..."

# Start the application
echo "Starting Gunicorn server..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 300 --max-requests 1000 --max-requests-jitter 100 --log-level debug --access-logfile - --error-logfile -
