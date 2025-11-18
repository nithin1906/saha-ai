import requests
from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg
from .models import Holding, Portfolio
from .data_service import stock_data_service
from .mf_data_service import mf_data_service
import json
import random
import math
import re
import logging
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)

# =====================
# Portfolio Management
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class PortfolioView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        from decimal import Decimal
        
        holdings = Holding.objects.filter(portfolio__user=request.user)
        total_value = sum(Decimal(h.quantity) * h.average_buy_price for h in holdings)
        
        # Check if this is a details request (for portfolio page)
        if request.path.endswith('/details/'):
            holdings_data = []
            total_current_value = 0
            
            for h in holdings:
                # Fetch real-time current price
                current_price = self._fetch_current_price(h.ticker)
                current_value = Decimal(h.quantity) * Decimal(str(current_price))
                net_profit = current_value - (Decimal(h.quantity) * h.average_buy_price)
                total_current_value += float(current_value)
                
                holdings_data.append({
                    "ticker": h.ticker,
                    "quantity": h.quantity,
                    "average_buy_price": float(h.average_buy_price),
                    "current_price": current_price,
                    "current_value": float(current_value),
                    "net_profit": float(net_profit)
                })
            
            return JsonResponse({
                "holdings": holdings_data,
                "total_invested": float(total_value),
                "total_current_value": total_current_value,
                "net_profit": total_current_value - float(total_value)
            })
        
        # Default response for other portfolio requests
        return JsonResponse({
            "holdings": [
                {
                    "ticker": h.ticker,
                    "quantity": h.quantity,
                    "buy_price": float(h.average_buy_price),
                    "current_value": float(Decimal(h.quantity) * h.average_buy_price)
                }
                for h in holdings
            ],
            "total_value": float(total_value)
        })
    
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        try:
            from decimal import Decimal
            
            data = json.loads(request.body.decode("utf-8"))
            ticker = data.get("ticker", "").upper()
            quantity = int(data.get("quantity", 0))
            average_buy_price = Decimal(str(data.get("buy_price", 0)))
            
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
                # Update existing holding - use Decimal arithmetic
                total_quantity = holding.quantity + quantity
                total_cost = (Decimal(holding.quantity) * holding.average_buy_price) + (Decimal(quantity) * average_buy_price)
                holding.average_buy_price = total_cost / Decimal(total_quantity)
                holding.quantity = total_quantity
                holding.save()
            
            return JsonResponse({"message": "Holding added successfully"})
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            return JsonResponse({"error": "Invalid payload"}, status=400)
        except Exception as e:
            print(f"Portfolio POST error: {e}")
            return JsonResponse({"error": f"Failed to add holding: {str(e)}"}, status=500)
    
    def _fetch_current_price(self, ticker):
        """Fetch current price/NAV for stocks and mutual funds"""
        # Check if it's a mutual fund (scheme IDs typically start with letters)
        if ticker.isalpha() or (len(ticker) > 3 and ticker[:3].isalpha()):
            # Try to get mutual fund NAV
            try:
                from advisor.mf_data_service import mf_data_service
                fund = mf_data_service.get_fund_by_id(ticker)
                if fund:
                    return fund['nav']
                else:
                    # If not found in MF database, try as stock
                    return stock_data_service.get_stock_price(ticker)
            except Exception as e:
                print(f"Error fetching MF NAV for {ticker}: {e}")
                # Fallback to stock price
                return stock_data_service.get_stock_price(ticker)
        else:
            # Regular stock ticker
            return stock_data_service.get_stock_price(ticker)
    
    def delete(self, request):
        """Remove a holding from portfolio"""
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        try:
            data = json.loads(request.body.decode("utf-8"))
            ticker = data.get("ticker", "").upper()
            
            if not ticker:
                return JsonResponse({"error": "Ticker is required"}, status=400)
            
            # Get user's portfolio
            try:
                portfolio = Portfolio.objects.get(user=request.user)
            except Portfolio.DoesNotExist:
                return JsonResponse({"error": "Portfolio not found"}, status=404)
            
            # Find and delete the holding
            try:
                holding = Holding.objects.get(portfolio=portfolio, ticker=ticker)
                holding.delete()
                return JsonResponse({"message": f"Holding {ticker} removed successfully"})
            except Holding.DoesNotExist:
                return JsonResponse({"error": f"Holding {ticker} not found"}, status=404)
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            return JsonResponse({"error": "Invalid payload"}, status=400)
        except Exception as e:
            print(f"Portfolio DELETE error: {e}")
            return JsonResponse({"error": f"Failed to remove holding: {str(e)}"}, status=500)

# =====================
# Market snapshot
# =====================

class MarketSnapshotView(View):
    def get(self, request):
        """Get market indices using the robust data service"""
        print("=== MarketSnapshotView: Starting market data fetch ===")
        
        try:
            # Get market indices from the robust data service
            market_data = stock_data_service.get_market_indices()
            
            # Handle both old and new response formats
            if isinstance(market_data, dict) and 'indices' in market_data:
                indices_data = market_data['indices']
                market_status = market_data.get('market_status', {})
            else:
                # Fallback for old format
                indices_data = market_data
                market_status = {}
            
            # Convert to the expected format
            resp = []
            for index_name, data in indices_data.items():
                resp.append({
                    "name": index_name,
                    "price": data['price'],
                    "change": data['change'],
                    "change_percent": data['change_percent']
                })
            
            print(f"MarketSnapshotView: Successfully fetched {len(resp)} indices")
            return JsonResponse({
                "indices": resp,
                "market_status": market_status
            })
            
        except Exception as e:
            print(f"MarketSnapshotView: Error in get method: {e}")
            return JsonResponse({
                "indices": [],
                "market_status": {
                    "status": "error",
                    "message": "Unable to fetch market data"
                }
            })

