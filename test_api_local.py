#!/usr/bin/env python3
"""
Test API Endpoints Locally
"""

import requests
import time
import sys

def test_api_endpoints():
    """Test API endpoints locally"""
    print("Testing API Endpoints Locally")
    print("=" * 40)
    
    base_url = "http://127.0.0.1:8000"
    
    # Wait for server to start
    print("Waiting for server to start...")
    time.sleep(5)
    
    endpoints = [
        ("/api/chat/", "Chat API"),
        ("/api/stock-price/RELIANCE/", "Stock Price API"),
        ("/api/portfolio/", "Portfolio API"),
    ]
    
    results = []
    
    for endpoint, description in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, timeout=10)
            status_ok = response.status_code in [200, 401, 403]  # 401/403 OK for unauthenticated
            
            print(f"[{'OK' if status_ok else 'ERROR'}] {description} - Status: {response.status_code}")
            
            if status_ok and response.status_code == 200:
                try:
                    data = response.json()
                    print(f"    Response: {data}")
                except:
                    print(f"    Response: {response.text[:100]}...")
            
            results.append((description, status_ok))
            
        except requests.exceptions.ConnectionError:
            print(f"[ERROR] {description} - Connection failed (server not running?)")
            results.append((description, False))
        except Exception as e:
            print(f"[ERROR] {description} - Exception: {e}")
            results.append((description, False))
    
    return results

def main():
    """Run API tests"""
    print("Local API Endpoint Test")
    print("=" * 50)
    
    results = test_api_endpoints()
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "[OK]" if success else "[ERROR]"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All API endpoints are working locally!")
        print("\nNext steps:")
        print("1. Commit and push changes to repository")
        print("2. Deploy to Railway services")
        print("3. Run 'python manage.py collectstatic' on mobile service")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
