#!/usr/bin/env python3
"""
Comprehensive Mobile App Test
Tests all mobile app functionality including routing, authentication, and API endpoints.
"""

import requests
import json
import time
import sys
from urllib.parse import urljoin

# Configuration
PC_SERVICE_URL = "https://saha-ai.up.railway.app"
MOBILE_SERVICE_URL = "https://saha-ai-mobile.up.railway.app"

def test_endpoint(url, method="GET", data=None, headers=None, expected_status=200):
    """Test a single endpoint"""
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        
        status_ok = response.status_code == expected_status
        print(f"[{'OK' if status_ok else 'ERROR'}] {method} {url} - Status: {response.status_code}")
        
        if not status_ok:
            print(f"    Expected: {expected_status}, Got: {response.status_code}")
            if response.text:
                print(f"    Response: {response.text[:200]}...")
        
        return status_ok, response
    except Exception as e:
        print(f"[ERROR] {method} {url} - Exception: {str(e)}")
        return False, None

def test_mobile_routing():
    """Test mobile device routing from PC service"""
    print("\n=== Testing Mobile Device Routing ===")
    
    # Test mobile user agent detection
    mobile_headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
    }
    
    success, response = test_endpoint(PC_SERVICE_URL, headers=mobile_headers)
    
    if success and response:
        # Check if redirected to mobile service
        if response.status_code == 302:
            location = response.headers.get('Location', '')
            if 'mobile' in location.lower():
                print(f"[OK] Mobile redirect detected: {location}")
                return True
            else:
                print(f"[ERROR] Redirect not to mobile service: {location}")
                return False
        else:
            print(f"[ERROR] Expected redirect (302), got {response.status_code}")
            return False
    
    return False

def test_mobile_service_endpoints():
    """Test mobile service endpoints"""
    print("\n=== Testing Mobile Service Endpoints ===")
    
    endpoints = [
        ("/", "Mobile Home"),
        ("/mobile/", "Mobile Index"),
        ("/mobile/portfolio/", "Mobile Portfolio"),
        ("/mobile/profile/", "Mobile Profile"),
        ("/mobile/about/", "Mobile About"),
        ("/users/login/", "Mobile Login"),
        ("/users/register/", "Mobile Register"),
    ]
    
    results = []
    for endpoint, description in endpoints:
        url = urljoin(MOBILE_SERVICE_URL, endpoint)
        success, response = test_endpoint(url)
        results.append((description, success))
        
        if success and response and endpoint in ["/", "/mobile/"]:
            # Check if it's actually the mobile version
            if "mobile" in response.text.lower() or "SAHA-AI" in response.text:
                print(f"    [OK] {description} returns mobile content")
            else:
                print(f"    [WARNING] {description} might not be mobile version")
    
    return results

def test_static_files():
    """Test mobile static files"""
    print("\n=== Testing Mobile Static Files ===")
    
    static_files = [
        "/static/css/mobile-saha.css",
        "/static/js/mobile-saha.js",
        "/static/css/tailwind.css",
        "/static/manifest.json",
        "/static/sw.js"
    ]
    
    results = []
    for file_path in static_files:
        url = urljoin(MOBILE_SERVICE_URL, file_path)
        success, response = test_endpoint(url)
        results.append((file_path, success))
        
        if success and response:
            content_type = response.headers.get('Content-Type', '')
            print(f"    [OK] {file_path} - Content-Type: {content_type}")
            
            # Check for proper MIME types
            if file_path.endswith('.css') and 'text/css' not in content_type:
                print(f"    [WARNING] CSS file has wrong MIME type: {content_type}")
            elif file_path.endswith('.js') and 'javascript' not in content_type:
                print(f"    [WARNING] JS file has wrong MIME type: {content_type}")
            elif file_path.endswith('.json') and 'json' not in content_type:
                print(f"    [WARNING] JSON file has wrong MIME type: {content_type}")
    
    return results

def test_api_endpoints():
    """Test API endpoints"""
    print("\n=== Testing API Endpoints ===")
    
    api_endpoints = [
        ("/api/chat/", "Chat API"),
        ("/api/stock-price/RELIANCE/", "Stock Price API"),
        ("/api/portfolio/", "Portfolio API"),
    ]
    
    results = []
    for endpoint, description in api_endpoints:
        url = urljoin(MOBILE_SERVICE_URL, endpoint)
        success, response = test_endpoint(url, expected_status=[200, 401, 403])  # 401/403 OK for unauthenticated
        results.append((description, success))
    
    return results

def test_authentication_flow():
    """Test authentication flow"""
    print("\n=== Testing Authentication Flow ===")
    
    # Test login page
    login_url = urljoin(MOBILE_SERVICE_URL, "/users/login/")
    success, response = test_endpoint(login_url)
    
    if not success:
        return False
    
    # Test CSRF token presence
    if response and 'csrf' in response.text.lower():
        print("[OK] CSRF token present in login form")
    else:
        print("[WARNING] CSRF token might be missing")
    
    return True

def main():
    """Run all tests"""
    print("SAHA-AI Mobile App Comprehensive Test")
    print("=" * 50)
    
    all_results = []
    
    # Test mobile routing
    routing_success = test_mobile_routing()
    all_results.append(("Mobile Routing", routing_success))
    
    # Test mobile service endpoints
    endpoint_results = test_mobile_service_endpoints()
    all_results.extend(endpoint_results)
    
    # Test static files
    static_results = test_static_files()
    all_results.extend(static_results)
    
    # Test API endpoints
    api_results = test_api_endpoints()
    all_results.extend(api_results)
    
    # Test authentication
    auth_success = test_authentication_flow()
    all_results.append(("Authentication Flow", auth_success))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(all_results)
    
    for test_name, success in all_results:
        status = "[OK]" if success else "[ERROR]"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed! Mobile app is working correctly.")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} tests failed. Check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