# =====================
# Portfolio Health Analysis
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class PortfolioHealthView(View):
    def get(self, request):
        print(f"PortfolioHealthView: User authenticated: {request.user.is_authenticated}")
        print(f"PortfolioHealthView: User: {request.user}")
        
        try:
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
                        "score": 0,
                        "feedback": "No holdings found. Add stocks to get risk analysis."
                    },
                    "performance": {
                        "score": 0,
                        "feedback": "No holdings found. Add stocks to get performance analysis."
                    }
                })
            
            # Calculate portfolio metrics
            total_invested = Decimal('0')
            total_current_value = Decimal('0')
            
            for holding in holdings:
                current_price = self._fetch_current_price(holding.ticker)
                current_value = Decimal(str(current_price)) * holding.quantity
                invested_value = holding.average_buy_price * holding.quantity
                
                total_invested += invested_value
                total_current_value += current_value
            
            # Calculate performance
            total_profit_loss = total_current_value - total_invested
            performance_percentage = (total_profit_loss / total_invested * 100) if total_invested > 0 else 0
            
            # Calculate diversification score (0-10)
            # More holdings = better diversification
            num_holdings = holdings.count()
            if num_holdings >= 10:
                diversification_score = 10
            elif num_holdings >= 7:
                diversification_score = 8
            elif num_holdings >= 5:
                diversification_score = 7
            elif num_holdings >= 3:
                diversification_score = 5
            elif num_holdings == 2:
                diversification_score = 3
            else:
                diversification_score = 1
            
            # Calculate risk score (0-10)
            # More holdings = lower risk (higher score)
            # Fewer holdings = higher risk (lower score)
            if num_holdings >= 10:
                risk_score = 10
            elif num_holdings >= 7:
                risk_score = 8
            elif num_holdings >= 5:
                risk_score = 7
            elif num_holdings >= 3:
                risk_score = 5
            elif num_holdings == 2:
                risk_score = 3
            else:
                risk_score = 1
            
            # Calculate performance score (0-10)
            if performance_percentage >= 30:
                performance_score = 10
            elif performance_percentage >= 20:
                performance_score = 9
            elif performance_percentage >= 15:
                performance_score = 8
            elif performance_percentage >= 10:
                performance_score = 7
            elif performance_percentage >= 5:
                performance_score = 6
            elif performance_percentage >= 0:
                performance_score = 5
            elif performance_percentage >= -5:
                performance_score = 4
            elif performance_percentage >= -10:
                performance_score = 3
            elif performance_percentage >= -20:
                performance_score = 2
            else:
                performance_score = 1
            
            # Overall score (weighted average: diversification 30%, risk 30%, performance 40%)
            overall_score = (diversification_score * 0.3) + (risk_score * 0.3) + (performance_score * 0.4)
            
            print(f"PortfolioHealthView: Calculated overall score: {overall_score}")
            
            return JsonResponse({
                "overall_score": round(overall_score, 1),
                "diversification": {
                    "score": diversification_score,
                    "feedback": f"Good diversification with {holdings.count()} holdings." if diversification_score >= 6 else f"Consider adding more stocks for better diversification. Currently have {holdings.count()} holdings."
                },
                "risk": {
                    "score": risk_score,
                    "feedback": f"Portfolio risk is {'low' if risk_score >= 7 else 'moderate' if risk_score >= 4 else 'high'} with {holdings.count()} holdings."
                },
                "performance": {
                    "score": performance_score,
                    "feedback": f"Portfolio performance is {'excellent' if performance_score >= 8 else 'good' if performance_score >= 6 else 'moderate' if performance_score >= 4 else 'poor'} with {performance_percentage:.1f}% returns."
                }
            })
            
        except Exception as e:
            print(f"PortfolioHealthView: Error in get method: {e}")
            return JsonResponse({
                "overall_score": 0,
                "diversification": {
                    "score": 0,
                    "feedback": "Unable to calculate diversification due to data error."
                },
                "risk": {
                    "score": 0,
                    "feedback": "Unable to calculate risk due to data error."
                },
                "performance": {
                    "score": 0,
                    "feedback": "Unable to calculate performance due to data error."
                }
            }, status=500)
    
    def _fetch_current_price(self, ticker):
        """Fetch current price/NAV for stocks and mutual funds"""
        # Check if it's a mutual fund (scheme IDs typically start with letters)
        if ticker.isalpha() or (len(ticker) > 3 and ticker[:3].isalpha()):
            # Try to get mutual fund NAV
            try:
                from advisor.mf_data_service import mf_data_service
                fund = mf_data_service.get_fund_by_id(ticker)
                if fund:
                    return fund['nav']
                else:
                    # If not found in MF database, try as stock
                    return stock_data_service.get_stock_price(ticker)
            except Exception as e:
                print(f"Error fetching MF NAV for {ticker}: {e}")
                # Fallback to stock price
                return stock_data_service.get_stock_price(ticker)
        else:
            # Regular stock ticker
            return stock_data_service.get_stock_price(ticker)

# =====================
# Mutual Fund Data
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class MutualFundView(View):
    def get(self, request):
        """Get mutual fund data with filtering options"""
        try:
            category = request.GET.get('category', '')
            limit = int(request.GET.get('limit', 20))
            
            if category:
                funds = mf_data_service.get_funds_by_category(category)
            else:
                # Get top performing funds by default
                funds = mf_data_service.get_top_performing_funds(limit=limit)
            
            return JsonResponse({
                "funds": funds[:limit],
                "total_count": len(funds),
                "category": category or "All"
            })
            
        except Exception as e:
            logger.error(f"MutualFundView error: {e}")
            return JsonResponse({
                "error": f"Failed to fetch mutual fund data: {str(e)}",
                "funds": []
            }, status=500)

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
    return render(request, 'advisor/index.html', {
        'user_first_name': request.user.first_name if request.user.is_authenticated else '',
        'csrf_token_value': request.META.get('CSRF_COOKIE', '')
    })

