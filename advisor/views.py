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
        
        holdings = Holding.objects.filter(user=request.user)
        total_value = sum(h.quantity * h.buy_price for h in holdings)
        
        return JsonResponse({
            "holdings": [
                {
                    "ticker": h.ticker,
                    "quantity": h.quantity,
                    "buy_price": h.buy_price,
                    "current_value": h.quantity * h.buy_price
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
            buy_price = float(data.get("buy_price", 0))
            
            if not ticker or quantity <= 0 or buy_price <= 0:
                return JsonResponse({"error": "Invalid data"}, status=400)
            
            # Check if holding already exists
            holding, created = Holding.objects.get_or_create(
                user=request.user,
                ticker=ticker,
                defaults={"quantity": quantity, "buy_price": buy_price}
            )
            
            if not created:
                # Update existing holding
                total_quantity = holding.quantity + quantity
                total_cost = (holding.quantity * holding.buy_price) + (quantity * buy_price)
                holding.buy_price = total_cost / total_quantity
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
        
        # Method 7: Use cached/static data as absolute last resort
        if not data:
            print("All methods failed, using static fallback data")
            # Use some reasonable static values based on recent market data
            static_data = {
                "NIFTY": {"price": 19500.0, "change": 150.0, "change_pct": 0.78},
                "SENSEX": {"price": 65000.0, "change": 500.0, "change_pct": 0.78},
                "BANKNIFTY": {"price": 45000.0, "change": 300.0, "change_pct": 0.67},
                "MIDCPNIFTY": {"price": 12000.0, "change": 80.0, "change_pct": 0.67},
                "FINNIFTY": {"price": 20000.0, "change": 120.0, "change_pct": 0.60}
            }
            
            for method_name, values in static_data.items():
                data.append({
                    'symbol': method_name,
                    'regularMarketPrice': values['price'],
                    'regularMarketChange': values['change'],
                    'regularMarketChangePercent': values['change_pct'],
                    'regularMarketPreviousClose': values['price'] - values['change']
                })
        
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
        
        holdings = Holding.objects.filter(user=request.user)
        if not holdings.exists():
            return "Your portfolio is currently empty. You can add stocks by using the 'Add to Portfolio' feature."
        
        total_value = sum(h.quantity * h.buy_price for h in holdings)
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

@login_required
def portfolio_page(request):
    """Portfolio management page"""
    holdings = Holding.objects.filter(user=request.user)
    total_value = sum(h.quantity * h.buy_price for h in holdings)
    
    return render(request, 'advisor/portfolio.html', {
        'holdings': holdings,
        'total_value': total_value
    })

def about_page(request):
    """About page"""
    return render(request, 'advisor/about.html')
