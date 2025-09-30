#!/usr/bin/env python
import os
import sys
import django

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings_production')

try:
    django.setup()
    print("✅ Django setup successful")
    
    # Test database connection
    from django.db import connection
    connection.ensure_connection()
    print("✅ Database connection successful")
    
    # Test basic Django functionality
    from django.conf import settings
    print(f"✅ Settings loaded: DEBUG={settings.DEBUG}")
    print(f"✅ ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    
    print("✅ All Django tests passed!")
    
except Exception as e:
    print(f"❌ Django test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