def profile_view(request):
    """User profile view"""
    return render(request, 'advisor/profile.html')

def about_view(request):
    """About page view"""
    return render(request, 'advisor/about.html')

def portfolio_page_view(request):
    """Portfolio page view"""
    return render(request, 'advisor/portfolio.html')

# =====================
# Natural Language Understanding (NLU)
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class ParseIntentView(View):
    def post(self, request):
        try:
            data = json.loads(request.body.decode("utf-8"))
            text = data.get("text", "").lower()
            original_text = data.get("text", "")  # Keep original for entity extraction

            # Enhanced NLP for better intent detection
            text_lower = text.strip().lower()
            
            # HIGHEST PRIORITY: Stock analysis queries (analyze X, should I buy X, etc)
            # Mutual fund queries (detect BEFORE checking for just "fund" as part of portfolio queries)
            if any(word in text_lower for word in ["mutual fund", "mutualfund", "mf ", "nav", "scheme", "sip"]):
                return JsonResponse({
                    "intent": "analyze_mutual_fund",
                    "confidence": 0.9,
                    "entities": {"query": original_text, "entity": original_text}
                })
            
            # Stock analysis queries (e.g., "analyze tata steel", "buy reliance", "should I sell infy")
            if any(word in text_lower for word in ["analyze", "analysis", "should i buy", "should i sell", "buy", "sell", "recommendation"]):
                return JsonResponse({
                    "intent": "stock_analysis",
                    "confidence": 0.85,
                    "entities": {"query": original_text, "entity": original_text}
                })
            
            # Portfolio queries
            if any(word in text_lower for word in ["portfolio", "holdings", "stocks i own", "my stocks", "investments", "my investments"]):
                return JsonResponse({
                    "intent": "portfolio",
                    "confidence": 0.9,
                    "entities": {"query": text}
                })
            
            # Market data queries (generic market info, index prices, etc)
            # Be more specific - don't match just "stock" alone as it's too generic
            if any(word in text_lower for word in ["market snapshot", "market data", "nifty", "sensex", "banknifty", "index", "indices", "market price", "market close"]):
                return JsonResponse({
                    "intent": "market_data",
                    "confidence": 0.9,
                    "entities": {"query": text}
                })
            
            # Search queries
            if any(word in text_lower for word in ["search", "find", "look for", "show me"]):
                return JsonResponse({
                    "intent": "search",
                    "confidence": 0.8,
                    "entities": {"query": text}
                })
            
            # Default to general chat
            return JsonResponse({
                "intent": "general_chat",
                "confidence": 0.5,
                "entities": {"query": text}
            })
            
        except Exception as e:
            return JsonResponse({
                "intent": "error",
                "confidence": 0.0,
                "entities": {"error": str(e)}
            }, status=500)

