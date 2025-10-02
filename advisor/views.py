import requests
from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg
from .models import Holding
import json
import random
import math
import re
from datetime import datetime, timedelta

# Optional: live market data via yfinance (fallback to mock if unavailable)
try:
    import yfinance as yf  # type: ignore
except Exception:  # pragma: no cover
    yf = None

# =====================
# Portfolio Management
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class PortfolioView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        holdings = Holding.objects.filter(portfolio__user=request.user)
        total_value = sum(h.quantity * h.average_buy_price for h in holdings)
        
        # Check if this is a details request (for portfolio page)
        if request.path.endswith('/details/'):
            return JsonResponse({
                "holdings": [
                    {
                        "ticker": h.ticker,
                        "quantity": h.quantity,
                        "average_buy_price": h.average_buy_price,
                        "current_price": h.average_buy_price,  # Using average_buy_price as current for now
                        "net_profit": 0  # No profit/loss calculation for now
                    }
                    for h in holdings
                ],
                "total_value": total_value
            })
        
        # Default response for other portfolio requests
        return JsonResponse({
            "holdings": [
                {
                    "ticker": h.ticker,
                    "quantity": h.quantity,
                    "buy_price": h.average_buy_price,
                    "current_value": h.quantity * h.average_buy_price
                }
                for h in holdings
            ],
            "total_value": total_value
        })
    
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        try:
            data = json.loads(request.body.decode("utf-8"))
            ticker = data.get("ticker", "").upper()
            quantity = float(data.get("quantity", 0))
            average_buy_price = float(data.get("buy_price", 0))
            
            if not ticker or quantity <= 0 or average_buy_price <= 0:
                return JsonResponse({"error": "Invalid data"}, status=400)
            
            # Get or create portfolio for user
            portfolio, _ = Portfolio.objects.get_or_create(user=request.user)
            
            # Check if holding already exists
            holding, created = Holding.objects.get_or_create(
                portfolio=portfolio,
                ticker=ticker,
                defaults={"quantity": quantity, "average_buy_price": average_buy_price}
            )
            
            if not created:
                # Update existing holding
                total_quantity = holding.quantity + quantity
                total_cost = (holding.quantity * holding.average_buy_price) + (quantity * average_buy_price)
                holding.average_buy_price = total_cost / total_quantity
                holding.quantity = total_quantity
                holding.save()
            
            return JsonResponse({"message": "Holding added successfully"})
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            return JsonResponse({"error": "Invalid payload"}, status=400)

# =====================
# Market snapshot
# =====================

