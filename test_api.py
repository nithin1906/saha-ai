#!/usr/bin/env python3
"""
Stock Market Chatbot API Test Script
Run this script to test all API endpoints before deployment
"""

import requests
import json
import time
from datetime import datetime

class APITester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = []
        
    def log_test(self, test_name, success, message="", response_time=0):
        """Log test results"""
        status = "PASS" if success else "FAIL"
        self.test_results.append({
            "test": test_name,
            "status": status,
            "message": message,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat()
        })
        print(f"[{status}] {test_name}: {message}")
        
    def test_endpoint(self, method, endpoint, data=None, headers=None, expected_status=200):
        """Test a single endpoint"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, timeout=10)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, headers=headers, timeout=10)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, json=data, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response_time = time.time() - start_time
            
            if response.status_code == expected_status:
                self.log_test(f"{method} {endpoint}", True, f"Status: {response.status_code}", response_time)
                return response.json() if response.content else {}
            else:
                self.log_test(f"{method} {endpoint}", False, f"Expected {expected_status}, got {response.status_code}", response_time)
                return None
                
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            self.log_test(f"{method} {endpoint}", False, f"Request failed: {str(e)}", response_time)
            return None
    
    def test_authentication(self):
        """Test authentication endpoints"""
        print("\n=== Testing Authentication ===")
        
        # Test registration
        register_data = {
            "username": "testuser_api",
            "email": "testuser@example.com",
            "password": "testpass123",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = self.test_endpoint("POST", "/users/register/", register_data)
        if response:
            self.log_test("User Registration", True, "User registered successfully")
        
        # Test login
        login_data = {
            "username": "testuser_api",
            "password": "testpass123"
        }
        
        response = self.test_endpoint("POST", "/users/login/", login_data)
        if response and "token" in response:
            self.auth_token = response["token"]
            self.log_test("User Login", True, "Login successful, token received")
        else:
            self.log_test("User Login", False, "Login failed or no token received")
    
    def test_market_data(self):
        """Test market data endpoints"""
        print("\n=== Testing Market Data ===")
        
        # Test market snapshot
        response = self.test_endpoint("GET", "/advisor/market/snapshot/")
        if response and "indices" in response:
            self.log_test("Market Snapshot", True, f"Retrieved {len(response['indices'])} indices")
        
        # Test stock search
        response = self.test_endpoint("GET", "/advisor/search/NSE/RELIANCE")
        if response and "stocks" in response:
            self.log_test("Stock Search NSE", True, f"Found {len(response['stocks'])} stocks")
        
        # Test stock analysis
        response = self.test_endpoint("GET", "/advisor/analyze/RELIANCE/2500/10")
        if response and "ticker" in response:
            self.log_test("Stock Analysis", True, f"Analysis completed for {response['ticker']}")
        
        # Test stock history
        response = self.test_endpoint("GET", "/advisor/history/RELIANCE/?period=1y")
        if response and "data" in response:
            self.log_test("Stock History", True, f"Retrieved {len(response['data']['dates'])} data points")
    
    def test_mutual_funds(self):
        """Test mutual fund endpoints"""
        print("\n=== Testing Mutual Funds ===")
        
        # Test get all mutual funds
        response = self.test_endpoint("GET", "/advisor/mutual-fund/")
        if response and "funds" in response:
            self.log_test("Get All Mutual Funds", True, f"Retrieved {len(response['funds'])} funds")
        
        # Test get categories
        response = self.test_endpoint("GET", "/advisor/mutual-fund/categories/")
        if response and "categories" in response:
            self.log_test("Get Categories", True, f"Found {len(response['categories'])} categories")
        
        # Test mutual fund search
        response = self.test_endpoint("GET", "/advisor/search/MF/HDFC")
        if response and "funds" in response:
            self.log_test("Mutual Fund Search", True, f"Found {len(response['funds'])} funds")
        
        # Test fund details
        response = self.test_endpoint("GET", "/advisor/mutual-fund/HDFC002/")
        if response and "fund" in response:
            self.log_test("Fund Details", True, f"Retrieved details for {response['fund']['fund_name']}")
        
        # Test fund analysis
        response = self.test_endpoint("GET", "/advisor/analyze_mf/HDFC002/75.50/100")
        if response and "scheme_id" in response:
            self.log_test("Fund Analysis", True, f"Analysis completed for {response['scheme_id']}")
        
        # Test fund history
        response = self.test_endpoint("GET", "/advisor/history_mf/HDFC002/?period=1y")
        if response and "nav_history" in response:
            self.log_test("Fund History", True, f"Retrieved {len(response['nav_history'])} NAV records")
    
    def test_portfolio(self):
        """Test portfolio management endpoints"""
        print("\n=== Testing Portfolio Management ===")
        
        if not self.auth_token:
            self.log_test("Portfolio Tests", False, "No auth token available")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test add to portfolio
        portfolio_data = {
            "ticker": "RELIANCE",
            "quantity": 10,
            "buy_price": 2500.00
        }
        response = self.test_endpoint("POST", "/advisor/portfolio/", portfolio_data, headers)
        if response:
            self.log_test("Add to Portfolio", True, "Holding added successfully")
        
        # Test get portfolio
        response = self.test_endpoint("GET", "/advisor/portfolio/", headers=headers)
        if response and "holdings" in response:
            self.log_test("Get Portfolio", True, f"Retrieved {len(response['holdings'])} holdings")
        
        # Test portfolio details
        response = self.test_endpoint("GET", "/advisor/portfolio/details/", headers=headers)
        if response and "total_invested" in response:
            self.log_test("Portfolio Details", True, f"Total invested: ₹{response['total_invested']}")
        
        # Test portfolio health
        response = self.test_endpoint("GET", "/advisor/portfolio/health/", headers=headers)
        if response and "overall_score" in response:
            self.log_test("Portfolio Health", True, f"Overall score: {response['overall_score']}")
        
        # Test remove from portfolio
        remove_data = {"ticker": "RELIANCE"}
        response = self.test_endpoint("DELETE", "/advisor/portfolio/", remove_data, headers)
        if response:
            self.log_test("Remove from Portfolio", True, "Holding removed successfully")
    
    def test_chat_ai(self):
        """Test chat and AI endpoints"""
        print("\n=== Testing Chat & AI ===")
        
        # Test parse intent
        parse_data = {"text": "What is the current price of Reliance?"}
        response = self.test_endpoint("POST", "/advisor/parse/", parse_data)
        if response and "intent" in response:
            self.log_test("Parse Intent", True, f"Intent: {response['intent']}")
        
        # Test chat
        chat_data = {"message": "Show me my portfolio performance"}
        response = self.test_endpoint("POST", "/advisor/chat/", chat_data)
        if response and "response" in response:
            self.log_test("Chat", True, "AI response generated")
    
    def test_development(self):
        """Test development endpoints"""
        print("\n=== Testing Development ===")
        
        # Test version info
        response = self.test_endpoint("GET", "/advisor/dev/version/")
        if response and "version" in response:
            self.log_test("Version Info", True, f"Version: {response['version']}")
    
    def run_all_tests(self):
        """Run all API tests"""
        print("Starting Stock Market Chatbot API Tests")
        print("=" * 50)
        
        start_time = time.time()
        
        # Run all test suites
        self.test_authentication()
        self.test_market_data()
        self.test_mutual_funds()
        self.test_portfolio()
        self.test_chat_ai()
        self.test_development()
        
        total_time = time.time() - start_time
        
        # Generate summary
        print("\n" + "=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result["status"] == "PASS")
        failed = sum(1 for result in self.test_results if result["status"] == "FAIL")
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        print(f"Total Time: {total_time:.2f} seconds")
        
        # Show failed tests
        if failed > 0:
            print("\nFAILED TESTS:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result['message']}")
        
        # Save results to file
        with open("api_test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "success_rate": (passed/total)*100,
                    "total_time": total_time
                },
                "results": self.test_results
            }, f, indent=2)
        
        print(f"\nDetailed results saved to: api_test_results.json")
        
        return failed == 0

if __name__ == "__main__":
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    tester = APITester(base_url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
