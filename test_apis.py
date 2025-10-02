#!/usr/bin/env python3
"""
Test script to verify all APIs are working correctly
"""
import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from advisor.data_service import StockDataService
import requests

def test_stock_price_apis():
    """Test stock price fetching for specific stocks"""
    print("=== Testing Stock Price APIs ===")
    
    # Set up the service
    service = StockDataService()
    
    # Test stocks
    test_stocks = ['MOTHERSON', 'TATASTEEL', 'RELIANCE', 'TCS']
    
    for stock in test_stocks:
        print(f"\n--- Testing {stock} ---")
        try:
            price = service.get_stock_price(stock)
            print(f"✅ {stock}: ₹{price}")
        except Exception as e:
            print(f"❌ {stock}: Error - {e}")

def test_market_indices():
    """Test market indices fetching"""
    print("\n=== Testing Market Indices ===")
    
    service = StockDataService()
    
    try:
        indices = service.get_market_indices()
        print(f"Market data type: {type(indices)}")
        
        if isinstance(indices, dict) and 'indices' in indices:
            print("✅ Market indices structure is correct")
            for name, data in indices['indices'].items():
                print(f"  {name}: ₹{data['price']} ({data['change']:+.2f}, {data['change_percent']:+.2f}%)")
            
            if 'market_status' in indices:
                status = indices['market_status']
                print(f"✅ Market status: {status['message']} ({status['status']})")
        else:
            print("❌ Market indices structure is incorrect")
            print(f"Data: {indices}")
            
    except Exception as e:
        print(f"❌ Market indices error: {e}")

def test_yahoo_finance_direct():
    """Test Yahoo Finance API directly"""
    print("\n=== Testing Yahoo Finance API Directly ===")
    
    test_symbols = ['MOTHERSON.NS', 'TATASTEEL.NS', 'RELIANCE.NS']
    
    for symbol in test_symbols:
        try:
            url = "https://query1.finance.yahoo.com/v7/finance/quote"
            params = {"symbols": symbol}
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Referer": "https://finance.yahoo.com/"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                result = data.get("quoteResponse", {}).get("result", [])
                if result:
                    item = result[0]
                    price = item.get("regularMarketPrice")
                    name = item.get("longName", symbol)
                    print(f"✅ {name}: ₹{price}")
                else:
                    print(f"❌ {symbol}: No data in response")
            else:
                print(f"❌ {symbol}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ {symbol}: Error - {e}")

def test_alpha_vantage():
    """Test Alpha Vantage API"""
    print("\n=== Testing Alpha Vantage API ===")
    
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY', 'C4LYL8SIKSX9YD6L')
    if not api_key or api_key == 'demo':
        print("❌ Alpha Vantage API key not set")
        return
    
    test_symbols = ['MOTHERSON.BSE', 'TATASTEEL.BSE', 'RELIANCE.BSE']
    
    for symbol in test_symbols:
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'Global Quote' in data and data['Global Quote']:
                    quote = data['Global Quote']
                    price = quote.get('05. price')
                    if price:
                        print(f"✅ {symbol}: ₹{price}")
                    else:
                        print(f"❌ {symbol}: No price in response")
                else:
                    print(f"❌ {symbol}: No Global Quote in response")
            else:
                print(f"❌ {symbol}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ {symbol}: Error - {e}")

if __name__ == "__main__":
    print("🔍 Testing SAHA-AI APIs...")
    print("=" * 50)
    
    test_stock_price_apis()
    test_market_indices()
    test_yahoo_finance_direct()
    test_alpha_vantage()
    
    print("\n" + "=" * 50)
    print("✅ API testing complete!")
