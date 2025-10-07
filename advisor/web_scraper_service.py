import requests
from bs4 import BeautifulSoup
import re
import time
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class WebScraperService:
    """
    Web scraping service for stock prices when APIs fail
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        
    def get_stock_price(self, symbol):
        """
        Get stock price using web scraping as fallback
        """
        try:
            # Try MoneyControl first (most reliable for Indian stocks)
            price = self._scrape_moneycontrol(symbol)
            if price:
                return price
                
            # Try Yahoo Finance scraping
            price = self._scrape_yahoo_finance(symbol)
            if price:
                return price
                
            # Try Google Finance scraping
            price = self._scrape_google_finance(symbol)
            if price:
                return price
                
            logger.warning(f"Web scraping failed for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Web scraping error for {symbol}: {e}")
            return None
    
    def _scrape_moneycontrol(self, symbol):
        """Scrape MoneyControl for stock price"""
        try:
            # Map symbols to MoneyControl format
            symbol_map = {
                'RELIANCE': 'reliance-industries',
                'TCS': 'tcs',
                'HDFCBANK': 'hdfc-bank',
                'INFOSYS': 'infosys',
                'ITC': 'itc',
                'BHARTIARTL': 'bharti-airtel',
                'MARUTI': 'maruti-suzuki',
                'ASIANPAINT': 'asian-paints',
                'WIPRO': 'wipro',
                'SBIN': 'state-bank-of-india',
                'ICICIBANK': 'icici-bank',
                'KOTAKBANK': 'kotak-mahindra-bank',
                'AXISBANK': 'axis-bank',
                'BAJFINANCE': 'bajaj-finance',
                'ULTRACEMCO': 'ultra-tech-cement',
                'NESTLEIND': 'nestle-india',
                'TITAN': 'titan-company',
                'TATAMOTORS': 'tata-motors',
                'TATAPOWER': 'tata-power',
                'TATACONSUM': 'tata-consumer-products',
                'HINDUNILVR': 'hindustan-unilever',
                'MOTHERSON': 'motherson-sumi-systems',
            }
            
            mc_symbol = symbol_map.get(symbol.upper(), symbol.lower())
            url = f"https://www.moneycontrol.com/india/stockpricequote/{mc_symbol}"
            
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for price in various selectors
                price_selectors = [
                    '.lastprice',
                    '.last-price',
                    '.pcp',
                    '.price-current',
                    '.b_52w_h',
                    '.b_52w_l'
                ]
                
                for selector in price_selectors:
                    price_elem = soup.select_one(selector)
                    if price_elem:
                        price_text = price_elem.get_text().strip()
                        # Extract numeric value
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            price = float(price_match.group())
                            logger.info(f"MoneyControl scraped price for {symbol}: {price}")
                            return price
                            
        except Exception as e:
            logger.error(f"MoneyControl scraping error for {symbol}: {e}")
            
        return None
    
    def _scrape_yahoo_finance(self, symbol):
        """Scrape Yahoo Finance for stock price"""
        try:
            # Add .NS suffix for Indian stocks
            yahoo_symbol = f"{symbol}.NS" if not symbol.endswith('.NS') else symbol
            url = f"https://finance.yahoo.com/quote/{yahoo_symbol}"
            
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for price in various selectors
                price_selectors = [
                    '[data-field="regularMarketPrice"]',
                    '.Trsdu\\(0\\.3s\\)',
                    '.Fw\\(b\\)',
                    '.Fz\\(36px\\)'
                ]
                
                for selector in price_selectors:
                    price_elem = soup.select_one(selector)
                    if price_elem:
                        price_text = price_elem.get_text().strip()
                        # Extract numeric value
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            price = float(price_match.group())
                            logger.info(f"Yahoo Finance scraped price for {symbol}: {price}")
                            return price
                            
        except Exception as e:
            logger.error(f"Yahoo Finance scraping error for {symbol}: {e}")
            
        return None
    
    def _scrape_google_finance(self, symbol):
        """Scrape Google Finance for stock price"""
        try:
            # Add exchange suffix
            google_symbol = f"{symbol}:NSE" if not ':' in symbol else symbol
            url = f"https://www.google.com/finance/quote/{google_symbol}"
            
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for price in various selectors
                price_selectors = [
                    '.YMlKec',
                    '.fxKbKc',
                    '.P2Luy',
                    '.VfPpkd'
                ]
                
                for selector in price_selectors:
                    price_elem = soup.select_one(selector)
                    if price_elem:
                        price_text = price_elem.get_text().strip()
                        # Extract numeric value
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            price = float(price_match.group())
                            logger.info(f"Google Finance scraped price for {symbol}: {price}")
                            return price
                            
        except Exception as e:
            logger.error(f"Google Finance scraping error for {symbol}: {e}")
            
        return None
    
    def get_market_data(self):
        """Get market indices using web scraping"""
        try:
            # Try NSE website for market data
            url = "https://www.nseindia.com/"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for market indices
                market_data = {}
                
                # Try to find NIFTY 50
                nifty_elem = soup.find(text=re.compile(r'NIFTY\s*50', re.I))
                if nifty_elem:
                    parent = nifty_elem.parent
                    price_elem = parent.find_next_sibling()
                    if price_elem:
                        price_text = price_elem.get_text().strip()
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            market_data['nifty_price'] = float(price_match.group())
                
                # Try to find SENSEX
                sensex_elem = soup.find(text=re.compile(r'SENSEX', re.I))
                if sensex_elem:
                    parent = sensex_elem.parent
                    price_elem = parent.find_next_sibling()
                    if price_elem:
                        price_text = price_elem.get_text().strip()
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            market_data['sensex_price'] = float(price_match.group())
                
                if market_data:
                    logger.info(f"Scraped market data: {market_data}")
                    return market_data
                    
        except Exception as e:
            logger.error(f"Market data scraping error: {e}")
            
        return None

# Global instance
web_scraper_service = WebScraperService()
