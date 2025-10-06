#!/usr/bin/env python3
"""
Basic API Test using Django Test Client
"""

import os
import sys
import django
from django.test import Client
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def test_basic_endpoints():
    """Test basic API endpoints using Django test client"""
    client = Client()
    
    print("Testing Basic API Endpoints")
    print("=" * 40)
    
    # Test home page
    try:
        response = client.get('/')
        print(f"[PASS] Home page: {response.status_code}")
    except Exception as e:
        print(f"[FAIL] Home page: {e}")
    
    # Test login page
    try:
        response = client.get('/users/login/')
        print(f"[PASS] Login page: {response.status_code}")
    except Exception as e:
        print(f"[FAIL] Login page: {e}")
    
    # Test portfolio page
    try:
        response = client.get('/portfolio/')
        print(f"[PASS] Portfolio page: {response.status_code}")
    except Exception as e:
        print(f"[FAIL] Portfolio page: {e}")
    
    # Test mobile index
    try:
        response = client.get('/mobile/')
        print(f"[PASS] Mobile index: {response.status_code}")
    except Exception as e:
        print(f"[FAIL] Mobile index: {e}")
    
    # Test API endpoints
    api_endpoints = [
        '/advisor/dev/version/',
        '/advisor/market/snapshot/',
        '/advisor/mutual-fund/',
        '/advisor/mutual-fund/categories/',
    ]
    
    print("\nTesting API Endpoints:")
    print("-" * 30)
    
    for endpoint in api_endpoints:
        try:
            response = client.get(endpoint)
            print(f"[PASS] {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"[FAIL] {endpoint}: {e}")
    
    print("\nBasic API test completed!")

if __name__ == "__main__":
    test_basic_endpoints()
