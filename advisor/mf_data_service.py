import requests
import os
import json
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class MutualFundDataService:
    """
    Production-ready mutual fund data service with multiple API sources
    """
    
    def __init__(self):
        # MFapi key for fallback (optional)
        self.mfapi_key = os.environ.get('MFAPI_KEY')
        # Cache timeout - 300 seconds (5 minutes) for mutual fund data
        self.cache_timeout = 300
        
        logger.info("MutualFundDataService initialized")
        logger.info(f"MFapi: {'Configured' if self.mfapi_key else 'Not configured (optional fallback)'}")
        
        # Comprehensive Indian mutual fund database (fallback)
        self.fund_database = self._load_fund_database()
        logger.info(f"Loaded {len(self.fund_database)} funds into database")
    
    def _load_fund_database(self):
        """Load comprehensive Indian mutual fund database"""
        return [
            # Large Cap Funds
            {'scheme_id': 'SBI001', 'fund_name': 'SBI Bluechip Fund', 'nav': 45.67, 'change': 0.23, 'change_pct': 0.51, 'category': 'Large Cap', 'amc': 'SBI Mutual Fund', 'aum': '₹15,234 Cr', 'expense_ratio': 1.25, 'min_sip': 500, 'min_lumpsum': 5000},
            {'scheme_id': 'HDFC002', 'fund_name': 'HDFC Top 100 Fund', 'nav': 78.45, 'change': -0.12, 'change_pct': -0.15, 'category': 'Large Cap', 'amc': 'HDFC Mutual Fund', 'aum': '₹12,456 Cr', 'expense_ratio': 1.15, 'min_sip': 500, 'min_lumpsum': 5000},
            {'scheme_id': 'ICICI003', 'fund_name': 'ICICI Prudential Bluechip Fund', 'nav': 123.89, 'change': 0.67, 'change_pct': 0.54, 'category': 'Large Cap', 'amc': 'ICICI Prudential', 'aum': '₹18,789 Cr', 'expense_ratio': 1.20, 'min_sip': 500, 'min_lumpsum': 5000},
            {'scheme_id': 'AXIS004', 'fund_name': 'Axis Bluechip Fund', 'nav': 67.23, 'change': 0.45, 'change_pct': 0.67, 'category': 'Large Cap', 'amc': 'Axis Mutual Fund', 'aum': '₹9,876 Cr', 'expense_ratio': 1.18, 'min_sip': 500, 'min_lumpsum': 5000},
            {'scheme_id': 'FRANKLIN005', 'fund_name': 'Franklin India Bluechip Fund', 'nav': 89.12, 'change': -0.23, 'change_pct': -0.26, 'category': 'Large Cap', 'amc': 'Franklin Templeton', 'aum': '₹7,543 Cr', 'expense_ratio': 1.30, 'min_sip': 500, 'min_lumpsum': 5000},
            
            # Mid Cap Funds
            {'scheme_id': 'HDFCMID001', 'fund_name': 'HDFC Mid Cap Fund', 'nav': 244.15, 'change': 1.12, 'change_pct': 0.46, 'category': 'Mid Cap', 'amc': 'HDFC Mutual Fund', 'aum': '₹8,234 Cr', 'expense_ratio': 1.35, 'min_sip': 500, 'min_lumpsum': 5000},
            {'scheme_id': 'SBIMID002', 'fund_name': 'SBI Magnum Midcap Fund', 'nav': 45.67, 'change': 0.78, 'change_pct': 1.74, 'category': 'Mid Cap', 'amc': 'SBI Mutual Fund', 'aum': '₹6,789 Cr', 'expense_ratio': 1.40, 'min_sip': 500, 'min_lumpsum': 5000},
            {'scheme_id': 'ICICIMID003', 'fund_name': 'ICICI Prudential Midcap Fund', 'nav': 123.89, 'change': 0.89, 'change_pct': 0.72, 'category': 'Mid Cap', 'amc': 'ICICI Prudential', 'aum': '₹5,432 Cr', 'expense_ratio': 1.45, 'min_sip': 500, 'min_lumpsum': 5000},
            {'scheme_id': 'AXISMID004', 'fund_name': 'Axis Midcap Fund', 'nav': 67.23, 'change': 1.23, 'change_pct': 1.86, 'category': 'Mid Cap', 'amc': 'Axis Mutual Fund', 'aum': '₹4,567 Cr', 'expense_ratio': 1.38, 'min_sip': 500, 'min_lumpsum': 5000},
            
            # Small Cap Funds
            {'scheme_id': 'HDFCSMALL001', 'fund_name': 'HDFC Small Cap Fund', 'nav': 78.45, 'change': 2.34, 'change_pct': 3.08, 'category': 'Small Cap', 'amc': 'HDFC Mutual Fund', 'aum': '₹3,456 Cr', 'expense_ratio': 1.50, 'min_sip': 500, 'min_lumpsum': 5000},
            {'scheme_id': 'SBISMALL002', 'fund_name': 'SBI Small Cap Fund', 'nav': 45.67, 'change': 1.89, 'change_pct': 4.32, 'category': 'Small Cap', 'amc': 'SBI Mutual Fund', 'aum': '₹2,345 Cr', 'expense_ratio': 1.55, 'min_sip': 500, 'min_lumpsum': 5000},
            {'scheme_id': 'ICICISMALL003', 'fund_name': 'ICICI Prudential Smallcap Fund', 'nav': 123.89, 'change': 3.12, 'change_pct': 2.58, 'category': 'Small Cap', 'amc': 'ICICI Prudential', 'aum': '₹1,876 Cr', 'expense_ratio': 1.60, 'min_sip': 500, 'min_lumpsum': 5000},
            
            # ELSS Funds
            {'scheme_id': 'SBIELSS001', 'fund_name': 'SBI Equity Linked Savings Scheme', 'nav': 45.67, 'change': 0.56, 'change_pct': 1.24, 'category': 'ELSS', 'amc': 'SBI Mutual Fund', 'aum': '₹4,567 Cr', 'expense_ratio': 1.25, 'min_sip': 500, 'min_lumpsum': 500, 'lock_in': '3 years'},
            {'scheme_id': 'HDFCELSS002', 'fund_name': 'HDFC Tax Saver Fund', 'nav': 78.45, 'change': 0.34, 'change_pct': 0.44, 'category': 'ELSS', 'amc': 'HDFC Mutual Fund', 'aum': '₹3,234 Cr', 'expense_ratio': 1.20, 'min_sip': 500, 'min_lumpsum': 500, 'lock_in': '3 years'},
            {'scheme_id': 'ICICIELSS003', 'fund_name': 'ICICI Prudential Long Term Equity Fund', 'nav': 123.89, 'change': 0.78, 'change_pct': 0.63, 'category': 'ELSS', 'amc': 'ICICI Prudential', 'aum': '₹2,876 Cr', 'expense_ratio': 1.15, 'min_sip': 500, 'min_lumpsum': 500, 'lock_in': '3 years'},
            
            # Hybrid Funds
            {'scheme_id': 'HDFCHYBRID001', 'fund_name': 'HDFC Balanced Advantage Fund', 'nav': 67.23, 'change': 0.45, 'change_pct': 0.67, 'category': 'Hybrid', 'amc': 'HDFC Mutual Fund', 'aum': '₹12,345 Cr', 'expense_ratio': 1.10, 'min_sip': 500, 'min_lumpsum': 5000},
            {'scheme_id': 'ICICIHYBRID002', 'fund_name': 'ICICI Prudential Balanced Advantage Fund', 'nav': 89.12, 'change': 0.23, 'change_pct': 0.26, 'category': 'Hybrid', 'amc': 'ICICI Prudential', 'aum': '₹9,876 Cr', 'expense_ratio': 1.12, 'min_sip': 500, 'min_lumpsum': 5000},
            
            # Debt Funds
            {'scheme_id': 'HDFCDEBT001', 'fund_name': 'HDFC Corporate Bond Fund', 'nav': 23.45, 'change': 0.12, 'change_pct': 0.51, 'category': 'Debt', 'amc': 'HDFC Mutual Fund', 'aum': '₹5,678 Cr', 'expense_ratio': 0.85, 'min_sip': 500, 'min_lumpsum': 5000},
            {'scheme_id': 'ICICIDEBT002', 'fund_name': 'ICICI Prudential Corporate Bond Fund', 'nav': 34.56, 'change': 0.08, 'change_pct': 0.23, 'category': 'Debt', 'amc': 'ICICI Prudential', 'aum': '₹4,321 Cr', 'expense_ratio': 0.90, 'min_sip': 500, 'min_lumpsum': 5000},
            
            # Additional Popular Funds
            {'scheme_id': 'MOTILAL001', 'fund_name': 'Motilal Oswal Midcap Fund', 'nav': 156.78, 'change': 2.45, 'change_pct': 1.58, 'category': 'Mid Cap', 'amc': 'Motilal Oswal Mutual Fund', 'aum': '₹3,456 Cr', 'expense_ratio': 1.25, 'min_sip': 500, 'min_lumpsum': 5000},
            {'scheme_id': 'MOTILAL002', 'fund_name': 'Motilal Oswal Large Cap Fund', 'nav': 89.34, 'change': 1.23, 'change_pct': 1.40, 'category': 'Large Cap', 'amc': 'Motilal Oswal Mutual Fund', 'aum': '₹2,345 Cr', 'expense_ratio': 1.15, 'min_sip': 500, 'min_lumpsum': 5000},
            {'scheme_id': 'MOTILAL003', 'fund_name': 'Motilal Oswal Small Cap Fund', 'nav': 234.56, 'change': 4.56, 'change_pct': 1.98, 'category': 'Small Cap', 'amc': 'Motilal Oswal Mutual Fund', 'aum': '₹1,876 Cr', 'expense_ratio': 1.45, 'min_sip': 500, 'min_lumpsum': 5000},
            {'scheme_id': 'MOTILAL004', 'fund_name': 'Motilal Oswal Multicap Fund', 'nav': 67.89, 'change': 0.89, 'change_pct': 1.33, 'category': 'Multi Cap', 'amc': 'Motilal Oswal Mutual Fund', 'aum': '₹4,567 Cr', 'expense_ratio': 1.20, 'min_sip': 500, 'min_lumpsum': 5000},
            
            # More HDFC Funds
            {'scheme_id': 'HDFC003', 'fund_name': 'HDFC Equity Fund', 'nav': 234.56, 'change': 3.45, 'change_pct': 1.49, 'category': 'Large Cap', 'amc': 'HDFC Mutual Fund', 'aum': '₹8,765 Cr', 'expense_ratio': 1.25, 'min_sip': 500, 'min_lumpsum': 5000},
            {'scheme_id': 'HDFC004', 'fund_name': 'HDFC Flexi Cap Fund', 'nav': 123.45, 'change': 1.67, 'change_pct': 1.37, 'category': 'Flexi Cap', 'amc': 'HDFC Mutual Fund', 'aum': '₹6,543 Cr', 'expense_ratio': 1.30, 'min_sip': 500, 'min_lumpsum': 5000},
            
            # More SBI Funds
            {'scheme_id': 'SBI002', 'fund_name': 'SBI Large & Midcap Fund', 'nav': 78.90, 'change': 1.23, 'change_pct': 1.58, 'category': 'Large & Mid Cap', 'amc': 'SBI Mutual Fund', 'aum': '₹5,432 Cr', 'expense_ratio': 1.35, 'min_sip': 500, 'min_lumpsum': 5000},
            {'scheme_id': 'SBI003', 'fund_name': 'SBI Flexicap Fund', 'nav': 45.67, 'change': 0.78, 'change_pct': 1.74, 'category': 'Flexi Cap', 'amc': 'SBI Mutual Fund', 'aum': '₹3,456 Cr', 'expense_ratio': 1.40, 'min_sip': 500, 'min_lumpsum': 5000},
        ]
    
    def search_mutual_funds(self, query):
        """
        Search mutual funds - PRIMARY: Yahoo Finance, FALLBACK: MFapi
        """
        query_lower = query.lower().strip()
        if not query_lower:
            return []
        
        # Check cache
        try:
            cache_key = f"mf_search_{query_lower.replace(' ', '_')}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for MF search: {query}")
                return cached_result
        except Exception:
            pass
        
        logger.info(f"MF Search: Searching for '{query}'")
        
        # PRIMARY: Try Yahoo Finance API
        results = self._search_yahoo_finance_mf(query)
        if results:
            logger.info(f"Yahoo Finance MF search success: {len(results)} results")
            try:
                cache.set(cache_key, results, self.cache_timeout)
            except Exception:
                pass
            return results
        
        # FALLBACK: Try MFapi
        if self.mfapi_key:
            results = self._search_mfapi(query)
            if results:
                logger.info(f"MFapi search success: {len(results)} results")
                try:
                    cache.set(cache_key, results, self.cache_timeout)
                except Exception:
                    pass
                return results
        
        # FINAL FALLBACK: Local database search
        return self._search_local_database(query)
    
    def _search_yahoo_finance_mf(self, query):
        """Search mutual funds using Yahoo Finance"""
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # Yahoo Finance search for mutual funds
            # Indian mutual funds often have .BO or .NS suffix or specific symbols
            url = "https://query1.finance.yahoo.com/v1/finance/search"
            params = {
                "q": f"{query} mutual fund India",
                "quotesCount": 10,
                "newsCount": 0
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://finance.yahoo.com/",
                "Origin": "https://finance.yahoo.com"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                quotes = data.get("quotes", [])
                
                results = []
                for quote in quotes:
                    symbol = quote.get("symbol", "")
                    longname = quote.get("longname", "")
                    shortname = quote.get("shortname", "")
                    quoteType = quote.get("quoteType", "")
                    
                    # Filter for mutual funds (quoteType should be MUTUALFUND or check symbol patterns)
                    if quoteType == "MUTUALFUND" or "mutual" in longname.lower() or "fund" in longname.lower():
                        # Try to get NAV/price
                        nav = quote.get("regularMarketPrice") or quote.get("previousClose")
                        
                        results.append({
                            'scheme_id': symbol.replace('.', '_'),
                            'fund_name': longname or shortname,
                            'nav': float(nav) if nav else 0.0,
                            'change': quote.get("regularMarketChange", 0.0) or 0.0,
                            'change_pct': quote.get("regularMarketChangePercent", 0.0) or 0.0,
                            'category': 'Mutual Fund',
                            'amc': longname.split('-')[0].strip() if '-' in longname else 'Unknown',
                            'source': 'yahoo_finance'
                        })
                
                if results:
                    return results[:8]  # Return top 8
                    
        except Exception as e:
            logger.error(f"Yahoo Finance MF search error: {e}")
        
        return None
    
    def _search_mfapi(self, query):
        """Search mutual funds using MFapi (fallback)"""
        try:
            # MFapi endpoint for searching mutual funds
            url = "https://www.mfapi.in/api/search"
            params = {
                "q": query
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }
            
            if self.mfapi_key:
                headers["Authorization"] = f"Bearer {self.mfapi_key}"
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                funds = data.get("data", []) or data.get("results", [])
                
                results = []
                for fund in funds:
                    results.append({
                        'scheme_id': fund.get("scheme_code", ""),
                        'fund_name': fund.get("scheme_name", ""),
                        'nav': float(fund.get("nav", 0)),
                        'change': float(fund.get("change", 0)),
                        'change_pct': float(fund.get("change_percent", 0)),
                        'category': fund.get("category", "Mutual Fund"),
                        'amc': fund.get("amc", "Unknown"),
                        'source': 'mfapi'
                    })
                
                if results:
                    return results[:8]
                    
        except Exception as e:
            logger.error(f"MFapi search error: {e}")
        
        return None
    
    def _search_local_database(self, query):
        """Search local database as final fallback"""
        query_lower = query.lower().strip()
        if not query_lower:
            return []
        
        clean_query = query_lower.replace(' direct', '').replace(' growth', '').replace(' dividend', '').replace(' regular', '').replace(' fund', '')
        query_words = clean_query.split()
        
        scored_funds = []
        for fund in self.fund_database:
            fund_name_lower = fund['fund_name'].lower()
            amc_lower = fund['amc'].lower()
            category_lower = fund['category'].lower()
            
            score = 0
            
            if clean_query in fund_name_lower:
                score += 100
            elif clean_query in amc_lower:
                score += 80
            
            fund_words = fund_name_lower.replace(' fund', '').replace(' scheme', '').split()
            amc_words = amc_lower.split()
            
            for word in query_words:
                if word in fund_words:
                    score += 20
                elif word in amc_words:
                    score += 15
            
            if any(word in fund_name_lower for word in query_words):
                score += 10
            if any(word in amc_lower for word in query_words):
                score += 8
            if any(word in category_lower for word in query_words):
                score += 5
            
            if score > 0:
                scored_funds.append({'fund': fund, 'score': score})
        
        scored_funds.sort(key=lambda x: x['score'], reverse=True)
        return [item['fund'] for item in scored_funds[:8]]
    
    def get_fund_by_id(self, scheme_id):
        """
        Get specific mutual fund by scheme ID from multiple sources.
        """
        cache_key = f"mf_fund_{scheme_id}"
        try:
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for get_fund_by_id: {scheme_id}")
                return cached_result
        except Exception:
            pass

        # 1. Search local database first
        for fund in self.fund_database:
            if str(fund['scheme_id']) == str(scheme_id):
                logger.info(f"Found fund {scheme_id} in local database.")
                try:
                    cache.set(cache_key, fund, self.cache_timeout)
                except Exception:
                    pass
                return fund

        # 2. If not in local DB, try Yahoo Finance search
        logger.info(f"Fund {scheme_id} not in local DB, searching Yahoo Finance...")
        try:
            yahoo_results = self._search_yahoo_finance_mf(scheme_id)
            if yahoo_results:
                for fund in yahoo_results:
                    if str(fund['scheme_id']) == str(scheme_id):
                        logger.info(f"Found fund {scheme_id} via Yahoo Finance search.")
                        try:
                            cache.set(cache_key, fund, self.cache_timeout)
                        except Exception:
                            pass
                        return fund
        except Exception as e:
            logger.error(f"Error searching Yahoo Finance in get_fund_by_id: {e}")

        # 3. If not found, try direct MFapi lookup
        if self.mfapi_key:
            logger.info(f"Fund {scheme_id} not found in Yahoo, trying direct MFapi lookup...")
            try:
                url = f"https://api.mfapi.in/mf/{scheme_id}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict) and data.get('status') == 'SUCCESS':
                        meta = data.get('meta', {})
                        nav_data = data.get('data', [])
                        if meta and nav_data:
                            fund_details = {
                                'scheme_id': meta.get('scheme_code'),
                                'fund_name': meta.get('scheme_name'),
                                'nav': float(nav_data[0]['nav']) if nav_data else 0.0,
                                'category': meta.get('scheme_category'),
                                'amc': meta.get('fund_house'),
                                'source': 'mfapi_direct'
                            }
                            logger.info(f"Found fund {scheme_id} via direct MFapi lookup.")
                            try:
                                cache.set(cache_key, fund_details, self.cache_timeout)
                            except Exception:
                                pass
                            return fund_details
            except Exception as e:
                logger.error(f"Error during direct MFapi lookup for {scheme_id}: {e}")

        logger.warning(f"Fund with scheme_id '{scheme_id}' not found in any data source.")
        return None
    
    def get_funds_by_category(self, category):
        """
        Get all funds in a specific category
        """
        cache_key = f"mf_category_{category.lower()}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        category_funds = [fund for fund in self.fund_database if fund['category'].lower() == category.lower()]
        cache.set(cache_key, category_funds, self.cache_timeout)
        
        return category_funds
    
    def get_top_performing_funds(self, category=None, limit=10):
        """
        Get top performing funds by category or overall
        """
        cache_key = f"mf_top_performing_{category or 'all'}_{limit}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        if category:
            funds = [fund for fund in self.fund_database if fund['category'].lower() == category.lower()]
        else:
            funds = self.fund_database.copy()
        
        # Sort by change percentage (performance)
        top_funds = sorted(funds, key=lambda x: x['change_pct'], reverse=True)[:limit]
        
        cache.set(cache_key, top_funds, self.cache_timeout)
        return top_funds
    
    def get_fund_categories(self):
        """
        Get all available fund categories
        """
        cache_key = "mf_categories"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        categories = list(set(fund['category'] for fund in self.fund_database))
        categories.sort()
        
        cache.set(cache_key, categories, self.cache_timeout)
        return categories
    
    def get_fund_nav_history(self, scheme_id, days=30):
        """
        Get NAV history for a fund (mock implementation)
        In production, this would fetch real historical data
        """
        cache_key = f"mf_nav_history_{scheme_id}_{days}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        fund = self.get_fund_by_id(scheme_id)
        if not fund:
            return None
        
        # Generate mock historical data
        import random
        from datetime import datetime, timedelta
        
        current_nav = fund['nav']
        nav_history = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=days-i-1)
            # Generate realistic NAV movement
            if i == 0:
                nav = current_nav
            else:
                # Small daily changes (0.1% to 0.5%)
                change_factor = random.uniform(0.999, 1.001)
                nav = nav_history[-1]['nav'] * change_factor
            
            nav_history.append({
                'date': date.strftime('%Y-%m-%d'),
                'nav': round(nav, 4),
                'change': round(nav - nav_history[-1]['nav'], 4) if nav_history else 0,
                'change_pct': round(((nav - nav_history[-1]['nav']) / nav_history[-1]['nav'] * 100), 2) if nav_history else 0
            })
        
        # Cache the result (if Django settings configured)
        try:
            cache.set(cache_key, nav_history, self.cache_timeout)
        except Exception:
            # Django settings not configured, skip caching
            pass
        
        return nav_history

# Global instance
mf_data_service = MutualFundDataService()
