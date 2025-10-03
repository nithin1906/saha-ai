"""
Django management command to test API endpoints
Run with: python manage.py test_api
"""

from django.core.management.base import BaseCommand
from django.test import Client
import json

class Command(BaseCommand):
    help = 'Test all API endpoints'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def handle(self, *args, **options):
        self.verbose = options['verbose']
        self.client = Client()
        self.test_results = []
        
        self.stdout.write("Starting Stock Market Chatbot API Tests")
        self.stdout.write("=" * 50)
        
        # Run all test suites
        self.test_market_data()
        self.test_mutual_funds()
        self.test_chat_ai()
        self.test_development()
        
        # Generate summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("TEST SUMMARY")
        self.stdout.write("=" * 50)
        
        passed = sum(1 for result in self.test_results if result["status"] == "PASS")
        failed = sum(1 for result in self.test_results if result["status"] == "FAIL")
        total = len(self.test_results)
        
        self.stdout.write(f"Total Tests: {total}")
        self.stdout.write(f"Passed: {passed}")
        self.stdout.write(f"Failed: {failed}")
        self.stdout.write(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Show failed tests
        if failed > 0:
            self.stdout.write("\nFAILED TESTS:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    self.stdout.write(f"  - {result['test']}: {result['message']}")
        
        # Save results to file
        with open("api_test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "success_rate": (passed/total)*100
                },
                "results": self.test_results
            }, f, indent=2)
        
        self.stdout.write(f"\nDetailed results saved to: api_test_results.json")
        
        if failed == 0:
            self.stdout.write(self.style.SUCCESS("All tests passed! [PASS]"))
        else:
            self.stdout.write(self.style.ERROR(f"{failed} tests failed! [FAIL]"))
    
    def log_test(self, test_name, success, message=""):
        """Log test results"""
        status = "PASS" if success else "FAIL"
        self.test_results.append({
            "test": test_name,
            "status": status,
            "message": message
        })
        
        if success:
            self.stdout.write(self.style.SUCCESS(f"[PASS] {test_name}: {message}"))
        else:
            self.stdout.write(self.style.ERROR(f"[FAIL] {test_name}: {message}"))
        
        if self.verbose:
            self.stdout.write(f"    Status: {status}, Message: {message}")
    
    def test_market_data(self):
        """Test market data endpoints"""
        self.stdout.write("\n=== Testing Market Data ===")
        
        # Test market snapshot
        try:
            response = self.client.get('/advisor/market/snapshot/')
            if response.status_code == 200:
                data = response.json()
                if 'indices' in data:
                    self.log_test("Market Snapshot", True, f"Retrieved {len(data['indices'])} indices")
                else:
                    self.log_test("Market Snapshot", False, "No indices data found")
            else:
                self.log_test("Market Snapshot", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Market Snapshot", False, f"Error: {str(e)}")
        
        # Test stock search
        try:
            response = self.client.get('/advisor/search/NSE/RELIANCE')
            if response.status_code == 200:
                data = response.json()
                if 'stocks' in data:
                    self.log_test("Stock Search NSE", True, f"Found {len(data['stocks'])} stocks")
                else:
                    self.log_test("Stock Search NSE", False, "No stocks data found")
            else:
                self.log_test("Stock Search NSE", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Stock Search NSE", False, f"Error: {str(e)}")
        
        # Test stock analysis
        try:
            response = self.client.get('/advisor/analyze/RELIANCE/2500/10')
            if response.status_code == 200:
                data = response.json()
                if 'ticker' in data:
                    self.log_test("Stock Analysis", True, f"Analysis completed for {data['ticker']}")
                else:
                    self.log_test("Stock Analysis", False, "No ticker data found")
            else:
                self.log_test("Stock Analysis", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Stock Analysis", False, f"Error: {str(e)}")
    
    def test_mutual_funds(self):
        """Test mutual fund endpoints"""
        self.stdout.write("\n=== Testing Mutual Funds ===")
        
        # Test get all mutual funds
        try:
            response = self.client.get('/advisor/mutual-fund/')
            if response.status_code == 200:
                data = response.json()
                if 'funds' in data:
                    self.log_test("Get All Mutual Funds", True, f"Retrieved {len(data['funds'])} funds")
                else:
                    self.log_test("Get All Mutual Funds", False, "No funds data found")
            else:
                self.log_test("Get All Mutual Funds", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Get All Mutual Funds", False, f"Error: {str(e)}")
        
        # Test get categories
        try:
            response = self.client.get('/advisor/mutual-fund/categories/')
            if response.status_code == 200:
                data = response.json()
                if 'categories' in data:
                    self.log_test("Get Categories", True, f"Found {len(data['categories'])} categories")
                else:
                    self.log_test("Get Categories", False, "No categories data found")
            else:
                self.log_test("Get Categories", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Get Categories", False, f"Error: {str(e)}")
        
        # Test mutual fund search
        try:
            response = self.client.get('/advisor/search/MF/HDFC')
            if response.status_code == 200:
                data = response.json()
                if 'funds' in data:
                    self.log_test("Mutual Fund Search", True, f"Found {len(data['funds'])} funds")
                else:
                    self.log_test("Mutual Fund Search", False, "No funds data found")
            else:
                self.log_test("Mutual Fund Search", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Mutual Fund Search", False, f"Error: {str(e)}")
        
        # Test fund details
        try:
            response = self.client.get('/advisor/mutual-fund/HDFC002/')
            if response.status_code == 200:
                data = response.json()
                if 'fund' in data:
                    self.log_test("Fund Details", True, f"Retrieved details for {data['fund']['fund_name']}")
                else:
                    self.log_test("Fund Details", False, "No fund data found")
            else:
                self.log_test("Fund Details", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Fund Details", False, f"Error: {str(e)}")
    
    def test_chat_ai(self):
        """Test chat and AI endpoints"""
        self.stdout.write("\n=== Testing Chat & AI ===")
        
        # Test parse intent
        try:
            response = self.client.post('/advisor/parse/', 
                                     json.dumps({"text": "What is the current price of Reliance?"}),
                                     content_type='application/json')
            if response.status_code == 200:
                data = response.json()
                if 'intent' in data:
                    self.log_test("Parse Intent", True, f"Intent: {data['intent']}")
                else:
                    self.log_test("Parse Intent", False, "No intent data found")
            else:
                self.log_test("Parse Intent", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Parse Intent", False, f"Error: {str(e)}")
        
        # Test chat
        try:
            response = self.client.post('/advisor/chat/', 
                                     json.dumps({"message": "Show me my portfolio performance"}),
                                     content_type='application/json')
            if response.status_code == 200:
                data = response.json()
                if 'response' in data:
                    self.log_test("Chat", True, "AI response generated")
                else:
                    self.log_test("Chat", False, "No response data found")
            else:
                self.log_test("Chat", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Chat", False, f"Error: {str(e)}")
    
    def test_development(self):
        """Test development endpoints"""
        self.stdout.write("\n=== Testing Development ===")
        
        # Test version info
        try:
            response = self.client.get('/advisor/dev/version/')
            if response.status_code == 200:
                data = response.json()
                if 'version' in data:
                    self.log_test("Version Info", True, f"Version: {data['version']}")
                else:
                    self.log_test("Version Info", False, "No version data found")
            else:
                self.log_test("Version Info", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Version Info", False, f"Error: {str(e)}")
