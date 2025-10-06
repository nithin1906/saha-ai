#!/usr/bin/env python3
"""
Test Mobile Routing Middleware Locally
"""

import os
import sys
import django
from django.test import RequestFactory
from django.http import HttpResponseRedirect

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from advisor.middleware import DeviceDetectionMiddleware

def test_mobile_routing():
    """Test mobile routing middleware"""
    print("Testing Mobile Routing Middleware")
    print("=" * 40)
    
    # Set environment variable
    os.environ['MOBILE_SERVICE_URL'] = 'https://saha-ai-mobile.up.railway.app'
    
    # Create middleware instance
    middleware = DeviceDetectionMiddleware(lambda x: None)
    
    # Create request factory
    factory = RequestFactory()
    
    # Test mobile user agent
    mobile_headers = {
        'HTTP_USER_AGENT': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
    }
    
    request = factory.get('/', **mobile_headers)
    request.session = {}
    
    # Test middleware
    response = middleware.process_request(request)
    
    if isinstance(response, HttpResponseRedirect):
        print(f"[OK] Mobile redirect working: {response.url}")
        return True
    else:
        print(f"[ERROR] No redirect, got: {type(response)}")
        return False

def test_desktop_routing():
    """Test desktop routing (no redirect)"""
    print("\nTesting Desktop Routing")
    print("=" * 40)
    
    # Set environment variable
    os.environ['MOBILE_SERVICE_URL'] = 'https://saha-ai-mobile.up.railway.app'
    
    # Create middleware instance
    middleware = DeviceDetectionMiddleware(lambda x: None)
    
    # Create request factory
    factory = RequestFactory()
    
    # Test desktop user agent
    desktop_headers = {
        'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    request = factory.get('/', **desktop_headers)
    request.session = {}
    
    # Test middleware
    response = middleware.process_request(request)
    
    if response is None:
        print("[OK] Desktop routing working (no redirect)")
        return True
    else:
        print(f"[ERROR] Unexpected redirect for desktop: {response}")
        return False

def main():
    """Run all tests"""
    print("Mobile Routing Middleware Test")
    print("=" * 50)
    
    mobile_ok = test_mobile_routing()
    desktop_ok = test_desktop_routing()
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    if mobile_ok and desktop_ok:
        print("[SUCCESS] Mobile routing middleware is working correctly!")
        print("\nNext steps:")
        print("1. Deploy the updated code to the mobile service")
        print("2. Run 'python manage.py collectstatic' on mobile service")
        print("3. Test the live mobile app")
        return 0
    else:
        print("[ERROR] Mobile routing middleware has issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())
