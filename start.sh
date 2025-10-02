#!/bin/bash

echo "=== SAHA-AI STARTUP SCRIPT ==="
echo "Starting at: $(date)"
echo "Working directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Django settings: $DJANGO_SETTINGS_MODULE"

# Set Django settings
export DJANGO_SETTINGS_MODULE=core.settings_production

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL is not set!"
    echo "Available environment variables:"
    env | grep -i database || echo "No DATABASE variables found"
    exit 1
else
    echo "DATABASE_URL is set (length: ${#DATABASE_URL} chars)"
fi

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
if python manage.py migrate --noinput; then
    echo "Migrations completed successfully"
else
    echo "ERROR: Migrations failed!"
    echo "Attempting to diagnose database connection..."
    python -c "
import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings_production')
django.setup()
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
    print('Database connection successful!')
except Exception as e:
    print(f'Database connection failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
    exit 1
fi

echo "=== Collecting Static Files ==="
python manage.py collectstatic --noinput || echo "Static collection failed, continuing..."

echo "=== Setting up Admin User ==="
python manage.py setup_admin --username admin --password admin123 || echo "Admin setup failed, continuing..."

echo "=== Starting Gunicorn ==="
echo "Port: $PORT"
echo "Starting Gunicorn with debug logging..."

exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 300 --log-level debug --access-logfile - --error-logfile -