# =====================
# Stock Search
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class StockSearchView(View):
    def get(self, request, exchange, query):
        """Search for stocks using real-time data"""
        try:
            # Use real-time search from Yahoo Finance
            stocks = self._search_real_stocks(query, exchange.upper())
            
            return JsonResponse({
                "stocks": stocks,  # Return all matching stocks
                "exchange": exchange.upper(),
                "query": query
            })
            
        except Exception as e:
            return JsonResponse({
                "error": f"Search failed: {str(e)}",
                "stocks": [],
                "exchange": exchange.upper(),
                "query": query
            }, status=500)
    
    def _search_real_stocks(self, query, exchange):
        """Search for real stocks using Yahoo Finance"""
        try:
            import requests
            import json
            
            # Yahoo Finance search endpoint
            url = "https://query1.finance.yahoo.com/v1/finance/search"
            params = {
                "q": query,
                "quotesCount": 50,  # Increased to get more results
                "newsCount": 0
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Referer": "https://finance.yahoo.com/"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                quotes = data.get("quotes", [])
                
                stocks = []
                query_lower = query.lower()
                
                for quote in quotes:
                    symbol = quote.get("symbol", "")
                    name = quote.get("longname") or quote.get("shortname", "")
                    price = quote.get("regularMarketPrice")
                    change = quote.get("regularMarketChange")
                    change_pct = quote.get("regularMarketChangePercent")
                    
                    # Normalize for matching
                    symbol_upper = symbol.upper()
                    name_lower = (name or "").lower()
                    
                    # Check if it's an Indian stock (NSE or BSE)
                    is_nse = ".NS" in symbol_upper
                    is_bse = ".BO" in symbol_upper
                    
                    # Also check if name contains query (case-insensitive)
                    name_matches = query_lower in name_lower if name else False
                    symbol_matches = query_lower in symbol_upper.lower()
                    
                    # Filter by exchange - be more flexible and inclusive
                    if exchange == "NSE":
                        # Include if: has .NS suffix, OR (name/symbol matches AND not a BSE stock)
                        if is_nse or (name_matches and not is_bse) or (symbol_matches and not is_bse):
                            # Remove .NS suffix for NSE stocks
                            clean_symbol = symbol.replace(".NS", "").replace(".ns", "")
                            stocks.append({
                                "symbol": clean_symbol,
                                "name": name,
                                "price": price or 0.0,
                                "change": change or 0.0,
                                "change_pct": change_pct or 0.0
                            })
                    elif exchange == "BSE":
                        # Include if: has .BO suffix, OR (name/symbol matches AND not an NSE stock)
                        if is_bse or (name_matches and not is_nse) or (symbol_matches and not is_nse):
                            # Keep .BO suffix for BSE stocks
                            clean_symbol = symbol.replace(".BO", "").replace(".bo", "")
                            if not clean_symbol.endswith(".BO"):
                                clean_symbol = clean_symbol + ".BO"
                            stocks.append({
                                "symbol": clean_symbol,
                                "name": name,
                                "price": price or 0.0,
                                "change": change or 0.0,
                                "change_pct": change_pct or 0.0
                            })
                
                # Sort by relevance (exact symbol match first, then name match)
                def sort_key(s):
                    symbol_match = query_lower in s["symbol"].lower()
                    name_match = query_lower in s["name"].lower() if s["name"] else False
                    if symbol_match:
                        return 0
                    elif name_match:
                        return 1
                    return 2
                
                stocks.sort(key=sort_key)
                return stocks
                
        except Exception as e:
            logger.error(f"Real stock search error: {e}")
            print(f"Real stock search error: {e}")
            
        return []

# =====================
# Mutual Fund Search
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class MutualFundSearchView(View):
    def get(self, request, query):
        """Search for mutual funds using comprehensive database"""
        try:
            # Use the new MF data service for search
            funds = mf_data_service.search_mutual_funds(query)
            
            return JsonResponse({
                "funds": funds[:10],  # Limit to 10 results
                "query": query,
                "total_results": len(funds)
            })
            
        except Exception as e:
            logger.error(f"MutualFundSearchView error: {e}")
            return JsonResponse({
                "error": f"Search failed: {str(e)}",
                "funds": [],
                "query": query
            }, status=500)

# =====================
# Mutual Fund Categories
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class MutualFundCategoriesView(View):
    def get(self, request):
        """Get all available mutual fund categories"""
        try:
            categories = mf_data_service.get_fund_categories()
            
            return JsonResponse({
                "categories": categories,
                "total_categories": len(categories)
            })
            
        except Exception as e:
            logger.error(f"MutualFundCategoriesView error: {e}")
            return JsonResponse({
                "error": f"Failed to fetch categories: {str(e)}",
                "categories": []
            }, status=500)

# =====================
# Mutual Fund Details
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class MutualFundDetailsView(View):
    def get(self, request, scheme_id):
        """Get detailed information about a specific mutual fund"""
        try:
            fund = mf_data_service.get_fund_by_id(scheme_id)
            
            if not fund:
                return JsonResponse({
                    "error": f"Fund with scheme ID '{scheme_id}' not found"
                }, status=404)
            
            # Get NAV history for the fund
            nav_history = mf_data_service.get_fund_nav_history(scheme_id, days=30)
            
            return JsonResponse({
                "fund": fund,
                "nav_history": nav_history,
                "last_updated": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"MutualFundDetailsView error: {e}")
            return JsonResponse({
                "error": f"Failed to fetch fund details: {str(e)}"
            }, status=500)

# =====================
# Stock Analysis
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
            
            # Calculate metrics
            total_investment = buy_price * shares
            current_value = current_price * shares
            profit_loss = current_value - total_investment
            profit_loss_percent = (profit_loss / total_investment * 100) if total_investment > 0 else 0
            
            # Generate analysis
            analysis = self._generate_analysis(ticker, current_price, buy_price, fundamentals)
            
            return JsonResponse({
                "ticker": ticker,
                "current_market_price": current_price,
                "buy_price": buy_price,
                "shares": shares,
                "total_investment": total_investment,
                "current_value": current_value,
                "profit_loss": profit_loss,
                "profit_loss_percent": profit_loss_percent,
                "fundamentals": fundamentals,
                "personalized_advice": analysis
            })
            
        except Exception as e:
            return JsonResponse({
                "error": f"Analysis failed: {str(e)}",
                "ticker": ticker
            }, status=500)
    
    def _fetch_stock_data(self, ticker):
        """Fetch real stock data and fundamentals using the robust data service"""
        print(f"=== StockAnalysisView: Fetching real data for {ticker} ===")
        
        # Get current price from the robust data service
        current_price = stock_data_service.get_stock_price(ticker)
        
        # Default fundamentals
        fundamentals = {
            "market_cap": "N/A",
            "roe": 15.0,
            "pe_ttm": 20.0,
            "eps_ttm": 5.0,
            "pb": 2.0,
            "dividend_yield": 2.0,
            "book_value": 50.0,
            "face_value": 10.0
        }
        
        # Try to get real fundamentals from multiple sources
        try:
            # Method 1: Try Yahoo Finance API directly
            fetched = self._fetch_fundamentals_yahoo_api(ticker)
            if fetched:
                print(f"StockAnalysisView: Got real fundamentals from Yahoo API for {ticker}")
                fundamentals = fetched
            else:
                # Method 2: Try yfinance as fallback
                fetched = self._fetch_fundamentals_yfinance(ticker)
                if fetched:
                    print(f"StockAnalysisView: Got real fundamentals from yfinance for {ticker}")
                    fundamentals = fetched
                else:
                    # Method 3: Try Alpha Vantage for fundamentals
                    fetched = self._fetch_fundamentals_alpha_vantage(ticker)
                    if fetched:
                        print(f"StockAnalysisView: Got real fundamentals from Alpha Vantage for {ticker}")
                        fundamentals = fetched
                    else:
                        print(f"StockAnalysisView: Using fallback fundamentals for {ticker}")
        except Exception as e:
            print(f"StockAnalysisView: Error getting fundamentals: {e}")
        
        print(f"StockAnalysisView: Returning price {current_price} and fundamentals for {ticker}")
        return current_price, fundamentals
    
    def _fetch_fundamentals_yahoo_api(self, ticker):
        """Fetch fundamentals from Yahoo Finance API"""
        try:
            import requests
            
            symbol_variants = [f"{ticker}.NS", f"{ticker}.BO", ticker]
            
            for symbol in symbol_variants:
                try:
                    url = "https://query1.finance.yahoo.com/v10/finance/quoteSummary/"
                    params = {
                        "symbol": symbol,
                        "modules": "defaultKeyStatistics,financialData,summaryDetail"
                    }
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "application/json",
                        "Referer": "https://finance.yahoo.com/"
                    }
                    
                    response = requests.get(url, params=params, headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        result = data.get("quoteSummary", {}).get("result", [])
                        if result:
                            summary = result[0]
                            financial_data = summary.get("financialData", {})
                            key_stats = summary.get("defaultKeyStatistics", {})
                            summary_detail = summary.get("summaryDetail", {})
                            
                            if financial_data or key_stats:
                                return {
                                    "market_cap": self._format_market_cap(key_stats.get('marketCap')),
                                    "roe": financial_data.get('returnOnEquity', {}).get('raw', 15.0) * 100 if financial_data.get('returnOnEquity', {}).get('raw') else 15.0,
                                    "pe_ttm": key_stats.get('trailingPE', {}).get('raw', 20.0) if key_stats.get('trailingPE', {}).get('raw') else 20.0,
                                    "eps_ttm": key_stats.get('trailingEps', {}).get('raw', 5.0) if key_stats.get('trailingEps', {}).get('raw') else 5.0,
                                    "pb": key_stats.get('priceToBook', {}).get('raw', 2.0) if key_stats.get('priceToBook', {}).get('raw') else 2.0,
                                    "dividend_yield": summary_detail.get('dividendYield', {}).get('raw', 2.0) * 100 if summary_detail.get('dividendYield', {}).get('raw') else 2.0,
                                    "book_value": key_stats.get('bookValue', {}).get('raw', 50.0) if key_stats.get('bookValue', {}).get('raw') else 50.0,
                                    "face_value": key_stats.get('faceValue', {}).get('raw', 10.0) if key_stats.get('faceValue', {}).get('raw') else 10.0
                                }
                except Exception as e:
                    print(f"Yahoo API fundamentals error for {symbol}: {e}")
                    continue
        except Exception as e:
            print(f"Yahoo API fundamentals error: {e}")
        return None
    
    def _fetch_fundamentals_yfinance(self, ticker):
        """Fetch fundamentals from yfinance"""
        try:
            import yfinance as yf
            symbol_variants = [f"{ticker}.NS", f"{ticker}.BO", ticker]
            
            for symbol in symbol_variants:
                try:
                    stock = yf.Ticker(symbol)
                    info = stock.info
                    
                    if info and len(info) > 10:  # Ensure we got real data
                        return {
                            "market_cap": self._format_market_cap(info.get('marketCap')),
                            "roe": info.get('returnOnEquity', 15.0) * 100 if info.get('returnOnEquity') else 15.0,
                            "pe_ttm": info.get('trailingPE', 20.0),
                            "eps_ttm": info.get('trailingEps', 5.0),
                            "pb": info.get('priceToBook', 2.0),
                            "dividend_yield": info.get('dividendYield', 2.0) * 100 if info.get('dividendYield') else 2.0,
                            "book_value": info.get('bookValue', 50.0),
                            "face_value": info.get('faceValue', 10.0)
                        }
                except Exception as e:
                    print(f"yfinance fundamentals error for {symbol}: {e}")
                    continue
        except ImportError:
            print("yfinance not available for fundamentals")
        except Exception as e:
            print(f"yfinance fundamentals error: {e}")
        return None
    
    def _fetch_fundamentals_alpha_vantage(self, ticker):
        """Fetch fundamentals from Alpha Vantage"""
        try:
            import requests
            import os
            
            api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
            if not api_key or api_key == 'demo':
                return None
            
            symbol_variants = [f"{ticker}.BSE", f"{ticker}.NSE", ticker]
            
            for symbol in symbol_variants:
                try:
                    url = "https://www.alphavantage.co/query"
                    params = {
                        'function': 'OVERVIEW',
                        'symbol': symbol,
                        'apikey': api_key
                    }
                    
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if 'Symbol' in data and data['Symbol']:
                            return {
                                "market_cap": self._format_market_cap(data.get('MarketCapitalization')),
                                "roe": float(data.get('ReturnOnEquityTTM', 15.0)) if data.get('ReturnOnEquityTTM') else 15.0,
                                "pe_ttm": float(data.get('PERatio', 20.0)) if data.get('PERatio') else 20.0,
                                "eps_ttm": float(data.get('EPS', 5.0)) if data.get('EPS') else 5.0,
                                "pb": float(data.get('PriceToBookRatio', 2.0)) if data.get('PriceToBookRatio') else 2.0,
                                "dividend_yield": float(data.get('DividendYield', 2.0)) * 100 if data.get('DividendYield') else 2.0,
                                "book_value": float(data.get('BookValue', 50.0)) if data.get('BookValue') else 50.0,
                                "face_value": float(data.get('FaceValue', 10.0)) if data.get('FaceValue') else 10.0
                            }
                except Exception as e:
                    print(f"Alpha Vantage fundamentals error for {symbol}: {e}")
                    continue
        except Exception as e:
            print(f"Alpha Vantage fundamentals error: {e}")
        return None
    
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
    
    def _generate_analysis(self, ticker, current_price, buy_price, fundamentals):
        """Generate personalized analysis"""
        price_change = current_price - buy_price
        price_change_percent = (price_change / buy_price * 100) if buy_price > 0 else 0
        
        if price_change_percent > 10:
            return f"Strong performance! {ticker} is up {price_change_percent:.1f}% from your buy price. Consider taking partial profits if you need liquidity."
        elif price_change_percent > 5:
            return f"Good performance! {ticker} is up {price_change_percent:.1f}% from your buy price. Hold for further gains."
        elif price_change_percent > 0:
            return f"Positive performance! {ticker} is up {price_change_percent:.1f}% from your buy price. Consider holding for long-term growth."
        elif price_change_percent > -5:
            return f"Minor decline. {ticker} is down {abs(price_change_percent):.1f}% from your buy price. This is normal market volatility."
        elif price_change_percent > -10:
            return f"Moderate decline. {ticker} is down {abs(price_change_percent):.1f}% from your buy price. Consider if this aligns with your investment thesis."
        else:
            return f"Significant decline. {ticker} is down {abs(price_change_percent):.1f}% from your buy price. Review your investment strategy and consider stop-loss."

# =====================
# Stock History
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class StockHistoryView(View):
    def get(self, request, ticker):
        """Get stock price history using real data from Yahoo Finance"""
        try:
            period = request.GET.get('period', '1y')
            interval = request.GET.get('interval', '1d')
            
            # Fetch real historical data from Yahoo Finance
            history = stock_data_service.get_stock_history(ticker, period=period, interval=interval)
            
            if history:
                dates = [item['date'] for item in history]
                prices = [item['price'] for item in history]
                
                return JsonResponse({
                    "ticker": ticker,
                    "period": period,
                    "history": prices,  # Return prices array for frontend compatibility
                    "dates": dates,  # Also return dates for reference
                    "data": {
                        "dates": dates,
                        "prices": prices
                    }
                })
            else:
                # Fallback to mock data if real data unavailable
                import random
                from datetime import datetime, timedelta
                
                end_date = datetime.now()
                days_map = {'1d': 1, '7d': 7, '1m': 30, '1mo': 30, '3mo': 90, '6m': 180, '6mo': 180, '1y': 365}
                days = days_map.get(period, 365)
                start_date = end_date - timedelta(days=days)
                
                dates = []
                prices = []
                current_price = stock_data_service.get_stock_price(ticker) or 100.0
                
                for i in range(min(days, 365)):
                    date = start_date + timedelta(days=i)
                    if i == 0:
                        price = current_price * random.uniform(0.8, 1.2)
                    else:
                        price = prices[-1] * random.uniform(0.98, 1.02)
                    
                    dates.append(date.strftime('%Y-%m-%d'))
                    prices.append(round(price, 2))
                
                return JsonResponse({
                    "ticker": ticker,
                    "period": period,
                    "data": {
                        "dates": dates,
                        "prices": prices
                    },
                    "note": "Using fallback data"
                })
            
        except Exception as e:
            logger.error(f"Stock history fetch error for {ticker}: {e}")
            return JsonResponse({
                "error": f"History fetch failed: {str(e)}",
                "ticker": ticker
            }, status=500)

# =====================
# Mutual Fund Analysis
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class MutualFundAnalysisView(View):
    def get(self, request, scheme_id, buy_nav, units):
        """Analyze a mutual fund with buy NAV and units"""
        try:
            buy_nav = float(buy_nav)
            units = float(units)

            # Fetch real mutual fund data using the service
            fund_details = mf_data_service.get_fund_by_id(scheme_id)

            if not fund_details:
                return JsonResponse({
                    "error": "FUND_NOT_FOUND",
                    "reasoning": f"Mutual fund with Scheme ID {scheme_id} could not be found."
                }, status=404)

            current_nav = fund_details.get('nav')
            scheme_name = fund_details.get('scheme_name', scheme_id)

            if current_nav is None:
                return JsonResponse({
                    "error": "NAV_NOT_AVAILABLE",
                    "reasoning": f"Could not retrieve the current NAV for {scheme_name}."
                }, status=500)

            current_nav = float(current_nav)
            
            # If buy_nav is 0, use current_nav for an uninvested analysis
            effective_buy_nav = current_nav if buy_nav == 0 else buy_nav

            total_investment = effective_buy_nav * units
            current_value = current_nav * units
            profit_loss = current_value - total_investment
            profit_loss_percent = (profit_loss / total_investment * 100) if total_investment > 0 else 0

            # Generate analysis
            if profit_loss_percent > 15:
                analysis = f"Excellent performance! Your investment in {scheme_name} is up {profit_loss_percent:.1f}%. Consider re-evaluating your allocation or booking partial profits if it aligns with your goals."
                strategy = "This fund is performing exceptionally well. Monitor its performance and consider if it still fits your long-term strategy."
            elif profit_loss_percent > 8:
                analysis = f"Good performance! The fund is up {profit_loss_percent:.1f}%. Continue your SIPs or hold your investment for long-term wealth creation."
                strategy = "Solid returns. This fund is a strong performer in your portfolio. Staying invested is a good strategy."
            elif profit_loss_percent > 0:
                analysis = f"Positive performance. Your investment is up {profit_loss_percent:.1f}%. Stay invested to benefit from long-term growth."
                strategy = "The fund is delivering positive returns. It's advisable to hold for the long term."
            elif profit_loss_percent > -5:
                analysis = f"Minor decline. The fund is down {abs(profit_loss_percent):.1f}%. This is likely due to normal market volatility. No action needed for long-term investors."
                strategy = "Short-term fluctuations are normal. For long-term goals, it's best to ignore minor dips."
            elif profit_loss_percent > -10:
                analysis = f"Moderate decline. Your investment is down {abs(profit_loss_percent):.1f}%. Review the fund's fundamentals and compare with peers to ensure it still meets your risk appetite."
                strategy = "The fund is underperforming. It's a good time to review its strategy and your investment thesis."
            else:
                analysis = f"Significant decline. The fund is down {abs(profit_loss_percent):.1f}%. It's crucial to reassess this investment. Check for any fundamental changes in the fund's strategy or sector."
                strategy = "High underperformance warrants a thorough review. Consider consulting a financial advisor about whether to hold or exit."

            return JsonResponse({
                "scheme_id": scheme_id,
                "scheme_name": scheme_name,
                "current_nav": current_nav,
                "your_buy_nav": buy_nav,
                "num_units": units,
                "total_investment": total_investment,
                "current_value": current_value,
                "pnl_total": profit_loss,
                "pnl_percentage": profit_loss_percent,
                "personalized_advice": analysis,
                "strategy_description": strategy,
                "reasoning": f"Based on your investment of {units} units at an average NAV of ₹{effective_buy_nav:.2f}, your current investment value is ₹{current_value:.2f}."
            })

        except Exception as e:
            logger.error(f"MutualFundAnalysisView error: {e}")
            return JsonResponse({
                "error": f"Analysis failed: {str(e)}",
                "scheme_id": scheme_id
            }, status=500)

# =====================
# Mutual Fund History
# =====================

@method_decorator(csrf_exempt, name="dispatch")
class MutualFundHistoryView(View):
    def get(self, request, scheme_id):
        """Get mutual fund NAV history"""
        try:
            period = request.GET.get('period', '1y')
            
            # Map frontend period to days for the service
            period_map = {'1d': 1, '7d': 7, '1m': 30, '6m': 180, '1y': 365}
            days = period_map.get(period.lower(), 365)

            # Fetch real historical NAV data
            history_data = mf_data_service.get_fund_nav_history(scheme_id, days=days)

            if history_data:
                # Ensure data is sorted by date
                history_data.sort(key=lambda x: x.get('date', ''))
                
                dates = []
                navs = []
                for item in history_data:
                    try:
                        # Ensure 'nav' and 'date' keys exist and NAV is a valid float
                        if 'nav' in item and 'date' in item:
                            nav = float(item['nav'])
                            dates.append(item['date'])
                            navs.append(nav)
                    except (ValueError, TypeError):
                        # Log the error and skip the invalid data point
                        logger.warning(f"Skipping invalid NAV data point for {scheme_id}: {item}")
                        continue
                
                return JsonResponse({
                    "scheme_id": scheme_id,
                    "period": period,
                    "history": navs, # For frontend compatibility
                    "dates": dates,
                    "data": {
                        "dates": dates,
                        "navs": navs
                    }
                })
            else:
                # Fallback to mock data if real data is not available
                raise ValueError("No history found, using fallback.")

        except Exception as e:
            logger.warning(f"Could not fetch real MF history for {scheme_id}: {e}. Falling back to mock data.")
            # Mock historical NAV data as a fallback
            import random
            from datetime import datetime, timedelta
            
            end_date = datetime.now()
            days = 365
            start_date = end_date - timedelta(days=days)
            
            dates = []
            navs = []
            # Try to get at least the current NAV to make mock data more realistic
            try:
                fund_details = mf_data_service.get_fund_by_id(scheme_id)
                base_nav = float(fund_details.get('nav', random.uniform(50, 200)))
            except:
                base_nav = random.uniform(50, 200)

            # Generate mock data backwards from current NAV
            current_mock_nav = base_nav
            for i in range(days):
                date = end_date - timedelta(days=i)
                dates.append(date.strftime('%Y-%m-%d'))
                navs.append(round(current_mock_nav, 4))
                current_mock_nav /= random.uniform(0.998, 1.002) # Simulate previous day's NAV
            
            dates.reverse()
            navs.reverse()

            return JsonResponse({
                "scheme_id": scheme_id,
                "period": period,
                "data": {
                    "dates": dates,
                    "navs": navs
                },
                "note": "Using fallback mock data as real data was unavailable."
            })

# =====================
# Development Version
# =====================

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
# Chat View
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
                "intent": intent
            })
            
        except Exception as e:
            return JsonResponse({
                "error": f"Chat processing failed: {str(e)}"
            }, status=500)
    
    def _parse_intent(self, message):
        """Parse user intent from message"""
        message_lower = message.lower()
        
        # Market data queries
        if any(word in message_lower for word in ["market", "nifty", "sensex", "stock", "price", "index", "indices"]):
            return {"intent": "market_data", "confidence": 0.9}
        
        # Portfolio queries
        if any(word in message_lower for word in ["portfolio", "holdings", "stocks", "investments", "my stocks"]):
            return {"intent": "portfolio", "confidence": 0.9}
        
        # Add to portfolio queries
        if any(word in message_lower for word in ["add", "buy", "purchase", "invest"]):
            return {"intent": "add_to_portfolio", "confidence": 0.8}
        
        # Advice queries
        if any(word in message_lower for word in ["advice", "recommend", "should i", "what do you think"]):
            return {"intent": "advice", "confidence": 0.8}
        
        # Default to general chat
        return {"intent": "general", "confidence": 0.5}
    
    def _handle_market_data_query(self, message):
        """Handle market data queries"""
        return "I can help you with market data! You can ask about NIFTY, SENSEX, or specific stock prices. What would you like to know?"
    
    def _handle_portfolio_query(self, request, message):
        """Handle portfolio queries"""
        if not request.user.is_authenticated:
            return "Please log in to view your portfolio."
        
        try:
            holdings = Holding.objects.filter(portfolio__user=request.user)
            if not holdings.exists():
                return "You don't have any stocks in your portfolio yet. Add some stocks to get started!"
            
            portfolio_summary = []
            total_invested = Decimal('0')
            total_current_value = Decimal('0')
            
            for holding in holdings:
                current_price = stock_data_service.get_stock_price(holding.ticker)
                current_value = Decimal(str(current_price)) * holding.quantity
                invested_value = holding.average_buy_price * holding.quantity
                
                total_invested += invested_value
                total_current_value += current_value
                
                profit_loss = current_value - invested_value
                profit_loss_percent = (profit_loss / invested_value * 100) if invested_value > 0 else 0
                
                portfolio_summary.append(
                    f"{holding.ticker}: {holding.quantity} shares at ₹{holding.average_buy_price} "
                    f"(Current: ₹{current_price:.2f}, P/L: {profit_loss_percent:+.1f}%)"
                )
            
            total_profit_loss = total_current_value - total_invested
            total_profit_loss_percent = (total_profit_loss / total_invested * 100) if total_invested > 0 else 0
            
            summary = f"Your portfolio summary:\n" + "\n".join(portfolio_summary)
            summary += f"\n\nTotal Investment: ₹{total_invested:.2f}"
            summary += f"\nCurrent Value: ₹{total_current_value:.2f}"
            summary += f"\nTotal P/L: ₹{total_profit_loss:.2f} ({total_profit_loss_percent:+.1f}%)"
            
            return summary
            
        except Exception as e:
            return f"Sorry, I couldn't retrieve your portfolio information. Error: {str(e)}"
    
    def _handle_add_portfolio_query(self, message):
        """Handle add to portfolio queries"""
        return "To add stocks to your portfolio, use the search function and click 'Add to Portfolio' after analyzing a stock."
    
    def _handle_advice_query(self, message):
        """Handle advice queries"""
        advice_responses = [
            "Based on current market conditions, I recommend diversifying your portfolio across different sectors.",
            "Consider investing in blue-chip stocks for stable returns and growth stocks for higher potential gains.",
            "Always do your own research before making investment decisions. Past performance doesn't guarantee future results.",
            "For long-term wealth creation, consider systematic investment plans (SIPs) in mutual funds.",
            "Keep an eye on market trends but don't let short-term volatility affect your long-term investment strategy."
        ]
        return random.choice(advice_responses)
    
    def _handle_general_query(self, message):
        """Handle general queries - STRICTLY use Gemini ONLY for non-financial general questions like 'hi', 'what can you do', etc."""
        message_lower = message.lower().strip()
        
        # Comprehensive financial keywords - if ANY of these appear, DO NOT use Gemini
        financial_keywords = [
            "stock", "share", "price", "market", "nifty", "sensex", "portfolio", 
            "invest", "investment", "mutual fund", "nav", "returns", "profit", 
            "loss", "buy", "sell", "ticker", "equity", "bond", "dividend", 
            "valuation", "pe ratio", "eps", "revenue", "earnings", "financial",
            "analysis", "analyze", "chart", "graph", "trend", "sector", "index",
            "holding", "asset", "fund", "scheme", "amc", "aum", "sip", "lumpsum",
            "capital", "gains", "tax", "stcg", "ltcg", "brokerage", "stocks",
            "shares", "equities", "securities", "trading", "trader", "investor",
            "portfolio", "diversification", "risk", "return", "volatility", "beta",
            "alpha", "sharpe", "ratio", "fundamental", "technical", "candlestick"
        ]
        
        # Check if it's a financial query - STRICT CHECK
        is_financial_query = any(keyword in message_lower for keyword in financial_keywords)
        
        # ONLY use Gemini for completely non-financial general queries like greetings, help, what can you do
        # Examples: "hi", "hello", "what can you do", "help", "how are you", "thanks"
        if not is_financial_query:
            # Additional check: Only use Gemini for very simple general queries
            simple_general_queries = [
                "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
                "what can you do", "what do you do", "help", "how are you", "thanks",
                "thank you", "who are you", "what are you", "tell me about yourself"
            ]
            
            is_simple_general = any(query in message_lower for query in simple_general_queries)
            
            # ONLY use Gemini for simple general queries, NOT for any financial context
            if is_simple_general:
                try:
                    from .gemini_service import gemini_service
                    if gemini_service and gemini_service.enabled:
                        # Use Gemini ONLY for general conversation, NOT for financial data
                        intent_response = gemini_service.understand_user_query(message, context={})
                        
                        # Triple-check it's not finance-related
                        is_finance_related = intent_response.get("is_finance_related", False)
                        if not is_finance_related:
                            # Generate response using Gemini for general queries only
                            # NEVER pass any financial data to Gemini
                            response = gemini_service.generate_response(
                                message,
                                financial_data={},  # Never pass financial data to Gemini
                                portfolio_data={},  # Never pass portfolio data to Gemini
                                market_data={},  # Never pass market data to Gemini
                                conversation_history=[],
                                is_finance_related=False
                            )
                            
                            # Final safety check: if response contains financial keywords, reject it
                            response_lower = response.lower() if response else ""
                            if not any(keyword in response_lower for keyword in financial_keywords[:10]):
                                logger.info("Gemini used for general non-financial query")
                                return response
                            else:
                                logger.warning("Gemini response contained financial keywords, rejecting")
                except ImportError:
                    # Gemini not available, fallback to rule-based
                    logger.debug("Gemini service not available, using rule-based chat")
                except Exception as e:
                    logger.debug(f"Gemini error: {e}, falling back to rule-based")
        
        # Rule-based responses for financial queries or when Gemini is unavailable
        # These responses are safe and don't use Gemini
        general_responses = [
            "I'm your AI investment assistant! I can help you with market data, portfolio analysis, and investment advice.",
            "Feel free to ask me about stocks, market trends, or your portfolio. I'm here to help!",
            "I'm your AI investment assistant. Ask me about market data, your portfolio, or investment strategies.",
            "Hello! I can help you with stock analysis, portfolio management, and market insights. What would you like to know?",
            "Hi there! I'm here to assist with your investment queries. Try asking about stocks, mutual funds, or your portfolio."
        ]
        return random.choice(general_responses)

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
    return render(request, 'advisor/index.html', {
        'user_first_name': request.user.first_name if request.user.is_authenticated else '',
        'csrf_token_value': request.META.get('CSRF_COOKIE', '')
    })

def profile_view(request):
    """User profile view"""
    return render(request, 'advisor/profile.html')

def about_view(request):
    """About page view"""
    return render(request, 'advisor/about.html')

def portfolio_page_view(request):
    """Portfolio page view"""
    return render(request, 'advisor/portfolio.html')
