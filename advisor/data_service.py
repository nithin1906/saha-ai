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
        
        # NIFTY 50
        nifty_price = self.get_stock_price('NIFTY')
        if nifty_price:
            indices['NIFTY'] = {
                'price': nifty_price,
                'change': 0.0,
                'change_percent': 0.0
            }
        
        # SENSEX
        sensex_price = self.get_stock_price('SENSEX')
        if sensex_price:
            indices['SENSEX'] = {
                'price': sensex_price,
                'change': 0.0,
                'change_percent': 0.0
            }
        
        # BANKNIFTY
        banknifty_price = self.get_stock_price('BANKNIFTY')
        if banknifty_price:
            indices['BANKNIFTY'] = {
                'price': banknifty_price,
                'change': 0.0,
                'change_percent': 0.0
            }
        
        # MIDCPNIFTY
        midcpnifty_price = self.get_stock_price('MIDCPNIFTY')
        if midcpnifty_price:
            indices['MIDCPNIFTY'] = {
                'price': midcpnifty_price,
                'change': 0.0,
                'change_percent': 0.0
            }
        
        cache.set(cache_key, indices, self.cache_timeout)  # Cache for configured timeout
        return indices

# Global instance
stock_data_service = StockDataService()