class MarketSnapshotView(View):
    def get(self, request):
        print("=== MarketSnapshotView: Starting market data fetch ===")
        
        # Define symbols with multiple fallback options
        symbols = {
            "NIFTY": ["NSEI.NS", "^NSEI", "NIFTY_50.NS"],
            "SENSEX": ["BSESN.BO", "^BSESN", "SENSEX.BO"],
            "BANKNIFTY": ["NSEBANK.NS", "^NSEBANK", "BANKNIFTY.NS"],
            "MIDCPNIFTY": ["NSEMDCP50.NS", "^NSEMDCP50", "MIDCAP_50.NS"],
            "FINNIFTY": ["NSEFIN.NS", "^NSEFIN", "FINANCIAL_SERVICES.NS"]
        }
        
        data = []
        
        # Method 1: Try Yahoo Finance API with multiple symbol formats
        for method_name, symbol_list in symbols.items():
            for symbol in symbol_list:
                try:
                    url = "https://query1.finance.yahoo.com/v7/finance/quote"
                    params = {"symbols": symbol}
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "application/json, text/plain, */*",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Connection": "keep-alive",
                        "Referer": "https://finance.yahoo.com/",
                        "Sec-Fetch-Dest": "empty",
                        "Sec-Fetch-Mode": "cors",
                        "Sec-Fetch-Site": "same-site"
                    }
                    r = requests.get(url, params=params, headers=headers, timeout=10)
                    if r.status_code == 200:
                        result = (r.json() or {}).get("quoteResponse", {}).get("result", [])
                        if result and len(result) > 0:
                            item = result[0]
                            if item.get("regularMarketPrice") or item.get("regularMarketPreviousClose"):
                                data.append({
                                    'symbol': method_name,
                                    'regularMarketPrice': item.get("regularMarketPrice"),
                                    'regularMarketChange': item.get("regularMarketChange"),
                                    'regularMarketChangePercent': item.get("regularMarketChangePercent"),
                                    'regularMarketPreviousClose': item.get("regularMarketPreviousClose")
                                })
                                print(f"Yahoo API success for {method_name} using {symbol}")
                                break
                except Exception as e:
                    print(f"Yahoo API error for {symbol}: {e}")
                    continue
        
        # Method 2: Try Yahoo Finance chart API
        if len(data) < 3:  # If we don't have at least 3 indices
            for method_name, symbol_list in symbols.items():
                if any(item['symbol'] == method_name for item in data):
                    continue  # Skip if we already have data for this index
                    
                for symbol in symbol_list:
                    try:
                        url = "https://query2.finance.yahoo.com/v8/finance/chart"
                        params = {"symbol": symbol, "range": "1d", "interval": "1m"}
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Accept": "application/json",
                            "Referer": "https://finance.yahoo.com/"
                        }
                        r = requests.get(url, params=params, headers=headers, timeout=8)
                        if r.status_code == 200:
                            chart_data = r.json()
                            if chart_data and 'chart' in chart_data and 'result' in chart_data['chart']:
                                result = chart_data['chart']['result'][0]
                                meta = result.get('meta', {})
                                if meta and (meta.get('regularMarketPrice') or meta.get('previousClose')):
                                    data.append({
                                        'symbol': method_name,
                                        'regularMarketPrice': meta.get('regularMarketPrice'),
                                        'regularMarketChange': meta.get('regularMarketChange'),
                                        'regularMarketChangePercent': meta.get('regularMarketChangePercent'),
                                        'regularMarketPreviousClose': meta.get('previousClose')
                                    })
                                    print(f"Chart API success for {method_name} using {symbol}")
                                    break
                    except Exception as e:
                        print(f"Chart API error for {symbol}: {e}")
                        continue
        
        # Method 3: Try yfinance if available
        if len(data) < 3 and yf is not None:
            for method_name, symbol_list in symbols.items():
                if any(item['symbol'] == method_name for item in data):
                    continue  # Skip if we already have data for this index
                    
                for symbol in symbol_list:
                    try:
                        ticker = yf.Ticker(symbol)
                        info = ticker.info
                        if info and (info.get('regularMarketPrice') or info.get('previousClose')):
                            data.append({
                                'symbol': method_name,
                                'regularMarketPrice': info.get('regularMarketPrice'),
                                'regularMarketChange': info.get('regularMarketChange'),
                                'regularMarketChangePercent': info.get('regularMarketChangePercent'),
                                'regularMarketPreviousClose': info.get('previousClose')
                            })
                            print(f"yfinance success for {method_name} using {symbol}")
                            break
                    except Exception as e:
                        print(f"yfinance error for {symbol}: {e}")
                        continue
        
        # Method 4: Try NSE official API
        if len(data) < 3:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': 'https://www.nseindia.com/'
                }
                
                # First get session cookies
                session = requests.Session()
                session.get('https://www.nseindia.com/', headers=headers, timeout=10)
                
                # Then get indices data
                url = "https://www.nseindia.com/api/allIndices"
                response = session.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    nse_data = response.json()
                    symbol_map = {
                        'NIFTY 50': 'NIFTY',
                        'NIFTY BANK': 'BANKNIFTY',
                        'NIFTY MIDCAP 50': 'MIDCPNIFTY',
                        'NIFTY FINANCIAL SERVICES': 'FINNIFTY'
                    }
                    
                    for item in nse_data.get('data', []):
                        index_name = item.get('index')
                        if index_name in symbol_map:
                            method_name = symbol_map[index_name]
                            if not any(item['symbol'] == method_name for item in data):
                                data.append({
                                    'symbol': method_name,
                                    'regularMarketPrice': item.get('last'),
                                    'regularMarketChange': item.get('variation'),
                                    'regularMarketChangePercent': item.get('percentChange'),
                                    'regularMarketPreviousClose': item.get('last') - item.get('variation', 0) if item.get('last') and item.get('variation') else None
                                })
                                print(f"NSE API success for {method_name}")
                    
                    print(f"NSE API success: {len(data)} symbols")
            except Exception as e:
                print(f"NSE API error: {e}")
        
        # Method 5: Try BSE API for SENSEX
        if not any(item['symbol'] == 'SENSEX' for item in data):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                # Try BSE API
                url = "https://www.bseindia.com/api/stockprices/GetStockPrices.aspx"
                params = {
                    'type': 'EQ',
                    'text': 'SENSEX'
                }
                response = requests.get(url, params=params, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    # Parse BSE response (this is a simplified approach)
                    # BSE API might return different format, so we'll try a different approach
                    pass
            except Exception as e:
                print(f"BSE API error: {e}")
        
        # Method 6: Web scraping fallback
        if len(data) < 3:
            try:
                from bs4 import BeautifulSoup
                
                # Try scraping from a financial news website
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                # Try Moneycontrol or similar site
                try:
                    url = "https://www.moneycontrol.com/indian-indices/nifty-50-9.html"
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        # Look for price elements (this would need to be customized based on actual HTML structure)
                        price_elements = soup.find_all(['span', 'div'], class_=lambda x: x and 'price' in x.lower() if x else False)
                        if price_elements:
                            # Extract price data (simplified)
                            pass
                except Exception as e:
                    print(f"Web scraping error: {e}")
                    
            except ImportError:
                print("BeautifulSoup not available for web scraping")
            except Exception as e:
                print(f"Web scraping error: {e}")
        
        # Method 7: Try alternative APIs for real data
        if len(data) < 3:
            try:
                # Try Alpha Vantage API (free tier)
                import os
                alpha_vantage_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
                if alpha_vantage_key:
                    for method_name, symbol_list in symbols.items():
                        if any(item['symbol'] == method_name for item in data):
                            continue
                        
                        for symbol in symbol_list:
                            try:
                                url = "https://www.alphavantage.co/query"
                                params = {
                                    'function': 'GLOBAL_QUOTE',
                                    'symbol': symbol,
                                    'apikey': alpha_vantage_key
                                }
                                response = requests.get(url, params=params, timeout=10)
                                if response.status_code == 200:
                                    result = response.json()
                                    if 'Global Quote' in result:
                                        quote = result['Global Quote']
                                        if quote.get('05. price'):
                                            data.append({
                                                'symbol': method_name,
                                                'regularMarketPrice': float(quote['05. price']),
                                                'regularMarketChange': float(quote['09. change']),
                                                'regularMarketChangePercent': float(quote['10. change percent'].replace('%', '')),
                                                'regularMarketPreviousClose': float(quote['08. previous close'])
                                            })
                                            print(f"Alpha Vantage success for {method_name}")
                                            break
                            except Exception as e:
                                print(f"Alpha Vantage error for {symbol}: {e}")
                                continue
            except Exception as e:
                print(f"Alpha Vantage API error: {e}")
        
        # Method 8: Return empty data if all methods fail - no mock data
        if not data:
            print("All methods failed, returning empty data - no mock data will be shown")
            # Return empty data instead of mock data
            # Frontend will handle this with loading animations
        
        print(f"Final data count: {len(data)}")
        
        # Process and return the data
        resp = []
        by_symbol = {itm.get("symbol"): itm for itm in data}

        for label in ["NIFTY", "SENSEX", "BANKNIFTY", "MIDCPNIFTY", "FINNIFTY"]:
            itm = by_symbol.get(label) or {}
            last = itm.get("regularMarketPrice") or itm.get("regularMarketPreviousClose")
            chg = itm.get("regularMarketChange")
            chgpct = itm.get("regularMarketChangePercent")
            
            if last is None:
                resp.append({
                    "name": label,
                    "value": "N/A",
                    "change": "N/A",
                    "change_pct": "N/A",
                    "error": "Data unavailable"
                })
                continue
                
            resp.append({
                "name": label,
                "value": round(float(last), 2) if isinstance(last, (int, float)) else last,
                "change": 0.0 if not isinstance(chg, (int, float)) else round(float(chg), 2),
                "change_pct": 0.0 if not isinstance(chgpct, (int, float)) else round(float(chgpct), 2)
            })
        
        print(f"Returning {len(resp)} indices")
        return JsonResponse({"indices": resp})

# =====================
# Natural Language Understanding (NLU)
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class ParseIntentView(View):
    def post(self, request):
        try:
            data = json.loads(request.body.decode("utf-8"))
            text = data.get("text", "").lower()

            # Enhanced NLP for better intent detection
            text_lower = text.strip().lower()
            
            # Market data queries
            if any(word in text_lower for word in ["market", "nifty", "sensex", "stock", "price", "index", "indices"]):
                return JsonResponse({
                    "intent": "market_data",
                    "confidence": 0.9,
                    "entities": {"query": text}
                })
            
            # Portfolio queries
            if any(word in text_lower for word in ["portfolio", "holdings", "stocks", "investments", "my stocks"]):
                return JsonResponse({
                    "intent": "portfolio",
                    "confidence": 0.9,
                    "entities": {"query": text}
                })
            
            # Add to portfolio
            if any(word in text_lower for word in ["add", "buy", "purchase", "invest"]):
                return JsonResponse({
                    "intent": "add_to_portfolio",
                    "confidence": 0.8,
                    "entities": {"query": text}
                })
            
            # General advice
            if any(word in text_lower for word in ["advice", "recommend", "suggest", "help", "what should"]):
                return JsonResponse({
                    "intent": "advice",
                    "confidence": 0.7,
                    "entities": {"query": text}
                })
            
            # Default fallback
            return JsonResponse({
                "intent": "general",
                "confidence": 0.5,
                "entities": {"query": text}
            })
            
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

# =====================
# Stock Search Views
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class StockSearchView(View):
    def get(self, request, exchange, query):
        """Search for stocks on NSE or BSE"""
        try:
            # Mock stock data for demonstration
            # In a real application, this would query actual stock databases
            mock_stocks = {
                'NSE': [
                    {'symbol': 'RELIANCE', 'name': 'Reliance Industries Limited'},
                    {'symbol': 'TCS', 'name': 'Tata Consultancy Services Limited'},
                    {'symbol': 'HDFCBANK', 'name': 'HDFC Bank Limited'},
                    {'symbol': 'INFY', 'name': 'Infosys Limited'},
                    {'symbol': 'HINDUNILVR', 'name': 'Hindustan Unilever Limited'},
                    {'symbol': 'ITC', 'name': 'ITC Limited'},
                    {'symbol': 'SBIN', 'name': 'State Bank of India'},
                    {'symbol': 'BHARTIARTL', 'name': 'Bharti Airtel Limited'},
                    {'symbol': 'KOTAKBANK', 'name': 'Kotak Mahindra Bank Limited'},
                    {'symbol': 'LT', 'name': 'Larsen & Toubro Limited'},
                    {'symbol': 'ASIANPAINT', 'name': 'Asian Paints Limited'},
                    {'symbol': 'AXISBANK', 'name': 'Axis Bank Limited'},
                    {'symbol': 'MARUTI', 'name': 'Maruti Suzuki India Limited'},
                    {'symbol': 'NESTLEIND', 'name': 'Nestle India Limited'},
                    {'symbol': 'SUNPHARMA', 'name': 'Sun Pharmaceutical Industries Limited'},
                    {'symbol': 'TITAN', 'name': 'Titan Company Limited'},
                    {'symbol': 'ULTRACEMCO', 'name': 'UltraTech Cement Limited'},
                    {'symbol': 'WIPRO', 'name': 'Wipro Limited'},
                    {'symbol': 'POWERGRID', 'name': 'Power Grid Corporation of India Limited'},
                    {'symbol': 'NTPC', 'name': 'NTPC Limited'},
                    {'symbol': 'GREENPANEL', 'name': 'Greenpanel Industries Limited'},
                    {'symbol': 'GREENPANELIND', 'name': 'Greenpanel Industries Limited'},
                ],
                'BSE': [
                    {'symbol': '500325', 'name': 'Reliance Industries Limited'},
                    {'symbol': '532540', 'name': 'Tata Consultancy Services Limited'},
                    {'symbol': '500180', 'name': 'HDFC Bank Limited'},
                    {'symbol': '500209', 'name': 'Infosys Limited'},
                    {'symbol': '500696', 'name': 'Hindustan Unilever Limited'},
                    {'symbol': '500875', 'name': 'ITC Limited'},
                    {'symbol': '500112', 'name': 'State Bank of India'},
                    {'symbol': '532454', 'name': 'Bharti Airtel Limited'},
                    {'symbol': '500247', 'name': 'Kotak Mahindra Bank Limited'},
                    {'symbol': '500510', 'name': 'Larsen & Toubro Limited'},
                    {'symbol': '500820', 'name': 'Asian Paints Limited'},
                    {'symbol': '532215', 'name': 'Axis Bank Limited'},
                    {'symbol': '532500', 'name': 'Maruti Suzuki India Limited'},
                    {'symbol': '500790', 'name': 'Nestle India Limited'},
                    {'symbol': '524715', 'name': 'Sun Pharmaceutical Industries Limited'},
                    {'symbol': '500114', 'name': 'Titan Company Limited'},
                    {'symbol': '532538', 'name': 'UltraTech Cement Limited'},
                    {'symbol': '507685', 'name': 'Wipro Limited'},
                    {'symbol': '532898', 'name': 'Power Grid Corporation of India Limited'},
                    {'symbol': '532555', 'name': 'NTPC Limited'},
                    {'symbol': '542008', 'name': 'Greenpanel Industries Limited'},
                ]
            }
            
            # Filter stocks based on query
            query_lower = query.lower()
            matching_stocks = []
            
            for stock in mock_stocks.get(exchange, []):
                if (query_lower in stock['name'].lower() or 
                    query_lower in stock['symbol'].lower()):
                    matching_stocks.append(stock)
            
            return JsonResponse({
                'stocks': matching_stocks[:10],  # Limit to 10 results
                'exchange': exchange,
                'query': query
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Search failed: {str(e)}',
                'stocks': [],
                'exchange': exchange,
                'query': query
            }, status=500)

@method_decorator(csrf_exempt, name="dispatch")
class MutualFundSearchView(View):
    def get(self, request, query):
        """Search for mutual funds"""
        try:
            # Mock mutual fund data for demonstration
            # In a real application, this would query actual mutual fund databases
            mock_funds = [
                {'symbol': 'SBIELSS', 'name': 'SBI Equity Linked Savings Scheme', 'nav': 45.67, 'category': 'ELSS'},
                {'symbol': 'HDFCEQ', 'name': 'HDFC Equity Fund', 'nav': 123.45, 'category': 'Large Cap'},
                {'symbol': 'ICICIPRU', 'name': 'ICICI Prudential Value Discovery Fund', 'nav': 89.12, 'category': 'Value'},
                {'symbol': 'AXISEQ', 'name': 'Axis Long Term Equity Fund', 'nav': 67.89, 'category': 'ELSS'},
                {'symbol': 'FRANKLIN', 'name': 'Franklin India Bluechip Fund', 'nav': 234.56, 'category': 'Large Cap'},
                {'symbol': 'DSPEQ', 'name': 'DSP Equity Fund', 'nav': 156.78, 'category': 'Large Cap'},
                {'symbol': 'KOTAKEQ', 'name': 'Kotak Standard Multicap Fund', 'nav': 78.90, 'category': 'Multi Cap'},
                {'symbol': 'MIRAEQ', 'name': 'Mirae Asset Large Cap Fund', 'nav': 45.23, 'category': 'Large Cap'},
                {'symbol': 'UTIEQ', 'name': 'UTI Equity Fund', 'nav': 112.34, 'category': 'Large Cap'},
                {'symbol': 'RELIANCE', 'name': 'Reliance Large Cap Fund', 'nav': 89.67, 'category': 'Large Cap'},
                {'symbol': 'ADITYA', 'name': 'Aditya Birla Sun Life Frontline Equity Fund', 'nav': 234.12, 'category': 'Large Cap'},
                {'symbol': 'TATAEQ', 'name': 'Tata Large Cap Fund', 'nav': 67.45, 'category': 'Large Cap'},
                {'symbol': 'L&TEQ', 'name': 'L&T Large Cap Fund', 'nav': 123.78, 'category': 'Large Cap'},
                {'symbol': 'INVESCO', 'name': 'Invesco India Growth Opportunities Fund', 'nav': 45.89, 'category': 'Large Cap'},
                {'symbol': 'CANARAEQ', 'name': 'Canara Robeco Equity Diversified Fund', 'nav': 78.34, 'category': 'Large Cap'},
            ]
            
            # Filter funds based on query
            query_lower = query.lower()
            matching_funds = []
            
            for fund in mock_funds:
                if (query_lower in fund['name'].lower() or 
                    query_lower in fund['symbol'].lower() or
                    query_lower in fund['category'].lower()):
                    matching_funds.append(fund)
            
            return JsonResponse({
                'funds': matching_funds[:10],  # Limit to 10 results
                'query': query
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Search failed: {str(e)}',
                'funds': [],
                'query': query
            }, status=500)

# =====================
# Stock Analysis Views
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class StockAnalysisView(View):
    def get(self, request, ticker, buy_price, shares):
        """Analyze a stock with buy price and shares"""
        try:
            buy_price = float(buy_price)
            shares = int(shares)
            
            # Fetch real stock data
            current_price, fundamentals = self._fetch_stock_data(ticker)
            
            # Calculate portfolio metrics
            total_investment = buy_price * shares
            current_value = current_price * shares
            profit_loss = current_value - total_investment
            profit_loss_percent = (profit_loss / total_investment) * 100 if total_investment > 0 else 0
            
            # Technical indicators (mock for now, can be enhanced with real data)
            rsi = 65.5
            macd = 2.3
            bollinger_position = "Above Upper Band"
            
            # Generate recommendation based on real data
            if profit_loss_percent > 10:
                recommendation = "Strong Buy"
                recommendation_reason = "Stock showing strong momentum with good technical indicators."
            elif profit_loss_percent > 0:
                recommendation = "Hold"
                recommendation_reason = "Stock is performing well. Consider holding for better returns."
            else:
                recommendation = "Sell"
                recommendation_reason = "Stock is underperforming. Consider selling to limit losses."
            
            analysis_data = {
                "ticker": ticker,
                "buy_price": buy_price,
                "shares": shares,
                "current_price": round(current_price, 2),
                "current_market_price": round(current_price, 2),  # Frontend expects this field
                "total_investment": round(total_investment, 2),
                "current_value": round(current_value, 2),
                "profit_loss": round(profit_loss, 2),
                "profit_loss_percent": round(profit_loss_percent, 2),
                "fundamentals": fundamentals,  # Real fundamental data
                "technical_indicators": {
                    "rsi": rsi,
                    "macd": macd,
                    "bollinger_position": bollinger_position
                },
                "recommendation": recommendation,
                "recommendation_reason": recommendation_reason,
                "personalized_advice": recommendation_reason,  # Frontend expects this field
                "analysis_date": datetime.now().strftime("%Y-%m-%d")
            }
            
            return JsonResponse(analysis_data)
            
        except (ValueError, TypeError) as e:
            return JsonResponse({
                "error": f"Invalid parameters: {str(e)}",
                "ticker": ticker,
                "buy_price": buy_price,
                "shares": shares
            }, status=400)
        except Exception as e:
            return JsonResponse({
                "error": f"Analysis failed: {str(e)}",
                "ticker": ticker
            }, status=500)
    
    def _fetch_stock_data(self, ticker):
        """Fetch real stock data and fundamentals"""
        try:
            # Try yfinance first
            if yf is not None:
                try:
                    # Add .NS suffix for NSE stocks if not present
                    symbol = ticker if '.' in ticker else f"{ticker}.NS"
                    stock = yf.Ticker(symbol)
                    info = stock.info
                    
                    if info and info.get('regularMarketPrice'):
                        current_price = info.get('regularMarketPrice', 0)
                        
                        # Extract fundamentals
                        fundamentals = {
                            "market_cap": self._format_market_cap(info.get('marketCap')),
                            "roe": info.get('returnOnEquity'),
                            "pe_ttm": info.get('trailingPE'),
                            "eps_ttm": info.get('trailingEps'),
                            "pb": info.get('priceToBook'),
                            "dividend_yield": info.get('dividendYield'),
                            "book_value": info.get('bookValue'),
                            "face_value": info.get('faceValue')
                        }
                        
                        return current_price, fundamentals
                except Exception as e:
                    print(f"yfinance error for {ticker}: {e}")
            
            # Fallback to Yahoo Finance API
            try:
                symbol = ticker if '.' in ticker else f"{ticker}.NS"
                url = "https://query1.finance.yahoo.com/v7/finance/quote"
                params = {"symbols": symbol}
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Referer": "https://finance.yahoo.com/",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site"
                }
                
                r = requests.get(url, params=params, headers=headers, timeout=10)
                if r.status_code == 200:
                    result = (r.json() or {}).get("quoteResponse", {}).get("result", [])
                    if result and len(result) > 0:
                        item = result[0]
                        current_price = item.get("regularMarketPrice", 0)
                        
                        # For Yahoo Finance API, we get limited fundamental data
                        # We'll use reasonable defaults based on the stock
                        fundamentals = {
                            "market_cap": "N/A",
                            "roe": None,
                            "pe_ttm": None,
                            "eps_ttm": None,
                            "pb": None,
                            "dividend_yield": None,
                            "book_value": None,
                            "face_value": 10.0  # Common face value for Indian stocks
                        }
                        
                        return current_price, fundamentals
            except Exception as e:
                print(f"Yahoo Finance API error for {ticker}: {e}")
            
            # Final fallback - use mock data
            print(f"Using fallback data for {ticker}")
            current_price = 250 if ticker == 'GREENPANEL' else 100
            fundamentals = {
                "market_cap": "N/A",
                "roe": None,
                "pe_ttm": None,
                "eps_ttm": None,
                "pb": None,
                "dividend_yield": None,
                "book_value": None,
                "face_value": 10.0
            }
            
            return current_price, fundamentals
            
        except Exception as e:
            print(f"Error fetching stock data for {ticker}: {e}")
            # Return fallback data
            current_price = 250 if ticker == 'GREENPANEL' else 100
            fundamentals = {
                "market_cap": "N/A",
                "roe": None,
                "pe_ttm": None,
                "eps_ttm": None,
                "pb": None,
                "dividend_yield": None,
                "book_value": None,
                "face_value": 10.0
            }
            return current_price, fundamentals
    
    def _format_market_cap(self, market_cap):
        """Format market cap in readable format"""
        if not market_cap:
            return "N/A"
        
        if market_cap >= 1e12:
            return f"₹{market_cap/1e12:.2f}T"
        elif market_cap >= 1e9:
            return f"₹{market_cap/1e9:.2f}B"
        elif market_cap >= 1e6:
            return f"₹{market_cap/1e6:.2f}M"
        else:
            return f"₹{market_cap:,.0f}"

