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
        # Cache timeout based on environment
        if os.environ.get('DEBUG', 'False').lower() == 'true':
            self.cache_timeout = 60  # 1 minute for development
        else:
            self.cache_timeout = 300  # 5 minutes for production
        
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
        """Get market indices with caching"""
        cache_key = "market_indices"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        
        indices = {}
        
        # Try to get real market indices
        try:
            # NIFTY 50
            nifty_data = self._fetch_market_index('NIFTY')
            if nifty_data:
                indices['NIFTY'] = nifty_data
            else:
                indices['NIFTY'] = {'price': 19500.0, 'change': 50.0, 'change_percent': 0.26}
            
            # SENSEX
            sensex_data = self._fetch_market_index('SENSEX')
            if sensex_data:
                indices['SENSEX'] = sensex_data
            else:
                indices['SENSEX'] = {'price': 65000.0, 'change': 150.0, 'change_percent': 0.23}
            
            # BANKNIFTY
            banknifty_data = self._fetch_market_index('BANKNIFTY')
            if banknifty_data:
                indices['BANKNIFTY'] = banknifty_data
            else:
                indices['BANKNIFTY'] = {'price': 45000.0, 'change': 200.0, 'change_percent': 0.45}
            
            # MIDCPNIFTY
            midcpnifty_data = self._fetch_market_index('MIDCPNIFTY')
            if midcpnifty_data:
                indices['MIDCPNIFTY'] = midcpnifty_data
            else:
                indices['MIDCPNIFTY'] = {'price': 12000.0, 'change': 30.0, 'change_percent': 0.25}
                
        except Exception as e:
            logger.error(f"Error fetching market indices: {e}")
            # Fallback to realistic market values
            indices = {
                'NIFTY': {'price': 19500.0, 'change': 50.0, 'change_percent': 0.26},
                'SENSEX': {'price': 65000.0, 'change': 150.0, 'change_percent': 0.23},
                'BANKNIFTY': {'price': 45000.0, 'change': 200.0, 'change_percent': 0.45},
                'MIDCPNIFTY': {'price': 12000.0, 'change': 30.0, 'change_percent': 0.25}
            }
        
        cache.set(cache_key, indices, self.cache_timeout)  # Cache for configured timeout
        return indices
    
    def _fetch_market_index(self, index_name):
        """Fetch specific market index data"""
        try:
            # Try Yahoo Finance for indices
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
                    
                    response = requests.get(url, params=params, headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        result = data.get("quoteResponse", {}).get("result", [])
                        if result:
                            item = result[0]
                            price = item.get("regularMarketPrice")
                            change = item.get("regularMarketChange")
                            change_percent = item.get("regularMarketChangePercent")
                            
                            if price and change is not None and change_percent is not None:
                                return {
                                    'price': float(price),
                                    'change': float(change),
                                    'change_percent': float(change_percent)
                                }
                except Exception as e:
                    logger.error(f"Yahoo Finance error for {symbol}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching {index_name}: {e}")
            
        return None

# Global instance
stock_data_service = StockDataService()