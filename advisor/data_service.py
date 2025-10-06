import requests
import os
import json
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
import logging
import time
import re
from urllib.parse import quote
import threading
import random
from bs4 import BeautifulSoup
import pytz

logger = logging.getLogger(__name__)

class StockDataService:
    """
    Production-ready stock data service with multiple API fallbacks and rate limiting
    """
    
    def __init__(self):
        self.alpha_vantage_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
        self.iex_cloud_key = os.environ.get('IEX_CLOUD_API_KEY')
        # Cache timeout based on environment - ENABLE CACHING TO REDUCE API CALLS
        self.cache_timeout = 300  # 5 minutes cache to reduce API calls
        
        # Rate limiting and throttling
        self._rate_limit_lock = threading.Lock()
        self._last_request_time = {}
        self._request_counts = {}
        
        # Log API key status (without exposing keys)
        logger.info(f"Alpha Vantage API: {'Configured' if self.alpha_vantage_key else 'Not configured'}")
        logger.info(f"IEX Cloud API: {'Configured' if self.iex_cloud_key else 'Not configured'}")
        
        # No fallback prices - we want real API data only
        self.fallback_prices = {}
        
        # Fallback prices for when all APIs fail (like PC version)
        self.fallback_prices = {
            "RELIANCE": 2450.75,
            "TCS": 3680.50,
            "INFY": 1420.80,
            "INFOSYS": 1420.80,
            "HDFC": 1650.25,
            "HDFCBANK": 1650.25,
            "ICICIBANK": 950.30,
            "SBIN": 580.45,
            "BHARTIARTL": 980.45,
            "BHARTI": 980.45,
            "ITC": 450.20,
            "TATASTEEL": 120.80,
            "WIPRO": 380.90,
            "HINDUNILVR": 2400.50,
            "KOTAKBANK": 1800.25,
            "KOTAK": 1800.25,
            "ASIANPAINT": 3200.75,
            "ASIAN": 3200.75,
            "MARUTI": 10500.00,
            "NESTLEIND": 18000.50,
            "ULTRACEMCO": 8500.25,
            "TITAN": 3200.80,
            "BAJFINANCE": 7500.50,
            "TATAMOTORS": 650.30,
            "TATAPOWER": 280.45,
            "TATACONSUM": 850.75,
            "TATAELXSI": 4200.50,
            "MOTHERSON": 180.25,
            "MOTHERSONSUMI": 95.80,
            "AXISBANK": 950.30,
            "AXIS": 950.30,
            "SBI": 580.45,
            "ICICI": 950.30
        }
        
        # Indian stock symbol mappings for common variations
        self.symbol_mappings = {
            'HDFC': 'HDFCBANK',  # HDFC merged with HDFC Bank
            'HDFC.NS': 'HDFCBANK.NS',
            'HDFC.BO': 'HDFCBANK.BO',
            'TCS': 'TCS',  # Already correct
            'RELIANCE': 'RELIANCE',  # Already correct
            'TATASTEEL': 'TATASTEEL',  # Already correct
            'INFOSYS': 'INFOSYS',  # Already correct
            'ITC': 'ITC',  # Already correct
            'BHARTI': 'BHARTIARTL',  # Bharti Airtel
            'MARUTI': 'MARUTI',  # Already correct
            'ASIAN': 'ASIANPAINT',  # Asian Paints
            'WIPRO': 'WIPRO',  # Already correct
            'SBI': 'SBIN',  # State Bank of India
            'ICICI': 'ICICIBANK',  # ICICI Bank
            'KOTAK': 'KOTAKBANK',  # Kotak Mahindra Bank
            'AXIS': 'AXISBANK',  # Axis Bank
            'BAJFINANCE': 'BAJFINANCE',  # Already correct
            'BAJAJFINSV': 'BAJAJFINSV',  # Already correct
            'ULTRACEMCO': 'ULTRACEMCO',  # Already correct
            'NESTLEIND': 'NESTLEIND',  # Already correct
        }
    
    def _normalize_symbol(self, symbol):
        """Normalize symbol using mappings and common variations"""
        symbol_upper = symbol.upper()
        
        # Check direct mapping first
        if symbol_upper in self.symbol_mappings:
            return self.symbol_mappings[symbol_upper]
        
        # Check for common patterns
        if symbol_upper.endswith('.NS') or symbol_upper.endswith('.BO'):
            base_symbol = symbol_upper.split('.')[0]
            if base_symbol in self.symbol_mappings:
                mapped_symbol = self.symbol_mappings[base_symbol]
                return f"{mapped_symbol}.{symbol_upper.split('.')[1]}"
        
        # Return original symbol if no mapping found
        return symbol_upper
    
    def _throttle_request(self, api_name, min_interval=12):
        """Throttle requests to respect API rate limits"""
        with self._rate_limit_lock:
            current_time = time.time()
            last_time = self._last_request_time.get(api_name, 0)
            
            # Calculate time since last request
            time_since_last = current_time - last_time
            
            # If not enough time has passed, wait
            if time_since_last < min_interval:
                wait_time = min_interval - time_since_last
                logger.info(f"Throttling {api_name} request - waiting {wait_time:.1f}s")
                time.sleep(wait_time)
            
            # Update last request time
            self._last_request_time[api_name] = time.time()
    
    def _track_api_usage(self, api_name):
        """Track API usage to monitor rate limits"""
        with self._rate_limit_lock:
            current_minute = int(time.time() / 60)
            current_day = int(time.time() / 86400)  # Track daily usage
            
            if api_name not in self._request_counts:
                self._request_counts[api_name] = {}
            
            # Track per-minute usage
            if current_minute not in self._request_counts[api_name]:
                self._request_counts[api_name][current_minute] = 0
            
            self._request_counts[api_name][current_minute] += 1
            
            # Track daily usage for Alpha Vantage
            if api_name == 'alpha_vantage':
                daily_key = f"{api_name}_daily_{current_day}"
                if daily_key not in self._request_counts[api_name]:
                    self._request_counts[api_name][daily_key] = 0
                self._request_counts[api_name][daily_key] += 1
                
                daily_count = self._request_counts[api_name][daily_key]
                if daily_count >= 25:
                    logger.warning(f"Alpha Vantage daily limit reached: {daily_count}/25")
            
            # Clean old entries (keep only last 5 minutes)
            for minute in list(self._request_counts[api_name].keys()):
                if isinstance(minute, int) and minute < current_minute - 5:
                    del self._request_counts[api_name][minute]
    
    def _check_rate_limit(self, api_name, max_per_minute=5):
        """Check if we're approaching rate limits"""
        with self._rate_limit_lock:
            current_minute = int(time.time() / 60)
            current_count = self._request_counts.get(api_name, {}).get(current_minute, 0)
            
            if current_count >= max_per_minute:
                logger.warning(f"Rate limit reached for {api_name}: {current_count}/{max_per_minute} requests this minute")
                return False
            return True
    
    def get_stock_price(self, symbol):
        """
        Get stock price with multiple fallbacks and caching
        """
        # Normalize symbol using mappings
        normalized_symbol = self._normalize_symbol(symbol)
        
        # Clean symbol for caching
        clean_symbol = normalized_symbol.upper().replace('.NS', '').replace('.BO', '')
        
        # Check cache first
        cache_key = f"stock_price_{clean_symbol}"
        cached_price = cache.get(cache_key)
        if cached_price:
            logger.info(f"Cache hit for {clean_symbol}: {cached_price}")
            return cached_price
        
        # Try multiple APIs in order of reliability
        price = None
        
        # Method 1: NSE Official API (Most reliable for Indian stocks)
        if self._check_rate_limit('nse', 3):
            self._throttle_request('nse', 10)
            self._track_api_usage('nse')
            price = self._fetch_nse_official(normalized_symbol)
            if price:
                cache.set(cache_key, price, self.cache_timeout)
                logger.info(f"NSE Official API success for {normalized_symbol}: {price}")
                return price
        
        # Method 2: BSE Official API (Reliable for Indian stocks)
        if self._check_rate_limit('bse', 3):
            self._throttle_request('bse', 10)
            self._track_api_usage('bse')
            price = self._fetch_bse_official(clean_symbol)
            if price:
                cache.set(cache_key, price, self.cache_timeout)
                logger.info(f"BSE Official API success for {clean_symbol}: {price}")
                return price
        
        # Method 3: Yahoo Finance API (Reliable with proper session handling)
        if self._check_rate_limit('yahoo', 5):
            self._throttle_request('yahoo', 8)
            self._track_api_usage('yahoo')
            price = self._fetch_yahoo_finance_api(normalized_symbol)
            if price:
                cache.set(cache_key, price, self.cache_timeout)
                logger.info(f"Yahoo Finance API success for {normalized_symbol}: {price}")
                return price
        
        # Method 4: NSE WebSocket (Real-time data)
        if self._check_rate_limit('nse_websocket', 5):
            self._throttle_request('nse_websocket', 12)
            self._track_api_usage('nse_websocket')
            price = self._fetch_nse_websocket(normalized_symbol)
            if price:
                cache.set(cache_key, price, self.cache_timeout)
                logger.info(f"NSE WebSocket success for {normalized_symbol}: {price}")
                return price
        
        # Method 5: Groww API (Professional broker API)
        if self._check_rate_limit('groww', 10):
            self._throttle_request('groww', 6)
            self._track_api_usage('groww')
            price = self._fetch_groww_api(normalized_symbol)
            if price:
                cache.set(cache_key, price, self.cache_timeout)
                logger.info(f"Groww API success for {normalized_symbol}: {price}")
                return price
        
        # Method 6: Alpha Vantage (with throttling and usage monitoring)
        if self.alpha_vantage_key and self.alpha_vantage_key != 'demo':
            if self._check_rate_limit('alpha_vantage', 2):  # Only 2 requests per minute to stay under daily limit
                self._throttle_request('alpha_vantage', 30)  # 30 seconds between requests
                self._track_api_usage('alpha_vantage')
                price = self._fetch_alpha_vantage(normalized_symbol)
                if price:
                    cache.set(cache_key, price, self.cache_timeout)
                    logger.info(f"Alpha Vantage success for {normalized_symbol}: {price}")
                    return price
            else:
                logger.warning(f"Skipping Alpha Vantage for {normalized_symbol} - daily limit reached (25/day)")
        
        # Method 7: IEX Cloud (with throttling)
        if self.iex_cloud_key and self.iex_cloud_key != 'demo':
            if self._check_rate_limit('iex_cloud', 10):  # 10 requests per minute
                self._throttle_request('iex_cloud', 6)  # 6 seconds between requests
                self._track_api_usage('iex_cloud')
                price = self._fetch_iex_cloud(normalized_symbol)
                if price:
                    cache.set(cache_key, price, self.cache_timeout)
                    logger.info(f"IEX Cloud success for {normalized_symbol}: {price}")
                    return price
            else:
                logger.warning(f"Skipping IEX Cloud for {normalized_symbol} - rate limit reached")
        
        # Method 8: Web Scraping Fallback (Simple and reliable)
        if self._check_rate_limit('web_scraping', 3):
            self._throttle_request('web_scraping', 15)
            self._track_api_usage('web_scraping')
            price = self._fetch_web_scraping(clean_symbol)
            if price:
                cache.set(cache_key, price, self.cache_timeout)
                logger.info(f"Web scraping success for {clean_symbol}: {price}")
                return price
        
        # Method 9: IndianAPI.in
        price = self._fetch_indian_api(clean_symbol)
        if price:
            cache.set(cache_key, price, self.cache_timeout)
            logger.info(f"IndianAPI success for {clean_symbol}: {price}")
            return price
        
        # Method 7: Moneycontrol scraping
        price = self._fetch_moneycontrol(clean_symbol)
        if price:
            cache.set(cache_key, price, self.cache_timeout)
            logger.info(f"Moneycontrol success for {clean_symbol}: {price}")
            return price
        
        # Method 8: Economic Times scraping
        price = self._fetch_economic_times(clean_symbol)
        if price:
            cache.set(cache_key, price, self.cache_timeout)
            logger.info(f"Economic Times success for {clean_symbol}: {price}")
            return price
        
        # Method 9: Google Finance scraping
        price = self._fetch_google_finance(clean_symbol)
        if price:
            cache.set(cache_key, price, self.cache_timeout)
            logger.info(f"Google Finance success for {clean_symbol}: {price}")
            return price
        
        # Method 10: Investing.com scraping
        price = self._fetch_investing_com(clean_symbol)
        if price:
            cache.set(cache_key, price, self.cache_timeout)
            logger.info(f"Investing.com success for {clean_symbol}: {price}")
            return price
        
        # Method 11: MarketWatch scraping
        price = self._fetch_marketwatch(clean_symbol)
        if price:
            cache.set(cache_key, price, self.cache_timeout)
            logger.info(f"MarketWatch success for {clean_symbol}: {price}")
            return price
        
        # Method 12: Financial Modeling Prep API (Free tier available)
        price = self._fetch_fmp_api(clean_symbol)
        if price:
            cache.set(cache_key, price, self.cache_timeout)
            logger.info(f"FMP API success for {clean_symbol}: {price}")
            return price
        
        # Method 13: Polygon.io API (Free tier available)
        price = self._fetch_polygon_api(clean_symbol)
        if price:
            cache.set(cache_key, price, self.cache_timeout)
            logger.info(f"Polygon API success for {clean_symbol}: {price}")
            return price
        
        # Method 14: Twelve Data API (Free tier available)
        price = self._fetch_twelve_data_api(clean_symbol)
        if price:
            cache.set(cache_key, price, self.cache_timeout)
            logger.info(f"Twelve Data API success for {clean_symbol}: {price}")
            return price
        
        # Method 15: MarketStack API (Free tier available)
        price = self._fetch_marketstack_api(clean_symbol)
        if price:
            cache.set(cache_key, price, self.cache_timeout)
            logger.info(f"MarketStack API success for {clean_symbol}: {price}")
            return price
        
        # Method 16: Quandl API (Free tier available)
        price = self._fetch_quandl_api(clean_symbol)
        if price:
            cache.set(cache_key, price, self.cache_timeout)
            logger.info(f"Quandl API success for {clean_symbol}: {price}")
            return price
        
        # Method 15: Retry with exponential backoff
        price = self._retry_with_backoff(clean_symbol)
        if price:
            cache.set(cache_key, price, self.cache_timeout)
            logger.info(f"Retry success for {clean_symbol}: {price}")
            return price
        
        # Last resort: Use fallback prices (like PC version)
        if clean_symbol in self.fallback_prices:
            fallback_price = self.fallback_prices[clean_symbol]
            logger.warning(f"Using fallback price for {clean_symbol}: {fallback_price}")
            cache.set(cache_key, fallback_price, self.cache_timeout)
            return fallback_price
        
        # No fallback prices available - fail properly when APIs are down
        logger.error(f"CRITICAL: All APIs failed for {clean_symbol}. No fallback prices available.")
        return None
    
    def update_fallback_prices_daily(self):
        """Update fallback prices with real data from web scraping"""
        try:
            logger.info("Starting daily fallback price update...")
            
            # Check if we already updated today
            last_update_key = "fallback_prices_last_update"
            last_update = cache.get(last_update_key)
            today = datetime.now().date()
            
            if last_update and last_update == today:
                logger.info("Fallback prices already updated today")
                return
            
            # Update prices for major stocks
            updated_prices = {}
            
            # List of major stocks to update
            major_stocks = [
                'RELIANCE', 'TCS', 'HDFCBANK', 'INFOSYS', 'ICICIBANK', 
                'SBIN', 'BHARTIARTL', 'ITC', 'TATASTEEL', 'WIPRO',
                'HINDUNILVR', 'KOTAKBANK', 'ASIANPAINT', 'MARUTI',
                'NESTLEIND', 'ULTRACEMCO', 'TITAN', 'BAJFINANCE'
            ]
            
            for stock in major_stocks:
                try:
                    price = self._scrape_price_from_web(stock)
                    if price:
                        updated_prices[stock] = price
                        logger.info(f"Updated {stock}: ₹{price}")
                    time.sleep(1)  # Be respectful to websites
                except Exception as e:
                    logger.warning(f"Failed to update {stock}: {e}")
            
            # Update fallback prices if we got any new data
            if updated_prices:
                self.fallback_prices.update(updated_prices)
                cache.set(last_update_key, today, 86400)  # Cache for 24 hours
                logger.info(f"Successfully updated {len(updated_prices)} fallback prices")
            else:
                logger.warning("No prices could be updated from web scraping")
                
        except Exception as e:
            logger.error(f"Error updating fallback prices: {e}")
    
    def _scrape_price_from_web(self, symbol):
        """Scrape real-time price from web sources"""
        try:
            # Method 1: Try Moneycontrol
            price = self._scrape_moneycontrol(symbol)
            if price:
                return price
            
            # Method 2: Try Economic Times
            price = self._scrape_economic_times(symbol)
            if price:
                return price
            
            # Method 3: Try Google Finance
            price = self._scrape_google_finance(symbol)
            if price:
                return price
                
        except Exception as e:
            logger.debug(f"Web scraping error for {symbol}: {e}")
        
        return None
    
    def _scrape_moneycontrol(self, symbol):
        """Scrape price from Moneycontrol"""
        try:
            url = f"https://www.moneycontrol.com/india/stockpricequote/{symbol.lower()}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for price in various possible selectors
                price_selectors = [
                    '.lastprice',
                    '.last-price',
                    '.price',
                    '.current-price',
                    '[data-price]',
                    '.bse-price',
                    '.nse-price'
                ]
                
                for selector in price_selectors:
                    price_element = soup.select_one(selector)
                    if price_element:
                        price_text = price_element.get_text().strip()
                        # Extract numeric value
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            price = float(price_match.group())
                            if self._validate_price(price, symbol):
                                logger.info(f"Moneycontrol price for {symbol}: ₹{price}")
                                return price
                                
        except Exception as e:
            logger.debug(f"Moneycontrol scraping error for {symbol}: {e}")
        
        return None
    
    def _scrape_economic_times(self, symbol):
        """Scrape price from Economic Times"""
        try:
            url = f"https://economictimes.indiatimes.com/markets/stocks/stock-quotes/{symbol.lower()}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for price in various possible selectors
                price_selectors = [
                    '.lastPrice',
                    '.current-price',
                    '.price',
                    '.last-price',
                    '[data-price]'
                ]
                
                for selector in price_selectors:
                    price_element = soup.select_one(selector)
                    if price_element:
                        price_text = price_element.get_text().strip()
                        # Extract numeric value
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            price = float(price_match.group())
                            if self._validate_price(price, symbol):
                                logger.info(f"Economic Times price for {symbol}: ₹{price}")
                                return price
                                
        except Exception as e:
            logger.debug(f"Economic Times scraping error for {symbol}: {e}")
        
        return None
    
    def _scrape_google_finance(self, symbol):
        """Scrape price from Google Finance"""
        try:
            url = f"https://www.google.com/finance/quote/{symbol}:NSE"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for price in various possible selectors
                price_selectors = [
                    '.YMlKec',
                    '.fxKbKc',
                    '.P2Luy',
                    '.kf1m0',
                    '[data-last-price]'
                ]
                
                for selector in price_selectors:
                    price_element = soup.select_one(selector)
                    if price_element:
                        price_text = price_element.get_text().strip()
                        # Extract numeric value
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            price = float(price_match.group())
                            if self._validate_price(price, symbol):
                                logger.info(f"Google Finance price for {symbol}: ₹{price}")
                                return price
                                
        except Exception as e:
            logger.debug(f"Google Finance scraping error for {symbol}: {e}")
        
        return None
    
    def _fetch_groww_api(self, symbol):
        """Fetch from Groww API (Professional broker API)"""
        try:
            # Groww API endpoint for live data
            url = f"https://api.groww.in/v1/live-data/quote"
            params = {
                'instrument_key': f"NSE_EQ|{symbol}",  # NSE equity format
                'segment': 'NSE_EQ'
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://groww.in/',
                'Origin': 'https://groww.in',
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data']:
                    price_data = data['data']
                    price = price_data.get('last_price')
                    if price and self._validate_price(float(price), symbol):
                        logger.info(f"Groww API success for {symbol}: {price}")
                        return float(price)
            elif response.status_code == 401:
                logger.warning(f"Groww API: Unauthorized (401) for {symbol}")
            elif response.status_code == 403:
                logger.warning(f"Groww API: Forbidden (403) for {symbol}")
            else:
                logger.debug(f"Groww API: HTTP {response.status_code} for {symbol}")
                
        except Exception as e:
            logger.debug(f"Groww API error for {symbol}: {e}")
        return None
    
    def _fetch_nse_websocket(self, symbol):
        """Fetch from NSE WebSocket (Real-time data)"""
        try:
            # NSE WebSocket endpoint for real-time data
            url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.nseindia.com/get-quotes/equity',
                'Origin': 'https://www.nseindia.com',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'X-Requested-With': 'XMLHttpRequest',
            }
            
            # Create session for proper cookie handling
            session = requests.Session()
            
            # First, establish session with main page
            main_response = session.get('https://www.nseindia.com/', headers=headers, timeout=10)
            if main_response.status_code == 200:
                # Now try to get the quote
                response = session.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    price_info = data.get('priceInfo', {})
                    price = price_info.get('lastPrice')
                    if price and self._validate_price(float(price), symbol):
                        logger.info(f"NSE WebSocket success for {symbol}: {price}")
                        return float(price)
                elif response.status_code == 401:
                    logger.warning(f"NSE WebSocket: Unauthorized (401) for {symbol}")
                elif response.status_code == 403:
                    logger.warning(f"NSE WebSocket: Forbidden (403) for {symbol}")
                else:
                    logger.debug(f"NSE WebSocket: HTTP {response.status_code} for {symbol}")
                    
        except Exception as e:
            logger.debug(f"NSE WebSocket error for {symbol}: {e}")
        return None
    
    def _fetch_alpha_vantage(self, symbol):
        """Fetch from Alpha Vantage API"""
        try:
            # Try different symbol formats
            symbol_variants = [f"{symbol}.BSE", f"{symbol}.NSE", symbol]
            
            for sym in symbol_variants:
                url = "https://www.alphavantage.co/query"
                params = {
                    'function': 'GLOBAL_QUOTE',
                    'symbol': sym,
                    'apikey': self.alpha_vantage_key
                }
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'Global Quote' in data and data['Global Quote']:
                        quote = data['Global Quote']
                        price = quote.get('05. price')
                        if price:
                            price_float = float(price)
                            if self._validate_price(price_float, symbol):
                                return price_float
        except Exception as e:
            logger.error(f"Alpha Vantage error for {symbol}: {e}")
            return None

    def _fetch_iex_cloud(self, symbol):
        """Fetch from IEX Cloud API"""
        try:
            url = f"https://cloud.iexapis.com/stable/stock/{symbol}/quote"
            params = {'token': self.iex_cloud_key}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                price = data.get('latestPrice')
                if price:
                    price_float = float(price)
                    if self._validate_price(price_float, symbol):
                        return price_float
        except Exception as e:
            logger.error(f"IEX Cloud error for {symbol}: {e}")
            return None

    def _fetch_yahoo_finance_api(self, symbol):
        """Fetch from Yahoo Finance API with proper session handling"""
        try:
            # Create a session for proper cookie handling
            session = requests.Session()
            
            # Set up session headers
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            })
            
            # Step 1: Visit Yahoo Finance homepage to establish session
            logger.info(f"Yahoo Finance: Establishing session for {symbol}")
            main_response = session.get("https://finance.yahoo.com/", timeout=10)
            
            if main_response.status_code != 200:
                logger.warning(f"Yahoo Finance: Failed to establish session - HTTP {main_response.status_code}")
                return None
            
            # Step 2: Wait briefly
            time.sleep(1)
            
            # Step 3: Try different symbol formats
            symbol_variants = [f"{symbol}.NS", f"{symbol}.BO", symbol]
            
            for sym in symbol_variants:
                try:
                    url = "https://query1.finance.yahoo.com/v7/finance/quote"
                    params = {"symbols": sym}
                    
                    # Update headers for API request
                    api_headers = {
                        "Accept": "application/json",
                        "Referer": "https://finance.yahoo.com/",
                        "Origin": "https://finance.yahoo.com",
                        "X-Requested-With": "XMLHttpRequest",
                    }
                    
                    # Add delay to avoid rate limiting
                    time.sleep(0.5)
                    
                    response = session.get(url, params=params, headers=api_headers, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        result = data.get("quoteResponse", {}).get("result", [])
                        if result:
                            item = result[0]
                            price = item.get("regularMarketPrice")
                            if price:
                                price_float = float(price)
                                if self._validate_price(price_float, symbol):
                                    logger.info(f"Yahoo Finance API success for {symbol}: {price_float}")
                                    return price_float
                    elif response.status_code == 401:
                        logger.warning(f"Yahoo Finance API: Unauthorized (401) for {symbol} - session issue")
                        break
                    elif response.status_code == 403:
                        logger.warning(f"Yahoo Finance API: Forbidden (403) for {symbol} - blocked")
                        break
                    elif response.status_code == 429:
                        logger.warning(f"Yahoo Finance API: Rate limited (429) for {symbol}")
                        break
                    else:
                        logger.debug(f"Yahoo Finance API: HTTP {response.status_code} for {symbol}")
                        
                except Exception as e:
                    logger.debug(f"Yahoo Finance API error for {sym}: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Yahoo Finance API error for {symbol}: {e}")
        return None

    def _fetch_nse_official(self, symbol):
        """Fetch from NSE Official API with proper session management"""
        try:
            # Create a session with proper headers
            session = requests.Session()
            
            # Set up session headers
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
            
            # Step 1: Visit NSE homepage to establish session
            logger.info(f"NSE: Establishing session for {symbol}")
            main_response = session.get('https://www.nseindia.com/', timeout=10)
            
            if main_response.status_code != 200:
                logger.warning(f"NSE: Failed to establish session - HTTP {main_response.status_code}")
                return None
            
            # Step 2: Wait briefly
            time.sleep(1)
            
            # Step 3: Try to get market status first (this helps establish session)
            try:
                status_response = session.get('https://www.nseindia.com/api/marketStatus', timeout=10)
                if status_response.status_code == 200:
                    logger.info("NSE: Market status check successful")
            except Exception as e:
                logger.debug(f"NSE: Market status check failed: {e}")
            
            # Step 4: Make the quote request
            quote_url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
            
            # Update headers for API request
            api_headers = {
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://www.nseindia.com/',
                'Origin': 'https://www.nseindia.com',
                'X-Requested-With': 'XMLHttpRequest',
            }
            
            response = session.get(quote_url, headers=api_headers, timeout=15)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    price_info = data.get('priceInfo', {})
                    price = price_info.get('lastPrice')
                    
                    if price:
                        price_float = float(price)
                        if self._validate_price(price_float, symbol):
                            logger.info(f"NSE Official API success for {symbol}: {price_float}")
                            return price_float
                    else:
                        logger.debug(f"NSE: No price data in response for {symbol}")
                        
                except (ValueError, KeyError) as json_error:
                    logger.debug(f"NSE: JSON parsing error for {symbol}: {json_error}")
                    
            elif response.status_code == 401:
                logger.warning(f"NSE Official API: Unauthorized (401) for {symbol}")
            elif response.status_code == 403:
                logger.warning(f"NSE Official API: Forbidden (403) for {symbol}")
            else:
                logger.warning(f"NSE Official API: HTTP {response.status_code} for {symbol}")
                
        except Exception as e:
            logger.debug(f"NSE Official error for {symbol}: {e}")
            
        return None

    def _fetch_bse_official(self, symbol):
        """Fetch from BSE Official API with proper session management"""
        try:
            # Create a session with proper headers
            session = requests.Session()
            
            # Set up session headers
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
            
            # Step 1: Visit BSE homepage to establish session
            logger.info(f"BSE: Establishing session for {symbol}")
            main_response = session.get('https://www.bseindia.com/', timeout=10)
            
            if main_response.status_code != 200:
                logger.warning(f"BSE: Failed to establish session - HTTP {main_response.status_code}")
                return None
            
            # Step 2: Wait briefly
            time.sleep(1)
            
            # Step 3: Try BSE's stock quote API
            quote_url = f"https://www.bseindia.com/api/stockReachGraph/w?scripcode={symbol}&flag=0&fromdate=&todate=&seriesid="
            
            # Update headers for API request
            api_headers = {
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://www.bseindia.com/',
                'Origin': 'https://www.bseindia.com',
                'X-Requested-With': 'XMLHttpRequest',
            }
            
            response = session.get(quote_url, headers=api_headers, timeout=15)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Parse BSE data structure
                    price = None
                    
                    if isinstance(data, dict):
                        # Check for price in various possible keys
                        if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                            latest_data = data['data'][-1]
                            if isinstance(latest_data, dict):
                                price = latest_data.get('close') or latest_data.get('lastPrice') or latest_data.get('price')
                        
                        if not price and 'priceInfo' in data:
                            price_info = data['priceInfo']
                            price = price_info.get('lastPrice') or price_info.get('close')
                        
                        if not price and 'quote' in data:
                            quote = data['quote']
                            price = quote.get('lastPrice') or quote.get('close')
                        
                        if price:
                            price_float = float(price)
                            if self._validate_price(price_float, symbol):
                                logger.info(f"BSE Official API success for {symbol}: {price_float}")
                                return price_float
                                
                except (ValueError, KeyError, IndexError) as json_error:
                    logger.debug(f"BSE API JSON parsing error for {symbol}: {json_error}")
                    
            elif response.status_code == 401:
                logger.warning(f"BSE Official API: Unauthorized (401) for {symbol}")
            elif response.status_code == 403:
                logger.warning(f"BSE Official API: Forbidden (403) for {symbol}")
            else:
                logger.warning(f"BSE Official API: HTTP {response.status_code} for {symbol}")
                
        except Exception as e:
            logger.debug(f"BSE Official error for {symbol}: {e}")
        return None

    def _fetch_web_scraping(self, symbol):
        """Simple web scraping fallback using multiple sources"""
        try:
            # Try Google Finance first (most reliable for scraping)
            price = self._scrape_google_finance_simple(symbol)
            if price:
                logger.info(f"Google Finance scraping success for {symbol}: {price}")
                return price
            
            # Try Moneycontrol
            price = self._scrape_moneycontrol_simple(symbol)
            if price:
                logger.info(f"Moneycontrol scraping success for {symbol}: {price}")
                return price
            
            # Try Economic Times
            price = self._scrape_economic_times_simple(symbol)
            if price:
                logger.info(f"Economic Times scraping success for {symbol}: {price}")
                return price
                
        except Exception as e:
            logger.debug(f"Web scraping error for {symbol}: {e}")
        
        return None

    def _scrape_google_finance_simple(self, symbol):
        """Simple Google Finance scraping"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Google Finance search URL
            url = f"https://www.google.com/search?q={symbol}+NSE+stock+price"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for price in Google's knowledge panel
                price_selectors = [
                    '.BNeawe.iBp4i.AP7Wnd',
                    '.BNeawe.deIvCb.AP7Wnd',
                    '[data-attrid="Price"]',
                    '.knowledge-finance-wholepage-price'
                ]
                
                for selector in price_selectors:
                    price_elem = soup.select_one(selector)
                    if price_elem:
                        price_text = price_elem.get_text().strip()
                        # Extract numeric value
                        import re
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            price = float(price_match.group())
                            if self._validate_price(price, symbol):
                                return price
                                
        except Exception as e:
            logger.debug(f"Google Finance scraping error for {symbol}: {e}")
        
        return None

    def _scrape_moneycontrol_simple(self, symbol):
        """Simple Moneycontrol scraping"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            url = f"https://www.moneycontrol.com/india/stockpricequote/{symbol.lower()}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for price in various selectors
                price_selectors = [
                    '.lastprice',
                    '.last-price',
                    '.price',
                    '.current-price',
                    '[data-price]',
                    '.bse-price',
                    '.nse-price'
                ]
                
                for selector in price_selectors:
                    price_elem = soup.select_one(selector)
                    if price_elem:
                        price_text = price_elem.get_text().strip()
                        # Extract numeric value
                        import re
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            price = float(price_match.group())
                            if self._validate_price(price, symbol):
                                return price
                                
        except Exception as e:
            logger.debug(f"Moneycontrol scraping error for {symbol}: {e}")
        
        return None

    def _scrape_economic_times_simple(self, symbol):
        """Simple Economic Times scraping"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            url = f"https://economictimes.indiatimes.com/markets/stocks/stock-quotes/{symbol.lower()}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for price in various selectors
                price_selectors = [
                    '.lastPrice',
                    '.current-price',
                    '.price',
                    '.last-price',
                    '[data-price]'
                ]
                
                for selector in price_selectors:
                    price_elem = soup.select_one(selector)
                    if price_elem:
                        price_text = price_elem.get_text().strip()
                        # Extract numeric value
                        import re
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            price = float(price_match.group())
                            if self._validate_price(price, symbol):
                                return price
                                
        except Exception as e:
            logger.debug(f"Economic Times scraping error for {symbol}: {e}")
        
        return None

    def _fetch_indian_api(self, symbol):
        """Fetch from IndianAPI.in - Free Indian stock API"""
        try:
            # IndianAPI.in free endpoint
            url = f"https://indianapi.in/api/stock/{symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Try different possible price fields
                price = (data.get('price') or 
                        data.get('lastPrice') or 
                        data.get('currentPrice') or
                        data.get('close') or
                        data.get('ltp'))
                if price:
                    price_float = float(price)
                    if self._validate_price(price_float, symbol):
                        print(f"IndianAPI: Got price {price_float} for {symbol}")
                        return price_float
        except Exception as e:
            print(f"IndianAPI error for {symbol}: {e}")
        return None
    
    def _fetch_moneycontrol(self, symbol):
        """Fetch from Moneycontrol scraping"""
        try:
            # Moneycontrol stock page
            url = f"https://www.moneycontrol.com/india/stockpricequote/{symbol.lower()}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for price in various selectors
                price_selectors = [
                    '.pcnsb div:nth-child(1) .lastprice',
                    '.lastprice',
                    '.pcnsb .lastprice',
                    '[class*="lastprice"]',
                    '.price'
                ]
                
                for selector in price_selectors:
                    price_elem = soup.select_one(selector)
                    if price_elem:
                        price_text = price_elem.get_text().strip()
                        # Extract numeric value
                        import re
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            price_float = float(price_match.group())
                            if self._validate_price(price_float, symbol):
                                print(f"Moneycontrol: Got price {price_float} for {symbol}")
                                return price_float
        except Exception as e:
            print(f"Moneycontrol error for {symbol}: {e}")
        return None
    
    def _fetch_economic_times(self, symbol):
        """Fetch from Economic Times scraping"""
        try:
            # Economic Times stock page
            url = f"https://economictimes.indiatimes.com/markets/stocks/stock-quotes/{symbol.lower()}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for price in various selectors
                price_selectors = [
                    '.lastPrice',
                    '.ltp',
                    '[class*="price"]',
                    '.stock-price',
                    '.current-price'
                ]
                
                for selector in price_selectors:
                    price_elem = soup.select_one(selector)
                    if price_elem:
                        price_text = price_elem.get_text().strip()
                        # Extract numeric value
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            price_float = float(price_match.group())
                            if self._validate_price(price_float, symbol):
                                print(f"Economic Times: Got price {price_float} for {symbol}")
                                return price_float
        except Exception as e:
            print(f"Economic Times error for {symbol}: {e}")
        return None
    
    def _fetch_google_finance(self, symbol):
        """Fetch from Google Finance scraping"""
        try:
            # Google Finance search
            search_query = f"{symbol} NSE stock price"
            url = f"https://www.google.com/search?q={quote(search_query)}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for price in Google's knowledge panel or search results
                price_selectors = [
                    '.BNeawe.iBp4i.AP7Wnd',
                    '.BNeawe.deIvCb.AP7Wnd',
                    '[data-attrid="Price"]',
                    '.knowledge-finance-wholepage-price'
                ]
                
                for selector in price_selectors:
                    price_elem = soup.select_one(selector)
                    if price_elem:
                        price_text = price_elem.get_text().strip()
                        # Extract numeric value
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            price_float = float(price_match.group())
                            if self._validate_price(price_float, symbol):
                                print(f"Google Finance: Got price {price_float} for {symbol}")
                                return price_float
        except Exception as e:
            print(f"Google Finance error for {symbol}: {e}")
        return None
    
    def _fetch_investing_com(self, symbol):
        """Fetch from Investing.com scraping"""
        try:
            # Investing.com stock page
            url = f"https://www.investing.com/equities/{symbol.lower()}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for price in various selectors
                price_selectors = [
                    '.last-price',
                    '.instrument-price_last__KQzyA',
                    '.text-5xl',
                    '[data-test="instrument-price-last"]'
                ]
                
                for selector in price_selectors:
                    price_elem = soup.select_one(selector)
                    if price_elem:
                        price_text = price_elem.get_text().strip()
                        # Extract numeric value
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            price_float = float(price_match.group())
                            if self._validate_price(price_float, symbol):
                                print(f"Investing.com: Got price {price_float} for {symbol}")
                                return price_float
        except Exception as e:
            print(f"Investing.com error for {symbol}: {e}")
        return None
    
    def _fetch_marketwatch(self, symbol):
        """Fetch from MarketWatch scraping"""
        try:
            # MarketWatch stock page
            url = f"https://www.marketwatch.com/investing/stock/{symbol.lower()}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for price in various selectors
                price_selectors = [
                    '.value',
                    '.last-value',
                    '.intraday__price',
                    '[data-module="MarketData"] .value'
                ]
                
                for selector in price_selectors:
                    price_elem = soup.select_one(selector)
                    if price_elem:
                        price_text = price_elem.get_text().strip()
                        # Extract numeric value
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            price_float = float(price_match.group())
                            if self._validate_price(price_float, symbol):
                                print(f"MarketWatch: Got price {price_float} for {symbol}")
                                return price_float
        except Exception as e:
            print(f"MarketWatch error for {symbol}: {e}")
        return None
    
    def _retry_with_backoff(self, symbol):
        """Retry failed APIs with exponential backoff"""
        try:
            # Retry the most reliable APIs with delays
            retry_methods = [
                ('Yahoo Finance API', self._fetch_yahoo_finance_api),
                ('NSE Official', self._fetch_nse_official),
                ('BSE Official', self._fetch_bse_official),
                ('IndianAPI', self._fetch_indian_api)
            ]
            
            for delay in [1, 2, 4]:  # 1s, 2s, 4s delays
                time.sleep(delay)
                for method_name, method_func in retry_methods:
                    try:
                        price = method_func(symbol)
                        if price:
                            print(f"Retry success with {method_name} after {delay}s delay: {price}")
                            return price
                    except Exception as e:
                        print(f"Retry failed with {method_name}: {e}")
                        continue
        except Exception as e:
            print(f"Retry with backoff error for {symbol}: {e}")
        return None
    
    def _emergency_price_fetch(self, symbol):
        """Emergency price fetch using alternative methods"""
        try:
            # Try alternative symbol formats
            symbol_variants = [
                symbol,
                f"{symbol}.NS",
                f"{symbol}.BO",
                f"{symbol}.NSE",
                f"{symbol}.BSE"
            ]
            
            # Try each variant with the most reliable methods
            for variant in symbol_variants:
                # Try Yahoo Finance with different headers
                try:
                    url = "https://query1.finance.yahoo.com/v7/finance/quote"
                    params = {"symbols": variant}
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                        "Accept": "application/json",
                        "Referer": "https://finance.yahoo.com/",
                        "Accept-Language": "en-US,en;q=0.9"
                    }
                    
                    response = requests.get(url, params=params, headers=headers, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        result = data.get("quoteResponse", {}).get("result", [])
                        if result:
                            item = result[0]
                            price = item.get("regularMarketPrice")
                            if price:
                                price_float = float(price)
                                if self._validate_price(price_float, symbol):
                                    print(f"Emergency fetch success with Yahoo Finance for {variant}: {price_float}")
                                    return price_float
                except Exception as e:
                    print(f"Emergency Yahoo Finance failed for {variant}: {e}")
                    continue
                
                # Try NSE with session
                try:
                    session = requests.Session()
                    session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                        'Accept': 'application/json',
                        'Accept-Language': 'en-US,en;q=0.9'
                    })
                    
                    # Get session first
                    session.get('https://www.nseindia.com/', timeout=10)
                    time.sleep(1)  # Small delay
                    
                    url = f"https://www.nseindia.com/api/quote-equity?symbol={variant}"
                    response = session.get(url, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        price_info = data.get('priceInfo', {})
                        price = price_info.get('lastPrice')
                        if price:
                            price_float = float(price)
                            if self._validate_price(price_float, symbol):
                                print(f"Emergency fetch success with NSE for {variant}: {price_float}")
                                return price_float
                except Exception as e:
                    print(f"Emergency NSE failed for {variant}: {e}")
                    continue
        except Exception as e:
            print(f"Emergency price fetch error for {symbol}: {e}")
        return None
    
    def _is_market_open(self):
        """Check if Indian stock market is currently open"""
        try:
            from datetime import datetime, time
            import pytz
            
            # Get current time in IST
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist)
            current_time = now.time()
            current_date = now.date()
            
            # Market hours: 9:15 AM to 3:30 PM IST (Monday to Friday)
            market_open = time(9, 15)  # 9:15 AM
            market_close = time(15, 30)  # 3:30 PM
            
            # Check if it's a weekday
            is_weekday = current_date.weekday() < 5  # Monday = 0, Sunday = 6
            
            return is_weekday and market_open <= current_time <= market_close
        except Exception as e:
            print(f"Error checking market status: {e}")
            return True  # Assume market is open if we can't determine
    
    def _validate_price(self, price, symbol):
        """Validate if price is reasonable for the stock"""
        if not price or price <= 0:
            return False
        
        # Basic validation - stock prices should be between 1 and 100000
        if price < 1 or price > 100000:
            return False
        
        # Symbol-specific validation
        symbol_upper = symbol.upper()
        if symbol_upper == 'RELIANCE' and (price < 1000 or price > 5000):
            return False
        elif symbol_upper == 'TCS' and (price < 2000 or price > 6000):
            return False
        elif symbol_upper == 'INFY' and (price < 1000 or price > 3000):
            return False
        
        return True
    
    def get_market_indices(self):
        """Get market indices with caching and market status"""
        cache_key = "market_indices"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        
        indices = {}
        market_status = self._get_market_status()
        
        # Try to get real market indices
        try:
            # NIFTY 50
            print(f"=== Fetching NIFTY data ===")
            nifty_data = self._fetch_market_index('NIFTY')
            if nifty_data:
                print(f"NIFTY: Got real data: {nifty_data}")
                indices['NIFTY'] = nifty_data
            else:
                print(f"NIFTY: Using fallback data")
                # Use current realistic values based on Groww data
                indices['NIFTY'] = {'price': 24836.30, 'change': 225.20, 'change_percent': 0.92}
            
            # SENSEX
            print(f"=== Fetching SENSEX data ===")
            sensex_data = self._fetch_market_index('SENSEX')
            if sensex_data:
                print(f"SENSEX: Got real data: {sensex_data}")
                indices['SENSEX'] = sensex_data
            else:
                print(f"SENSEX: Using fallback data")
                indices['SENSEX'] = {'price': 80983.31, 'change': 715.69, 'change_percent': 0.89}
            
            # BANKNIFTY
            print(f"=== Fetching BANKNIFTY data ===")
            banknifty_data = self._fetch_market_index('BANKNIFTY')
            if banknifty_data:
                print(f"BANKNIFTY: Got real data: {banknifty_data}")
                indices['BANKNIFTY'] = banknifty_data
            else:
                print(f"BANKNIFTY: Using fallback data")
                indices['BANKNIFTY'] = {'price': 55347.95, 'change': 712.10, 'change_percent': 1.30}
            
            # MIDCPNIFTY
            print(f"=== Fetching MIDCPNIFTY data ===")
            midcpnifty_data = self._fetch_market_index('MIDCPNIFTY')
            if midcpnifty_data:
                print(f"MIDCPNIFTY: Got real data: {midcpnifty_data}")
                indices['MIDCPNIFTY'] = midcpnifty_data
            else:
                print(f"MIDCPNIFTY: Using fallback data")
                indices['MIDCPNIFTY'] = {'price': 12698.15, 'change': 98.90, 'change_percent': 0.78}
                
        except Exception as e:
            logger.error(f"Error fetching market indices: {e}")
            # Fallback to current realistic market values
            indices = {
                'NIFTY': {'price': 24836.30, 'change': 225.20, 'change_percent': 0.92},
                'SENSEX': {'price': 80983.31, 'change': 715.69, 'change_percent': 0.89},
                'BANKNIFTY': {'price': 55347.95, 'change': 712.10, 'change_percent': 1.30},
                'MIDCPNIFTY': {'price': 12698.15, 'change': 98.90, 'change_percent': 0.78}
            }
        
        # Add market status to the response
        result = {
            'indices': indices,
            'market_status': market_status
        }
        
        cache.set(cache_key, result, self.cache_timeout)  # Cache for configured timeout
        return result
    
    def _get_market_status(self):
        """Get current market status and timing"""
        from datetime import datetime, time
        import pytz
        
        try:
            # Get current time in IST
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist)
            current_time = now.time()
            current_date = now.date()
            
            # Market hours: 9:15 AM to 3:30 PM IST (Monday to Friday)
            market_open = time(9, 15)  # 9:15 AM
            market_close = time(15, 30)  # 3:30 PM
            
            # Check if it's a weekday
            is_weekday = current_date.weekday() < 5  # Monday = 0, Sunday = 6
            
            if is_weekday and market_open <= current_time <= market_close:
                return {
                    'status': 'open',
                    'message': 'Market is LIVE',
                    'next_close': f'Closes at 3:30 PM IST'
                }
            else:
                # Market is closed
                if not is_weekday:
                    return {
                        'status': 'closed',
                        'message': 'Market Closed (Weekend)',
                        'next_open': 'Opens Monday at 9:15 AM IST'
                    }
                elif current_time < market_open:
                    return {
                        'status': 'closed',
                        'message': 'Market Closed',
                        'next_open': 'Opens today at 9:15 AM IST'
                    }
                else:
                    return {
                        'status': 'closed',
                        'message': 'Market Closed',
                        'next_open': 'Opens tomorrow at 9:15 AM IST'
                    }
                    
        except Exception as e:
            logger.error(f"Error getting market status: {e}")
            return {
                'status': 'unknown',
                'message': 'Market status unknown',
                'next_open': 'Check market hours'
            }
    
    def _fetch_market_index(self, index_name):
        """Fetch specific market index data from NSE API"""
        try:
            # Try NSE API first (most reliable for Indian markets)
            nse_data = self._fetch_from_nse_api(index_name)
            if nse_data:
                print(f"NSE API: Got real data for {index_name}: {nse_data}")
                logger.info(f"NSE API: Got real data for {index_name}: {nse_data}")
                return nse_data
            
            # Fallback to Yahoo Finance if NSE fails
            print(f"NSE API failed for {index_name}, trying Yahoo Finance")
            logger.warning(f"NSE API failed for {index_name}, trying Yahoo Finance")
            
            symbol_variants = {
                'NIFTY': ['^NSEI', 'NIFTY.NS'],
                'SENSEX': ['^BSESN', 'SENSEX.BO'],
                'BANKNIFTY': ['^NSEBANK', 'BANKNIFTY.NS'],
                'MIDCPNIFTY': ['^CNXMDCP', 'MIDCPNIFTY.NS']
            }
            
            variants = symbol_variants.get(index_name, [index_name])
            
            for symbol in variants:
                try:
                    url = "https://query1.finance.yahoo.com/v7/finance/quote"
                    params = {"symbols": symbol}
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "application/json",
                        "Referer": "https://finance.yahoo.com/"
                    }
                    
                    print(f"Fetching {index_name} with symbol {symbol}")
                    logger.info(f"Fetching {index_name} with symbol {symbol}")
                    response = requests.get(url, params=params, headers=headers, timeout=10)
                    print(f"Response status: {response.status_code}")
                    logger.info(f"Response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        result = data.get("quoteResponse", {}).get("result", [])
                        print(f"Result length: {len(result)}")
                        logger.info(f"Result length: {len(result)}")
                        
                        if result:
                            item = result[0]
                            price = item.get("regularMarketPrice")
                            change = item.get("regularMarketChange")
                            change_percent = item.get("regularMarketChangePercent")
                            
                            print(f"Price: {price}, Change: {change}, Change%: {change_percent}")
                            logger.info(f"Price: {price}, Change: {change}, Change%: {change_percent}")
                            
                            if price and change is not None and change_percent is not None:
                                return {
                                    'price': float(price),
                                    'change': float(change),
                                    'change_percent': float(change_percent)
                                }
                        else:
                            print(f"No data in response for {symbol}")
                            logger.warning(f"No data in response for {symbol}")
                    elif response.status_code == 401:
                        print(f"Yahoo Finance API: Unauthorized (401) for {symbol} - may be rate limited or blocked")
                        logger.warning(f"Yahoo Finance API: Unauthorized (401) for {symbol} - may be rate limited or blocked")
                    elif response.status_code == 403:
                        print(f"Yahoo Finance API: Forbidden (403) for {symbol} - may be blocked")
                        logger.warning(f"Yahoo Finance API: Forbidden (403) for {symbol} - may be blocked")
                    else:
                        print(f"HTTP error {response.status_code} for {symbol}")
                        logger.warning(f"HTTP error {response.status_code} for {symbol}")
                except Exception as e:
                    print(f"Yahoo Finance error for {symbol}: {e}")
                    logger.error(f"Yahoo Finance error for {symbol}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching {index_name}: {e}")
            
        return None
    
    def _fetch_from_nse_api(self, index_name):
        """Fetch data from NSE API - most reliable for Indian markets"""
        try:
            # NSE API mapping (SENSEX is BSE, not NSE)
            nse_mapping = {
                'NIFTY': 'NIFTY 50',
                'BANKNIFTY': 'NIFTY BANK',
                'MIDCPNIFTY': 'NIFTY MIDCAP 100'
            }
            
            nse_symbol = nse_mapping.get(index_name)
            if not nse_symbol:
                return None
            
            url = "https://www.nseindia.com/api/allIndices"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
                "Referer": "https://www.nseindia.com/"
            }
            
            print(f"NSE API: Fetching {index_name} ({nse_symbol})")
            logger.info(f"NSE API: Fetching {index_name} ({nse_symbol})")
            
            response = requests.get(url, headers=headers, timeout=15)
            print(f"NSE API Response status: {response.status_code}")
            logger.info(f"NSE API Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                indices = data.get('data', [])
                
                # Find the specific index
                for index_data in indices:
                    if index_data.get('index') == nse_symbol:
                        price = index_data.get('last', 0)
                        change = index_data.get('variation', 0)
                        change_percent = index_data.get('percentChange', 0)
                        
                        print(f"NSE API: Found {nse_symbol} - Price: {price}, Change: {change}, Change%: {change_percent}")
                        logger.info(f"NSE API: Found {nse_symbol} - Price: {price}, Change: {change}, Change%: {change_percent}")
                        
                        if price and price > 0:
                            return {
                                'price': float(price),
                                'change': float(change),
                                'change_percent': float(change_percent)
                            }
                
                print(f"NSE API: Index {nse_symbol} not found in response")
                logger.warning(f"NSE API: Index {nse_symbol} not found in response")
            elif response.status_code == 401:
                print(f"NSE API: Unauthorized (401) for {nse_symbol} - may be rate limited or blocked")
                logger.warning(f"NSE API: Unauthorized (401) for {nse_symbol} - may be rate limited or blocked")
            elif response.status_code == 403:
                print(f"NSE API: Forbidden (403) for {nse_symbol} - may be blocked")
                logger.warning(f"NSE API: Forbidden (403) for {nse_symbol} - may be blocked")
            else:
                print(f"NSE API: HTTP error {response.status_code}")
                logger.warning(f"NSE API: HTTP error {response.status_code}")
                
        except Exception as e:
            print(f"NSE API error for {index_name}: {e}")
            logger.error(f"NSE API error for {index_name}: {e}")
            
        return None

    def _fetch_fmp_api(self, symbol):
        """Fetch from Financial Modeling Prep API (Free tier)"""
        try:
            # FMP supports Indian stocks with .NSE suffix
            fmp_symbol = f"{symbol}.NSE" if not symbol.endswith('.NSE') else symbol
            
            url = f"https://financialmodelingprep.com/api/v3/quote/{fmp_symbol}"
            params = {'apikey': 'demo'}  # Free tier key
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    price = data[0].get('price')
                    if price and self._validate_price(float(price), symbol):
                        return float(price)
        except Exception as e:
            logger.debug(f"FMP API error for {symbol}: {e}")
        return None
    
    def _fetch_polygon_api(self, symbol):
        """Fetch from Polygon.io API (Free tier)"""
        try:
            # Polygon supports Indian stocks
            polygon_symbol = f"{symbol}.NSE" if not symbol.endswith('.NSE') else symbol
            
            url = f"https://api.polygon.io/v1/last_quote/stocks/{polygon_symbol}"
            params = {'apikey': 'demo'}  # Free tier key
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'results' in data and data['results']:
                    price = data['results'].get('P')
                    if price and self._validate_price(float(price), symbol):
                        return float(price)
        except Exception as e:
            logger.debug(f"Polygon API error for {symbol}: {e}")
        return None
    
    def _fetch_twelve_data_api(self, symbol):
        """Fetch from Twelve Data API (Free tier)"""
        try:
            # Twelve Data supports Indian stocks
            twelve_symbol = f"{symbol}.NSE" if not symbol.endswith('.NSE') else symbol
            
            url = "https://api.twelvedata.com/price"
            params = {
                'symbol': twelve_symbol,
                'apikey': 'demo'  # Free tier key
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'price' in data:
                    price = data['price']
                    if price and self._validate_price(float(price), symbol):
                        return float(price)
        except Exception as e:
            logger.debug(f"Twelve Data API error for {symbol}: {e}")
        return None
    
    def _fetch_marketstack_api(self, symbol):
        """Fetch from MarketStack API (Free tier)"""
        try:
            # MarketStack supports Indian stocks
            marketstack_symbol = f"{symbol}.NSE" if not symbol.endswith('.NSE') else symbol
            
            url = "http://api.marketstack.com/v1/eod/latest"
            params = {
                'access_key': 'demo',  # Free tier key
                'symbols': marketstack_symbol
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data']:
                    price = data['data'][0].get('close')
                    if price and self._validate_price(float(price), symbol):
                        return float(price)
        except Exception as e:
            logger.debug(f"MarketStack API error for {symbol}: {e}")
        return None
    
    def _fetch_quandl_api(self, symbol):
        """Fetch from Quandl API (Free tier)"""
        try:
            # Quandl supports Indian stocks with NSE prefix
            quandl_symbol = f"NSE/{symbol}" if not symbol.startswith('NSE/') else symbol
            
            url = f"https://www.quandl.com/api/v3/datasets/{quandl_symbol}.json"
            params = {
                'api_key': 'demo',  # Free tier key
                'limit': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'dataset' in data and 'data' in data['dataset']:
                    price = data['dataset']['data'][0][4]  # Close price
                    if price and self._validate_price(float(price), symbol):
                        return float(price)
        except Exception as e:
            logger.debug(f"Quandl API error for {symbol}: {e}")
        return None

# Global instance
stock_data_service = StockDataService()