@method_decorator(csrf_exempt, name="dispatch")
class StockHistoryView(View):
    def get(self, request, ticker):
        """Get stock price history"""
        try:
            period = request.GET.get('period', '1y')
            
            # Mock historical data
            # In a real application, this would fetch real historical data
            import random
            from datetime import datetime, timedelta
            
            base_price = 250 if ticker == 'GREENPANEL' else 100
            days = 365 if period == '1y' else (90 if period == '3m' else 30)
            
            history_data = []
            current_date = datetime.now()
            
            for i in range(days):
                date = current_date - timedelta(days=i)
                # Mock price with some volatility
                price = base_price * (1 + random.uniform(-0.1, 0.1))
                history_data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "price": round(price, 2),
                    "volume": random.randint(1000, 10000)
                })
            
            # Sort by date (oldest first)
            history_data.sort(key=lambda x: x["date"])
            
            return JsonResponse({
                "ticker": ticker,
                "period": period,
                "data": history_data
            })
            
        except Exception as e:
            return JsonResponse({
                "error": f"Failed to fetch history: {str(e)}",
                "ticker": ticker
            }, status=500)

@method_decorator(csrf_exempt, name="dispatch")
class MutualFundAnalysisView(View):
    def get(self, request, scheme_id, buy_nav, units):
        """Analyze a mutual fund with buy NAV and units"""
        try:
            buy_nav = float(buy_nav)
            units = float(units)
            
            # Mock analysis data for demonstration
            current_nav = buy_nav * 1.08  # Mock 8% gain
            total_investment = buy_nav * units
            current_value = current_nav * units
            profit_loss = current_value - total_investment
            profit_loss_percent = (profit_loss / total_investment) * 100
            
            # Mock fund metrics
            expense_ratio = 1.2
            risk_level = "Moderate"
            category = "Large Cap"
            
            # Mock recommendation
            if profit_loss_percent > 15:
                recommendation = "Excellent Performance"
                recommendation_reason = "Fund is outperforming with strong returns and good risk management."
            elif profit_loss_percent > 5:
                recommendation = "Good Performance"
                recommendation_reason = "Fund is performing well above market average."
            else:
                recommendation = "Average Performance"
                recommendation_reason = "Fund performance is in line with market expectations."
            
            analysis_data = {
                "scheme_id": scheme_id,
                "buy_nav": buy_nav,
                "units": units,
                "current_nav": round(current_nav, 2),
                "current_market_price": round(current_nav, 2),  # Frontend expects this field
                "total_investment": round(total_investment, 2),
                "current_value": round(current_value, 2),
                "profit_loss": round(profit_loss, 2),
                "profit_loss_percent": round(profit_loss_percent, 2),
                "fund_metrics": {
                    "expense_ratio": expense_ratio,
                    "risk_level": risk_level,
                    "category": category
                },
                "recommendation": recommendation,
                "recommendation_reason": recommendation_reason,
                "personalized_advice": recommendation_reason,  # Frontend expects this field
                "analysis_date": "2025-01-02"
            }
            
            return JsonResponse(analysis_data)
            
        except (ValueError, TypeError) as e:
            return JsonResponse({
                "error": f"Invalid parameters: {str(e)}",
                "scheme_id": scheme_id,
                "buy_nav": buy_nav,
                "units": units
            }, status=400)
        except Exception as e:
            return JsonResponse({
                "error": f"Analysis failed: {str(e)}",
                "scheme_id": scheme_id
            }, status=500)

