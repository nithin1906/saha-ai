import requests
import os
import json
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class StockDataService:
    """
    Production-ready stock data service with multiple API fallbacks
    """
    
    def __init__(self):
        self.alpha_vantage_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
        self.iex_cloud_key = os.environ.get('IEX_CLOUD_API_KEY')
        # Cache timeout based on environment - DISABLED FOR DEBUGGING
        self.cache_timeout = 0  # Disable caching to get fresh data
        
        # Log API key status (without exposing keys)
        logger.info(f"Alpha Vantage API: {'Configured' if self.alpha_vantage_key else 'Not configured'}")
        logger.info(f"IEX Cloud API: {'Configured' if self.iex_cloud_key else 'Not configured'}")
        
        # Fallback prices for major Indian stocks (updated regularly)
        self.fallback_prices = {
            'RELIANCE': 1368.70,
            'TCS': 3500.0,
            'INFY': 1500.0,
            'HDFC': 1600.0,
            'ICICIBANK': 900.0,
            'SBIN': 600.0,
            'BHARTIARTL': 800.0,
            'ITC': 400.0,
            'GREENPANEL': 293.0,
            'TATASTEEL': 150.0,
            'TATAINVEST': 850.0,
            'WIPRO': 450.0,
            'HINDUNILVR': 2500.0,
            'KOTAKBANK': 1800.0,
            'ASIANPAINT': 3000.0,
            'MARUTI': 10000.0,
            'NESTLEIND': 18000.0,
            'ULTRACEMCO': 7000.0,
            'TITAN': 3000.0,
            'BAJFINANCE': 7000.0,
            'HDFCBANK': 1600.0,
        }
    
    def get_stock_price(self, symbol):
        """
        Get stock price with multiple fallbacks and caching
        """
        # Clean symbol
        clean_symbol = symbol.upper().replace('.NS', '').replace('.BO', '')
        
        # Check cache first
        cache_key = f"stock_price_{clean_symbol}"
        cached_price = cache.get(cache_key)
        if cached_price:
            logger.info(f"Cache hit for {clean_symbol}: {cached_price}")
            return cached_price
        
        # Try multiple APIs
        price = None
        
        # Method 1: Alpha Vantage
        if self.alpha_vantage_key and self.alpha_vantage_key != 'demo':
            price = self._fetch_alpha_vantage(clean_symbol)
            if price:
                cache.set(cache_key, price, self.cache_timeout)
                logger.info(f"Alpha Vantage success for {clean_symbol}: {price}")
                return price
        
        # Method 2: IEX Cloud
        if self.iex_cloud_key and self.iex_cloud_key != 'demo':
            price = self._fetch_iex_cloud(clean_symbol)
            if price:
                cache.set(cache_key, price, self.cache_timeout)
                logger.info(f"IEX Cloud success for {clean_symbol}: {price}")
                return price
        
        # Method 3: Yahoo Finance API (more reliable than yfinance)
        price = self._fetch_yahoo_finance_api(clean_symbol)
        if price:
            cache.set(cache_key, price, self.cache_timeout)
            logger.info(f"Yahoo Finance API success for {clean_symbol}: {price}")
            return price
        
        # Method 4: NSE Official API
        price = self._fetch_nse_official(clean_symbol)
        if price:
            cache.set(cache_key, price, self.cache_timeout)
            logger.info(f"NSE Official success for {clean_symbol}: {price}")
            return price
        
        # Method 5: BSE Official API
        price = self._fetch_bse_official(clean_symbol)
        if price:
            cache.set(cache_key, price, self.cache_timeout)
            logger.info(f"BSE Official success for {clean_symbol}: {price}")
            return price
        
        # Method 6: IndianAPI.in
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
        
        # Final fallback
        fallback_price = self.fallback_prices.get(clean_symbol, 100.0)
        logger.warning(f"All APIs failed for {clean_symbol}, using fallback: {fallback_price}")
        # Cache fallback for shorter time to retry APIs sooner
        cache.set(cache_key, fallback_price, 30)  # Cache fallback for 30 seconds
        return fallback_price
    
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
        """Fetch from Yahoo Finance API (more reliable)"""
        try:
            # Try different symbol formats
            symbol_variants = [f"{symbol}.NS", f"{symbol}.BO", symbol]
            
            for sym in symbol_variants:
                url = "https://query1.finance.yahoo.com/v7/finance/quote"
                params = {"symbols": sym}
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
                        if price:
                            price_float = float(price)
                            if self._validate_price(price_float, symbol):
                                return price_float
                elif response.status_code == 401:
                    logger.warning(f"Yahoo Finance API: Unauthorized (401) for {symbol} - may be rate limited or blocked")
                elif response.status_code == 403:
                    logger.warning(f"Yahoo Finance API: Forbidden (403) for {symbol} - may be blocked")
                else:
                    logger.warning(f"Yahoo Finance API: HTTP {response.status_code} for {symbol}")
        except Exception as e:
            logger.error(f"Yahoo Finance API error for {symbol}: {e}")
        return None

    def _fetch_nse_official(self, symbol):
        """Fetch from NSE Official API"""
        try:
            url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': 'https://www.nseindia.com/'
            }
            
            # Get session first
            session = requests.Session()
            session.get('https://www.nseindia.com/', headers=headers, timeout=10)
            
            response = session.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                price_info = data.get('priceInfo', {})
                price = price_info.get('lastPrice')
                if price:
                    price_float = float(price)
                    if self._validate_price(price_float, symbol):
                        return price_float
            elif response.status_code == 401:
                logger.warning(f"NSE Official API: Unauthorized (401) for {symbol} - may be rate limited or blocked")
            elif response.status_code == 403:
                logger.warning(f"NSE Official API: Forbidden (403) for {symbol} - may be blocked")
            else:
                logger.warning(f"NSE Official API: HTTP {response.status_code} for {symbol}")
        except Exception as e:
            logger.error(f"NSE Official error for {symbol}: {e}")
        return None

    def _fetch_bse_official(self, symbol):
        """Fetch from BSE Official API"""
        try:
            url = f"https://api.bseindia.com/BseIndiaAPI/api/StockReachGraph/w?scripcode={symbol}&flag=0&fromdate=&todate=&seriesid="
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # BSE API structure may vary, this is a basic implementation
                if isinstance(data, dict) and 'data' in data:
                    price_data = data['data']
                    if isinstance(price_data, list) and len(price_data) > 0:
                        latest = price_data[-1]
                        if isinstance(latest, dict) and 'close' in latest:
                            price_float = float(latest['close'])
                            if self._validate_price(price_float, symbol):
                                return price_float
        except Exception as e:
            logger.error(f"BSE Official error for {symbol}: {e}")
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

# Global instance
stock_data_service = StockDataService()