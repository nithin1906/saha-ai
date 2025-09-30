#!/bin/bash

echo "=== SAHA-AI STARTUP SCRIPT ==="
echo "Starting at: $(date)"
echo "Working directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Django settings: $DJANGO_SETTINGS_MODULE"

# Set Django settings
export DJANGO_SETTINGS_MODULE=core.settings_production

echo "=== Testing Django ==="
python -c "
import os
import sys
print('Python path:', sys.path)
print('Django settings:', os.environ.get('DJANGO_SETTINGS_MODULE'))
try:
    import django
    print('Django imported successfully')
    django.setup()
    print('Django setup completed')
except Exception as e:
    print('Django error:', str(e))
    import traceback
    traceback.print_exc()
"

echo "=== Running Migrations ==="
python manage.py migrate --noinput || echo "Migrations failed, continuing..."

echo "=== Collecting Static Files ==="
python manage.py collectstatic --noinput || echo "Static collection failed, continuing..."

echo "=== Starting Gunicorn ==="
echo "Port: $PORT"
echo "Starting Gunicorn with debug logging..."

exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 300 --log-level debug --access-logfile - --error-logfile -