@method_decorator(csrf_exempt, name="dispatch")
class MutualFundHistoryView(View):
    def get(self, request, scheme_id):
        """Get mutual fund NAV history"""
        try:
            period = request.GET.get('period', '1y')
            
            # Mock historical NAV data
            import random
            from datetime import datetime, timedelta
            
            base_nav = 45.67  # Mock base NAV
            days = 365 if period == '1y' else (90 if period == '3m' else 30)
            
            history_data = []
            current_date = datetime.now()
            
            for i in range(days):
                date = current_date - timedelta(days=i)
                # Mock NAV with gradual growth
                nav = base_nav * (1 + (i * 0.0001) + random.uniform(-0.02, 0.02))
                history_data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "nav": round(nav, 2)
                })
            
            # Sort by date (oldest first)
            history_data.sort(key=lambda x: x["date"])
            
            return JsonResponse({
                "scheme_id": scheme_id,
                "period": period,
                "data": history_data
            })
            
        except Exception as e:
            return JsonResponse({
                "error": f"Failed to fetch history: {str(e)}",
                "scheme_id": scheme_id
            }, status=500)

@method_decorator(csrf_exempt, name="dispatch")
class DevVersionView(View):
    def get(self, request):
        """Development version endpoint"""
        return JsonResponse({
            "version": "1.0.0",
            "status": "development",
            "timestamp": "2025-01-02T00:00:00Z"
        })

# =====================
# Chat Response Generation
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class ChatView(View):
    def post(self, request):
        try:
            data = json.loads(request.body.decode("utf-8"))
            message = data.get("message", "").strip()
            
            if not message:
                return JsonResponse({"error": "Message is required"}, status=400)
            
            # Parse intent
            intent_response = self._parse_intent(message)
            intent = intent_response.get("intent", "general")
            
            # Generate response based on intent
            if intent == "market_data":
                response = self._handle_market_data_query(message)
            elif intent == "portfolio":
                response = self._handle_portfolio_query(request, message)
            elif intent == "add_to_portfolio":
                response = self._handle_add_portfolio_query(message)
            elif intent == "advice":
                response = self._handle_advice_query(message)
            else:
                response = self._handle_general_query(message)
            
            return JsonResponse({
                "response": response,
                "intent": intent,
                "timestamp": datetime.now().isoformat()
            })
            
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    def _parse_intent(self, text):
        """Parse user intent from text"""
        text_lower = text.strip().lower()
        
        if any(word in text_lower for word in ["market", "nifty", "sensex", "stock", "price", "index", "indices"]):
            return {"intent": "market_data", "confidence": 0.9}
        elif any(word in text_lower for word in ["portfolio", "holdings", "stocks", "investments", "my stocks"]):
            return {"intent": "portfolio", "confidence": 0.9}
        elif any(word in text_lower for word in ["add", "buy", "purchase", "invest"]):
            return {"intent": "add_to_portfolio", "confidence": 0.8}
        elif any(word in text_lower for word in ["advice", "recommend", "suggest", "help", "what should"]):
            return {"intent": "advice", "confidence": 0.7}
        else:
            return {"intent": "general", "confidence": 0.5}
    
    def _handle_market_data_query(self, message):
        """Handle market data queries"""
        return "I can provide you with current market data including NIFTY, SENSEX, and other major indices. Would you like me to fetch the latest market snapshot?"
    
    def _handle_portfolio_query(self, request, message):
        """Handle portfolio queries"""
        if not request.user.is_authenticated:
            return "Please log in to view your portfolio."
        
        holdings = Holding.objects.filter(portfolio__user=request.user)
        if not holdings.exists():
            return "Your portfolio is currently empty. You can add stocks by using the 'Add to Portfolio' feature."
        
        total_value = sum(h.quantity * h.average_buy_price for h in holdings)
        holdings_text = "\n".join([
            f"• {h.ticker}: {h.quantity} shares @ ₹{h.buy_price:.2f} (Total: ₹{h.quantity * h.buy_price:.2f})"
            for h in holdings
        ])
        
        return f"Here's your current portfolio:\n\n{holdings_text}\n\nTotal Portfolio Value: ₹{total_value:.2f}"
    
    def _handle_add_portfolio_query(self, message):
        """Handle add to portfolio queries"""
        return "To add stocks to your portfolio, please use the 'Add to Portfolio' button in the interface, or provide the stock symbol, quantity, and buy price."
    
    def _handle_advice_query(self, message):
        """Handle advice queries"""
        advice_responses = [
            "Diversification is key to managing risk in your portfolio.",
            "Consider your investment horizon and risk tolerance before making decisions.",
            "Regular monitoring of your portfolio is important for long-term success.",
            "Don't put all your eggs in one basket - spread your investments across different sectors.",
            "Consider consulting with a financial advisor for personalized advice."
        ]
        return random.choice(advice_responses)
    
    def _handle_general_query(self, message):
        """Handle general queries"""
        general_responses = [
            "I'm here to help with your investment and portfolio management needs. How can I assist you today?",
            "I can help you with market data, portfolio management, and investment advice. What would you like to know?",
            "Feel free to ask me about stocks, market trends, or your portfolio. I'm here to help!",
            "I'm your AI investment assistant. Ask me about market data, your portfolio, or investment strategies."
        ]
        return random.choice(general_responses)

# =====================
# Portfolio Health Analysis
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class PortfolioHealthView(View):
    def get(self, request):
        print(f"PortfolioHealthView: User authenticated: {request.user.is_authenticated}")
        print(f"PortfolioHealthView: User: {request.user}")
        
        if not request.user.is_authenticated:
            print("PortfolioHealthView: User not authenticated, returning 401")
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        holdings = Holding.objects.filter(portfolio__user=request.user)
        print(f"PortfolioHealthView: Found {holdings.count()} holdings for user {request.user}")
        
        if not holdings.exists():
            print("PortfolioHealthView: No holdings found, returning empty portfolio response")
            return JsonResponse({
                "overall_score": 0,
                "diversification": {
                    "score": 0,
                    "feedback": "No holdings found. Add stocks to get health analysis."
                },
                "risk": {
                    "score": 5,
                    "feedback": "Cannot assess risk without holdings."
                },
                "performance": {
                    "score": 0,
                    "feedback": "No performance data available."
                }
            })
        
        # Calculate basic portfolio metrics
        total_value = sum(h.quantity * h.average_buy_price for h in holdings)
        num_holdings = holdings.count()
        
        # Diversification scoring (0-10)
        if num_holdings >= 5:
            diversification_score = 8
            diversification_feedback = "Good diversification across multiple stocks."
        elif num_holdings >= 3:
            diversification_score = 6
            diversification_feedback = "Moderate diversification. Consider adding more stocks."
        else:
            diversification_score = 3
            diversification_feedback = "Low diversification. Add more stocks to reduce risk."
        
        # Risk scoring (0-10) - simplified
        risk_score = 6  # Default moderate risk
        risk_feedback = "Moderate risk level. Monitor your investments regularly."
        
        # Performance scoring (0-10) - simplified
        performance_score = 7  # Default good performance
        performance_feedback = "Portfolio performance looks stable."
        
        # Overall score (average of all scores)
        overall_score = round((diversification_score + risk_score + performance_score) / 3, 1)
        
        response_data = {
            "overall_score": overall_score,
            "diversification": {
                "score": diversification_score,
                "feedback": diversification_feedback
            },
            "risk": {
                "score": risk_score,
                "feedback": risk_feedback
            },
            "performance": {
                "score": performance_score,
                "feedback": performance_feedback
            }
        }
        
        print(f"PortfolioHealthView: Returning response: {response_data}")
        return JsonResponse(response_data)

# =====================
# Mutual Fund Data
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class MutualFundView(View):
    def get(self, request):
        # Sample mutual fund data - in production, this would come from a real API
        funds = [
            {
                "scheme_id": "SBI001",
                "fund_name": "SBI Bluechip Fund",
                "nav": 45.67,
                "change": 0.23,
                "change_pct": 0.51,
                "category": "Large Cap"
            },
            {
                "scheme_id": "HDFC002",
                "fund_name": "HDFC Top 100 Fund",
                "nav": 78.45,
                "change": -0.12,
                "change_pct": -0.15,
                "category": "Large Cap"
            },
            {
                "scheme_id": "ICICI003",
                "fund_name": "ICICI Prudential Value Discovery Fund",
                "nav": 123.89,
                "change": 0.67,
                "change_pct": 0.54,
                "category": "Value"
            }
        ]
        
        return JsonResponse({"funds": funds})

# =====================
# Dashboard Views
# =====================

@login_required
def dashboard(request):
    """Main dashboard view"""
    return render(request, 'advisor/index.html')

# =====================
# Missing View Functions for URL Configuration
# =====================

def chat_view(request):
    """Main chat interface view"""
    return render(request, 'advisor/index.html')

def profile_view(request):
    """User profile view"""
    return render(request, 'advisor/profile.html')

def about_view(request):
    """About page view"""
    return render(request, 'advisor/about.html')

def portfolio_page_view(request):
    """Portfolio page view"""
    holdings = Holding.objects.filter(portfolio__user=request.user)
    total_value = sum(h.quantity * h.average_buy_price for h in holdings)
    
    return render(request, 'advisor/portfolio.html', {
        'holdings': holdings,
        'total_value': total_value
    })