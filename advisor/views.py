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
import requests

# Optional: live market data via yfinance (fallback to mock if unavailable)
try:
    import yfinance as yf  # type: ignore
except Exception:  # pragma: no cover
    yf = None


# --------------------------
# Yahoo helpers
# --------------------------

def yahoo_search(query: str, quotes_count: int = 20, region: str = "IN", lang: str = "en-IN") -> list:
    try:
        url = "https://query1.finance.yahoo.com/v1/finance/search"
        params = {"q": query, "quotesCount": quotes_count, "newsCount": 0, "region": region, "lang": lang}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
        r = requests.get(url, params=params, headers=headers, timeout=8)
        if r.status_code == 200:
            return (r.json() or {}).get("quotes", []) or []
    except Exception:
        pass
    return []


def yahoo_autocomplete(query: str, region: str = "IN", lang: str = "en-IN") -> list:
    try:
        url = "https://query2.finance.yahoo.com/v6/finance/autocomplete"
        params = {"query": query, "region": region, "lang": lang}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
        r = requests.get(url, params=params, headers=headers, timeout=8)
        if r.status_code == 200:
            return ((r.json() or {}).get("ResultSet", {}) or {}).get("Result", []) or []
    except Exception:
        pass
    return []


# --------------------------
# Mutual fund helpers (MFAPI)
# --------------------------

def mfapi_search(query: str) -> list:
    """Search Indian mutual funds via MFAPI (AMFI mirror).

    Returns a list of dicts: { symbol, name } where symbol is scheme code
    when a Yahoo-compatible symbol is not available. The frontend expects
    this shape.
    """
    q = (query or "").strip()
    if not q:
        return []
    
    # Try multiple search variations for better results
    search_queries = [q]
    
    # Add variations for common fund name patterns
    if "mid cap" in q.lower():
        search_queries.extend(["midcap", "mid cap", "mid-cap"])
    if "large cap" in q.lower():
        search_queries.extend(["largecap", "large cap", "large-cap"])
    if "small cap" in q.lower():
        search_queries.extend(["smallcap", "small cap", "small-cap"])
    if "growth" in q.lower():
        search_queries.append(q.replace("growth", "").strip())
    if "direct" in q.lower():
        search_queries.append(q.replace("direct", "").strip())
    if "regular" in q.lower():
        search_queries.append(q.replace("regular", "").strip())
    
    all_results = []
    seen = set()
    
    for search_q in search_queries:
        try:
            url = "https://api.mfapi.in/mf/search"
            r = requests.get(url, params={"q": search_q}, timeout=8)
            if r.status_code == 200:
                items = r.json() or []
                for itm in items:
                    code = str(itm.get("schemeCode") or "").strip()
                    name = str(itm.get("schemeName") or "").strip()
                    if not code or not name:
                        continue
                    key = (code, name)
                    if key in seen:
                        continue
                    seen.add(key)
                    all_results.append({"symbol": code, "name": name})
        except Exception:
            continue
    
    return all_results[:15]  # Return more results for better matching


def mfapi_latest_nav(scheme_code_or_name: str):
    """Return (scheme_name, latest_nav) using MFAPI, or None."""
    s = (scheme_code_or_name or "").strip()
    if not s:
        return None
    # Direct by numeric scheme code
    if s.isdigit():
        try:
            r = requests.get(f"https://api.mfapi.in/mf/{s}", timeout=8)
            if r.status_code == 200:
                data = r.json() or {}
                name = (data.get("meta", {}) or {}).get("scheme_name") or s
                his = data.get("data") or []
                if his:
                    nav = float(his[0].get("nav") or his[0].get("NAV"))
                    return (name, nav)
        except Exception:
            pass
        return None
    # Otherwise search then resolve by first match
    matches = mfapi_search(s)
    if not matches:
        return None
    first = matches[0]
    return mfapi_latest_nav(first.get("symbol") or "")


def mfapi_history(scheme_code_or_name: str, max_days: int = 1095):
    """Return (scheme_name, [(date_iso, nav_float), ...]) using MFAPI.

    Accepts numeric scheme code or a fuzzy name.
    """
    s = (scheme_code_or_name or "").strip()
    if not s:
        return None
    # Resolve to code if not numeric
    code = s
    if not s.isdigit():
        matches = mfapi_search(s)
        if not matches:
            return None
        code = matches[0].get("symbol") or ""
    if not code:
        return None
    try:
        r = requests.get(f"https://api.mfapi.in/mf/{code}", timeout=8)
        if r.status_code == 200:
            data = r.json() or {}
            name = (data.get("meta", {}) or {}).get("scheme_name") or s
            raw = data.get("data") or []
            hist = []
            for itm in raw[:max_days]:
                dt = str(itm.get("date") or "")
                try:
                    nav = float(itm.get("nav") or itm.get("NAV"))
                except Exception:
                    continue
                if dt and nav:
                    hist.append((dt, nav))
            return (name, hist)
    except Exception:
        pass
    return None


def resolve_symbol_via_search(ticker_or_name: str) -> str | None:
    """Resolve a canonical Yahoo symbol (prefer .NS then .BO) for a given query.
    Returns the symbol with suffix when available.
    """
    q = (ticker_or_name or "").strip()
    if not q:
        return None
    # First try search API
    quotes = yahoo_search(q)
    best = None
    for itm in quotes:
        sym = (itm.get("symbol") or "").upper()
        qtype = (itm.get("quoteType") or "").upper()
        if qtype not in {"EQUITY", "ETF"}:
            continue
        # Prefer NSE
        if sym.endswith(".NS"):
            return sym
        if sym.endswith(".BO") and best is None:
            best = sym
        if best is None:
            best = sym
    if best:
        return best
    # Fallback to autocomplete
    ac = yahoo_autocomplete(q)
    best = None
    for itm in ac:
        sym = (itm.get("symbol") or "").upper()
        tdisp = (itm.get("typeDisp") or "").upper()
        if tdisp not in {"EQUITY", "ETF", "MUTUAL FUND", "FUND"}:
            continue
        if sym.endswith(".NS"):
            return sym
        if sym.endswith(".BO") and best is None:
            best = sym
        if best is None:
            best = sym
    return best


def _normalize_base_ticker(raw: str) -> str:
    if not raw:
        return ""
    t = raw.upper().strip()
    # strip leading markers
    if t.startswith("$") or t.startswith("^"):
        t = t[1:]
    # remove NSE/BSE suffix if present already
    if t.endswith(".NS") or t.endswith(".BO"):
        t = t[:-3]
    # strip common trading suffixes
    t = re.sub(r"-(EQ|BE|BL)$", "", t)
    # remove all non-alphanumeric
    t = re.sub(r"[^A-Z0-9]", "", t)
    return t


def _resolve_yf_symbols(ticker: str) -> list:
    raw = (ticker or "").upper().strip()
    base = _normalize_base_ticker(raw)
    candidates = []
    # If user already provided a suffixed symbol, try it first
    if raw.endswith('.NS') or raw.endswith('.BO'):
        candidates.append(raw)
    if base:
        candidates.extend([f"{base}.NS", f"{base}.BO", base])
    # de-duplicate while preserving order
    seen = set()
    ordered = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered


def get_live_price(ticker: str) -> float | None:
    if yf is None:
        return None
    # Try direct symbol variants first
    for sym in _resolve_yf_symbols(ticker):
        try:
            tk = yf.Ticker(sym)
            price = getattr(getattr(tk, "fast_info", object()), "last_price", None)
            if price is None:
                info = getattr(tk, "info", {}) or {}
                price = info.get("currentPrice") or info.get("regularMarketPrice")
            if price:
                return float(price)
        except Exception:
            continue
    # Fallback to Yahoo search resolution
    resolved = resolve_symbol_via_search(ticker)
    if resolved:
        try:
            tk = yf.Ticker(resolved)
            price = getattr(getattr(tk, "fast_info", object()), "last_price", None)
            if price is None:
                info = getattr(tk, "info", {}) or {}
                price = info.get("currentPrice") or info.get("regularMarketPrice")
            if price:
                return float(price)
        except Exception:
            pass
    return None


def get_price_history(ticker: str, days: int = 60) -> list:
    # Helper: Yahoo chart JSON API fallback
    def _yahoo_chart_series(sym: str) -> list:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
            params = {"range": "1y", "interval": "1d"}
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, params=params, headers=headers, timeout=8)
            if r.status_code == 200:
                js = r.json() or {}
                res = (((js.get("chart", {}) or {}).get("result", []) or []) or [None])[0]
                if res:
                    closes = (res.get("indicators", {}) or {}).get("quote", [])
                    if closes and "close" in closes[0]:
                        arr = [x for x in closes[0]["close"] if isinstance(x, (int, float))]
                        if arr and len(arr) >= 5:
                            return arr[-days:]
        except Exception:
            pass
        return []

    # Build candidate symbols
    symbols_to_try = _resolve_yf_symbols(ticker) + [ticker.upper(), ticker.lower()]
    resolved = resolve_symbol_via_search(ticker)
    if resolved:
        symbols_to_try = [resolved] + symbols_to_try
    # ensure NSE/BSE suffixed are first
    base = _normalize_base_ticker(ticker)
    symbols_to_try = [f"{base}.NS", f"{base}.BO"] + symbols_to_try

    # Try yfinance download first
    if yf is not None:
        periods_to_try = [f"{max(30, days)}d", "3mo", "6mo", "1y", "2y"]
        for sym in symbols_to_try:
            for period in periods_to_try:
                try:
                    df = yf.download(sym, period=period, interval="1d", progress=False, auto_adjust=False, threads=False)
                    if df is not None and not df.empty and len(df) > 5:
                        closes = df["Close"].dropna().astype(float).tolist()
                        if closes and len(closes) >= 5:
                            return closes[-days:]
                except Exception:
                    continue

    # Fallback: Yahoo chart JSON API
    for sym in symbols_to_try:
        series = _yahoo_chart_series(sym)
        if series:
            return series

    return []  # Return empty list if no live data available


def get_latest_close_from_history(ticker: str) -> float | None:
    history = get_price_history(ticker, days=5)
    if history:
        return float(history[-1])
    return None


# --------------------------
# Fundamentals helpers
# --------------------------

def get_stock_fundamentals(ticker: str) -> dict:
    """Fetch a compact set of fundamentals using yfinance."""
    result = {
        "market_cap": None,
        "pe_ttm": None,
        "pb": None,
        "roe": None,
        "eps_ttm": None,
        "dividend_yield": None,
        "book_value": None,
        "face_value": None,
        "industry_pe": None,
    }
    if yf is None:
        return result
    symbols = _resolve_yf_symbols(ticker) + [ticker]
    for sym in symbols:
        try:
            tk = yf.Ticker(sym)
            info = getattr(tk, "info", {}) or {}
            if not info:
                continue
            result.update({
                "market_cap": info.get("marketCap"),
                "pe_ttm": info.get("trailingPE"),
                "pb": info.get("priceToBook"),
                "roe": (info.get("returnOnEquity") * 100) if isinstance(info.get("returnOnEquity"), (int, float)) else None,
                "eps_ttm": info.get("trailingEps"),
                "dividend_yield": (info.get("dividendYield") * 100) if isinstance(info.get("dividendYield"), (int, float)) else None,
                "book_value": info.get("bookValue"),
                "face_value": info.get("faceValue"),
                "industry_pe": info.get("trailingPE")
            })
            return result
        except Exception:
            continue
    return result


def evaluate_fundamentals(f: dict) -> dict:
    notes = []
    score = 0
    pe = f.get("pe_ttm")
    pb = f.get("pb")
    roe = f.get("roe")
    dy = f.get("dividend_yield")
    if isinstance(roe, (int, float)) and roe >= 15:
        notes.append("ROE looks healthy (≥15%), suggests efficient capital use.")
        score += 1
    if isinstance(pe, (int, float)) and pe <= 20:
        notes.append("P/E is on the reasonable side (≤20).")
        score += 1
    if isinstance(pb, (int, float)) and pb <= 3:
        notes.append("P/B indicates valuation not too stretched.")
        score += 1
    if isinstance(dy, (int, float)) and dy >= 1:
        notes.append("Offers some dividend yield, aiding total return.")
    return {"score": score, "notes": notes}

# =====================
# Page Views (Frontend)
# =====================


@login_required
def chat_view(request):
    """Serve the main chatbot interface (index.html)."""
    return render(request, "advisor/index.html")


@login_required
def profile_view(request):
    """Serve the profile page."""
    return render(request, "advisor/profile.html")


def about_view(request):
    """Serve the about page."""
    return render(request, "advisor/about.html")

@login_required
def portfolio_page_view(request):
    """Serve the portfolio page with user holdings."""
    holdings = Holding.objects.filter(portfolio__user=request.user)
    return render(request, "advisor/portfolio.html", {"holdings": holdings})


# =====================
# Portfolio API Views
# =====================

class PortfolioHealthView(View):
    def get(self, request):
        # If user is not authenticated, return a friendly default response
        # so the UI can render a neutral state instead of failing.
        if not request.user.is_authenticated:
            return JsonResponse({
                "overall_score": 0,
                "diversification": {
                    "score": 0,
                    "feedback": "Login to see personalized diversification insights."
                },
                "risk": {
                    "score": 0,
                    "feedback": "Login to evaluate your portfolio risk."
                },
                "performance": {
                    "score": 0,
                    "feedback": "Login to review your portfolio performance."
                }
            })

        # Fetch all holdings for the logged-in user
        holdings = Holding.objects.filter(portfolio__user=request.user)

        if not holdings.exists():
            return JsonResponse({
                "overall_score": 0,
                "diversification": {
                    "score": 0,
                    "feedback": "No holdings found. Add stocks to build your portfolio."
                },
                "risk": {
                    "score": 0,
                    "feedback": "Risk cannot be calculated without holdings."
                },
                "performance": {
                    "score": 0,
                    "feedback": "Performance cannot be evaluated without holdings."
                }
            })

        # --------------------------
        # Diversification: based on unique tickers
        # --------------------------
        unique_tickers = holdings.values_list("ticker", flat=True).distinct().count()
        diversification_score = min(10, unique_tickers * 2)  # crude: 5+ tickers → score ~10
        diversification_feedback = (
            "Excellent diversification across multiple stocks."
            if diversification_score >= 8 else
            "Moderately diversified, consider adding more stocks."
            if diversification_score >= 5 else
            "Portfolio is concentrated, diversify to reduce risk."
        )

        # --------------------------
        # Risk: based on concentration
        # --------------------------
        total_qty = sum(h.quantity for h in holdings)
        largest_share = max(h.quantity for h in holdings) if total_qty > 0 else 0
        largest_pct = (largest_share / total_qty) * 100 if total_qty > 0 else 0

        if largest_pct > 70:
            risk_score = 3
            risk_feedback = "High concentration in a single stock. Very risky."
        elif largest_pct > 40:
            risk_score = 5
            risk_feedback = "Moderate concentration. Somewhat risky."
        else:
            risk_score = 8
            risk_feedback = "Well balanced portfolio risk."

        # --------------------------
        # Performance: consistent mock data (no internet required)
        # --------------------------
        # Use consistent mock performance based on user ID for stability
        user_id_hash = hash(request.user.id) % 100
        # Create consistent "performance" based on user ID
        if user_id_hash > 70:
            performance_score = 8
            performance_feedback = "Your portfolio is performing excellently relative to cost."
        elif user_id_hash > 40:
            performance_score = 6
            performance_feedback = "Your portfolio is performing well relative to cost."
        else:
            performance_score = 4
            performance_feedback = "Portfolio underperforming slightly. Review stock picks."

        # --------------------------
        # Combine into overall score
        # --------------------------
        overall_score = round((diversification_score + risk_score + performance_score) / 3)

        response = {
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

        return JsonResponse(response)

class PortfolioDetailView(View):
    def get(self, request):
        """Return actual holdings for logged-in user."""
        holdings = Holding.objects.filter(portfolio__user=request.user)
        data = [
            {
                "ticker": h.ticker,
                "quantity": h.quantity,
                "average_buy_price": float(h.average_buy_price),
                "current_price": (get_live_price(h.ticker) or get_latest_close_from_history(h.ticker) or 0.0),
                "current_value": round((get_live_price(h.ticker) or get_latest_close_from_history(h.ticker) or 0.0) * float(h.quantity), 2),
                "net_profit": round(((get_live_price(h.ticker) or get_latest_close_from_history(h.ticker) or 0.0) - float(h.average_buy_price)) * float(h.quantity), 2),
            }
            for h in holdings
        ]
        return JsonResponse({"holdings": data})

@method_decorator(csrf_exempt, name="dispatch")
class PortfolioView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Login required"}, status=401)
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
            ticker = str(data.get('ticker', '')).upper().strip()
            quantity = int(data.get('quantity', 0))
            buy_price = float(data.get('buy_price', 0))
            if not ticker or quantity <= 0 or buy_price <= 0:
                return JsonResponse({"error": "Invalid payload"}, status=400)

            # Ensure portfolio exists
            from .models import Portfolio as PortfolioModel, Holding as HoldingModel
            portfolio, _ = PortfolioModel.objects.get_or_create(user=request.user)

            try:
                holding = HoldingModel.objects.get(portfolio=portfolio, ticker=ticker)
                # Weighted average buy price update
                old_qty = float(holding.quantity)
                old_avg = float(holding.average_buy_price)
                new_qty = old_qty + float(quantity)
                new_avg = ((old_avg * old_qty) + (buy_price * float(quantity))) / new_qty if new_qty > 0 else buy_price
                holding.quantity = int(new_qty)
                holding.average_buy_price = round(new_avg, 2)
                holding.save()
            except HoldingModel.DoesNotExist:
                holding = HoldingModel.objects.create(
                    portfolio=portfolio,
                    ticker=ticker,
                    quantity=quantity,
                    average_buy_price=round(buy_price, 2)
                )

            current_price = get_live_price(ticker) or get_latest_close_from_history(ticker) or 0.0
            return JsonResponse({
                "message": "Holding saved",
                "holding": {
                    "ticker": holding.ticker,
                    "quantity": holding.quantity,
                    "average_buy_price": float(holding.average_buy_price),
                    "current_price": current_price
                }
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

class HoldingDetailView(View):
    def get(self, request, holding_id):
        try:
            h = Holding.objects.get(id=holding_id, portfolio__user=request.user)
            return JsonResponse({
                "ticker": h.ticker,
                "quantity": h.quantity,
                "average_buy_price": float(h.average_buy_price),
            })
        except Holding.DoesNotExist:
            return JsonResponse({"error": "Holding not found"}, status=404)


# =====================
# Stock API Views
# =====================

class StockNewsView(View):
    def get(self, request, ticker):
        return JsonResponse({"ticker": ticker, "news": ["Stock news 1", "Stock news 2"]})

class StockSearchView(View):
    def get(self, request, exchange, query):
        ex = (exchange or "").strip().upper()
        q = (query or "").strip()
        search_results = yahoo_search(q)
        ac_results = yahoo_autocomplete(q)

        candidates = []
        # From search v1
        for itm in search_results:
            sym = (itm.get("symbol") or "").upper()
            name = itm.get("shortname") or itm.get("longname") or sym
            qtype = (itm.get("quoteType") or "").upper()
            if qtype not in {"EQUITY", "ETF"}:
                continue
            candidates.append((sym, name))
        # From autocomplete v6
        for itm in ac_results:
            sym = (itm.get("symbol") or "").upper()
            name = itm.get("name") or sym
            qtype = (itm.get("typeDisp") or "").upper()
            if qtype and qtype not in {"EQUITY", "ETF", "FUND", "INDEX"}:
                continue
            candidates.append((sym, name))

        # Filter by requested exchange
        def ex_ok(sym: str) -> bool:
            if ex == "NSE":
                return sym.endswith(".NS") or sym.endswith("-NS")
            if ex == "BSE":
                return sym.endswith(".BO") or sym.endswith("-BO")
            return True

        seen = set()
        results = []
        for sym, name in candidates:
            if not ex_ok(sym):
                continue
            base = _normalize_base_ticker(sym)
            key = (base, name)
            if key in seen:
                continue
            seen.add(key)
            results.append({"symbol": base, "name": name})

        return JsonResponse({"exchange": ex, "query": q, "stocks": results[:10]})

class StockHistoryView(View):
    def get(self, request, ticker):
        p = (request.GET.get("period") or "60d").lower()
        label_to_days = {"1d": 1, "7d": 7, "1m": 30, "6m": 180, "1y": 365}
        days = label_to_days.get(p, 60)
        return JsonResponse({
            "ticker": ticker,
            "history": get_price_history(ticker, days=days)
        })


# Mutual fund history for toggles (period-based)
class MutualFundHistoryView(View):
    def get(self, request, scheme_id):
        p = (request.GET.get("period") or "60d").lower()
        label_to_days = {"1d": 1, "7d": 7, "1m": 30, "6m": 180, "1y": 365}
        days = label_to_days.get(p, 60)
        hist_tuple = mfapi_history(scheme_id, max_days=400)
        series = []
        if hist_tuple is not None:
            _, hist = hist_tuple
            series = [v for _, v in hist][:days]
            series = list(reversed(series))
        return JsonResponse({"scheme_id": scheme_id, "history": series})


# Simple dev live-reload version endpoint
SERVER_STARTED_AT = int(datetime.now().timestamp())

class DevVersionView(View):
    def get(self, request):
        return JsonResponse({"version": SERVER_STARTED_AT})

class StockAnalysisView(View):
    def get(self, request, ticker, buy_price, num_shares):
        try:
            buy = float(buy_price)
            shares = int(num_shares)
        except Exception:
            buy = 0.0
            shares = 0

        current = get_live_price(ticker) or get_latest_close_from_history(ticker) or 0.0
        pnl_per_share = current - buy if buy > 0 else 0.0
        pnl_total = round(pnl_per_share * shares, 2)

        if buy <= 0:
            advice = "Enter a valid buy price to get personalized advice."
            reasoning = "The system needs your average buy price to compare with current market price."
            strategy_desc = "Provide your average buy price so I can gauge gains/losses accurately."
        else:
            gain_pct = ((current - buy) / buy) * 100
            if gain_pct > 20:
                advice = "Consider taking partial profits."
                reasoning = f"Price is up {gain_pct:.1f}% over your cost; booking some profits reduces risk."
                strategy_desc = "Partial profit booking means selling a portion to lock gains while staying invested."
            elif gain_pct > 10:
                advice = "Hold with caution; monitor closely."
                reasoning = f"Price is up {gain_pct:.1f}% over your cost; good gains but watch for reversal signals."
                strategy_desc = "Hold but keep a stop-loss or alert in case momentum weakens."
            elif gain_pct < -15:
                advice = "Review investment thesis; consider stop-loss."
                reasoning = f"Price is down {gain_pct:.1f}% from your cost; significant loss requires careful review."
                strategy_desc = "Re-check fundamentals; a stop-loss helps limit further downside."
            elif gain_pct < -5:
                advice = "Hold but monitor closely; consider averaging down if conviction is high."
                reasoning = f"Price is down {gain_pct:.1f}% from your cost; moderate decline, evaluate fundamentals."
                strategy_desc = "Averaging down reduces average cost, but only if your long-term thesis is intact."
            else:
                advice = "Hold; price movement is within normal range."
                reasoning = f"Price is within ±10% of cost ({gain_pct:+.1f}%); no strong signal either way."
                strategy_desc = "Do nothing major; revisit only if price moves beyond your comfort band."

        return JsonResponse({
            "ticker": ticker.upper(),
            "your_buy_price": buy,
            "num_shares": shares,
            "current_market_price": current,
            "pnl_total": pnl_total,
            "personalized_advice": advice,
            "reasoning": reasoning,
            "strategy_description": strategy_desc,
            "fundamentals": get_stock_fundamentals(ticker),
            "fundamentals_notes": evaluate_fundamentals(get_stock_fundamentals(ticker)).get("notes", [])
        })


# =====================
# Mutual Fund API Views
# =====================

@csrf_exempt
def search_mutual_funds(request, query):
    """Search Yahoo Finance for mutual funds matching the query."""
    q = (query or "").strip()
    print(f"Searching mutual funds for: '{q}'")
    
    # Try MFAPI first for Indian mutual funds (more reliable for Indian funds)
    mf_results = []
    try:
        mf_results = mfapi_search(q)
        print(f"MFAPI found {len(mf_results)} results")
    except Exception as e:
        print(f"MFAPI search failed: {e}")
    
    # Also try Yahoo Finance for international funds
    search_results = yahoo_search(q)
    ac_results = yahoo_autocomplete(q)
    yahoo_results = []
    seen = set()
    
    # Prefer explicit mutual funds, but include ETFs so users can pick them
    for itm in search_results:
        qtype = (itm.get("quoteType") or "").upper()
        if qtype not in {"MUTUALFUND", "ETF"}:
            continue
        sym = (itm.get("symbol") or "").upper()
        name = itm.get("shortname") or itm.get("longname") or sym
        key = (sym, name)
        if key in seen:
            continue
        seen.add(key)
        yahoo_results.append({"symbol": sym, "name": name})
    
    for itm in ac_results:
        qtype = (itm.get("typeDisp") or "").upper()
        if qtype not in {"MUTUAL FUND", "ETF", "FUND"}:
            continue
        sym = (itm.get("symbol") or "").upper()
        name = itm.get("name") or sym
        key = (sym, name)
        if key in seen:
            continue
        seen.add(key)
        yahoo_results.append({"symbol": sym, "name": name})
    
    print(f"Yahoo found {len(yahoo_results)} results")
    
    # Combine results: MFAPI first (Indian funds), then Yahoo (international)
    all_results = mf_results + yahoo_results
    
    # Remove duplicates based on name similarity
    unique_results = []
    seen_names = set()
    for result in all_results:
        name_lower = result["name"].lower()
        if name_lower not in seen_names:
            seen_names.add(name_lower)
            unique_results.append(result)
    
    print(f"Returning {len(unique_results)} unique results")
    return JsonResponse({"query": q, "stocks": unique_results[:10]})

@csrf_exempt
def analyze_mutual_fund(request, scheme_id, buy_nav, units):
    """Analyze mutual fund using avg buy NAV and units.

    Logic:
    - Resolve current NAV using Yahoo; if unavailable, use MFAPI.
    - Pull MFAPI history to compute recent trend (1Y CAGR), volatility, and
      a simple momentum signal.
    - Compare user's average NAV vs current to produce advice.
    """
    try:
        buy = float(buy_nav)
        units_float = float(units)
    except Exception:
        buy = 0.0
        units_float = 0.0

    # For mutual funds, prioritize MFAPI over Yahoo Finance
    current_nav = None
    fund_name = scheme_id
    
    # Try MFAPI first for mutual funds (more reliable)
    mf = mfapi_latest_nav(scheme_id)
    if mf is not None:
        fund_name, current_nav = mf
    
    # Only try Yahoo Finance if MFAPI failed
    if current_nav is None and yf is not None:
        try:
            # Try with common Indian suffixes as well
            for sym in _resolve_yf_symbols(scheme_id):
                try:
                    tk = yf.Ticker(sym)
                    info = getattr(tk, "info", {}) or {}
                    fund_name = info.get("longName") or info.get("shortName") or sym
                    current_nav = info.get("currentPrice") or info.get("regularMarketPrice")
                    if current_nav is None:
                        df = yf.download(sym, period="10d", interval="1d", progress=False, auto_adjust=False)
                        if df is not None and not df.empty:
                            current_nav = float(df["Close"].iloc[-1])
                    if current_nav is not None:
                        break
                except Exception:
                    continue
        except Exception:
            pass
    if current_nav is None:
        return JsonResponse({
            "scheme_id": scheme_id,
            "scheme_name": fund_name,
            "your_buy_nav": buy,
            "num_units": units_float,
            "current_nav": "N/A",
            "personalized_advice": "Unable to fetch current NAV from market data. Please check the fund name or try a different fund.",
            "reasoning": f"The fund '{scheme_id}' could not be resolved or has no recent price data available. Try searching with the exact fund name or scheme code.",
            "error": "FUND_NOT_FOUND"
        })

    # Calculate P&L based on average NAV and units
    pnl_per_unit = (current_nav - buy) if buy > 0 else 0.0
    pnl_total = round(pnl_per_unit * units_float, 2)

    # Pull history and compute simple indicators
    hist_tuple = mfapi_history(scheme_id, max_days=500)
    one_year_cagr = None
    volatility_pct = None
    momentum = None
    if hist_tuple is not None:
        _, hist = hist_tuple
        closes = [v for _, v in hist]
        if len(closes) >= 250:
            try:
                nav_1y_ago = closes[249]
                if nav_1y_ago and current_nav:
                    one_year_cagr = ((current_nav / nav_1y_ago) - 1) * 100
            except Exception:
                pass
        if len(closes) >= 60:
            # daily pct std over last ~3 months
            try:
                import statistics
                rets = []
                for i in range(1, min(90, len(closes))):
                    if closes[i-1] > 0:
                        rets.append((closes[i] / closes[i-1]) - 1)
                if rets:
                    volatility_pct = statistics.pstdev(rets) * 100
            except Exception:
                pass
        if len(closes) >= 30:
            sma_20 = sum(closes[:20]) / 20.0
            sma_50 = sum(closes[:50]) / 50.0 if len(closes) >= 50 else None
            if sma_50 is not None:
                momentum = "bullish" if sma_20 > sma_50 else "bearish"

    # Generate advice combining user P&L and trend
    if buy <= 0:
        advice = "Enter a valid average buy NAV for personalized advice."
        reasoning = "Average NAV helps evaluate your actual position against current NAV."
        strategy_desc = "Provide your average NAV so I can compare with today’s NAV and compute P&L."
    else:
        gain_pct = ((current_nav - buy) / buy) * 100
        if momentum == "bullish" and gain_pct > 10:
            advice = "Trail profits; consider continuing SIP if goals remain."
            reasoning = f"Up {gain_pct:.1f}% from cost with positive momentum; trailing helps protect gains."
            strategy_desc = "Trailing profits means raising your stop level as price rises to protect gains."
        elif momentum == "bearish" and gain_pct < -10:
            advice = "Pause new lump-sum; review fund and consider staggered averaging."
            reasoning = f"Down {gain_pct:.1f}% and momentum weak; avoid adding aggressively until trend stabilizes."
            strategy_desc = "Staggered averaging (SIP) spreads risk instead of adding a big lump-sum in a downtrend."
        elif gain_pct > 20:
            advice = "Partial profit booking can de-risk while staying invested."
            reasoning = f"Healthy gains of {gain_pct:.1f}% over cost."
            strategy_desc = "Sell a small portion to lock gains, continue holding the rest for long-term goals."
        elif gain_pct < -15:
            advice = "Revisit thesis; switch if long-term underperformance persists."
            reasoning = f"Loss of {gain_pct:.1f}% from cost; ensure fund still fits objectives."
            strategy_desc = "If a fund lags peers/benchmark for long, consider switching to a stronger category peer."
        else:
            advice = "Hold and continue SIP aligned to goals."
            reasoning = f"Return {gain_pct:+.1f}%; no strong signal."
            strategy_desc = "Stay the course; SIP builds position steadily and reduces timing risk."

    return JsonResponse({
        "scheme_id": scheme_id,
        "scheme_name": fund_name,
        "your_buy_nav": buy,
        "num_units": units_float,
        "current_nav": current_nav,
        "pnl_total": pnl_total,
        "one_year_cagr_pct": None if one_year_cagr is None else round(one_year_cagr, 2),
        "volatility_pct": None if volatility_pct is None else round(volatility_pct, 2),
        "momentum": momentum,
        "personalized_advice": advice,
        "reasoning": reasoning,
        "strategy_description": strategy_desc
    })


# =====================
# Market snapshot
# =====================

class MarketSnapshotView(View):
    def get(self, request):
        # Prefer Yahoo quote API for multiple symbols in one call
        symbols = {
            "NIFTY": "NSEI.NS",  # NSE NIFTY 50
            "SENSEX": "BSESN.BO",  # BSE SENSEX
            "BANKNIFTY": "NSEBANK.NS",  # NSE BANK NIFTY
            "MIDCPNIFTY": "NSEMDCP50.NS",  # NSE MIDCAP 50
            "FINNIFTY": "NSEFIN.NS"  # NSE FINANCIAL SERVICES
        }
        # Try multiple data sources for real market data
        data = []
        
        # Method 1: Try Yahoo Finance API with better headers
        try:
            url = "https://query1.finance.yahoo.com/v7/finance/quote"
            params = {"symbols": ",".join([v for v in symbols.values()])}
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
                data = (r.json() or {}).get("quoteResponse", {}).get("result", []) or []
                print(f"Yahoo API success: {len(data)} symbols")
            else:
                print(f"Yahoo API returned status {r.status_code}")
        except Exception as e:
            print(f"Yahoo API error: {e}")
        
        # Method 2: Try alternative Yahoo Finance endpoint if first fails
        if not data:
            try:
                url = "https://query2.finance.yahoo.com/v8/finance/chart"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                    "Referer": "https://finance.yahoo.com/"
                }
                for symbol in symbols.values():
                    try:
                        params = {"symbol": symbol, "range": "1d", "interval": "1m"}
                        r = requests.get(url, params=params, headers=headers, timeout=8)
                        if r.status_code == 200:
                            chart_data = r.json()
                            if chart_data and 'chart' in chart_data and 'result' in chart_data['chart']:
                                result = chart_data['chart']['result'][0]
                                meta = result.get('meta', {})
                                if meta:
                                    data.append({
                                        'symbol': symbol,
                                        'regularMarketPrice': meta.get('regularMarketPrice'),
                                        'regularMarketChange': meta.get('regularMarketChange'),
                                        'regularMarketChangePercent': meta.get('regularMarketChangePercent')
                                    })
                    except Exception as e:
                        print(f"Chart API error for {symbol}: {e}")
                        continue
                print(f"Chart API success: {len(data)} symbols")
            except Exception as e:
                print(f"Chart API error: {e}")
        
        # Method 3: Try yfinance info as fallback
        if not data and yf is not None:
            try:
                for symbol in symbols.values():
                    try:
                        ticker = yf.Ticker(symbol)
                        info = ticker.info
                        if info and 'regularMarketPrice' in info:
                            data.append({
                                'symbol': symbol,
                                'regularMarketPrice': info.get('regularMarketPrice'),
                                'regularMarketChange': info.get('regularMarketChange'),
                                'regularMarketChangePercent': info.get('regularMarketChangePercent')
                            })
                    except Exception as e:
                        print(f"yfinance info error for {symbol}: {e}")
                        continue
                print(f"yfinance info success: {len(data)} symbols")
            except Exception as e:
                print(f"yfinance info error: {e}")
        
        # Method 4: Try alternative symbols if primary ones fail
        if not data:
            alternative_symbols = {
                "NIFTY": "NIFTY_50.NS",
                "SENSEX": "SENSEX.BO", 
                "BANKNIFTY": "BANKNIFTY.NS",
                "MIDCPNIFTY": "MIDCAP_50.NS",
                "FINNIFTY": "FINANCIAL_SERVICES.NS"
            }
            try:
                for label, symbol in alternative_symbols.items():
                    try:
                        ticker = yf.Ticker(symbol)
                        hist = ticker.history(period="2d")
                        if not hist.empty:
                            latest_close = hist['Close'].iloc[-1]
                            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else latest_close
                            change = latest_close - prev_close
                            change_pct = (change / prev_close) * 100 if prev_close != 0 else 0
                            
                            data.append({
                                'symbol': symbol,
                                'regularMarketPrice': latest_close,
                                'regularMarketChange': change,
                                'regularMarketChangePercent': change_pct
                            })
                    except Exception as e:
                        print(f"Alternative symbol error for {symbol}: {e}")
                        continue
                print(f"Alternative symbols success: {len(data)} symbols")
            except Exception as e:
                print(f"Alternative symbols error: {e}")
        
        # Method 5: Try to get historical data for closed markets
        if not data and yf is not None:
            try:
                for symbol in symbols.values():
                    try:
                        ticker = yf.Ticker(symbol)
                        # Get recent data (last 5 days)
                        hist = ticker.history(period="5d")
                        if not hist.empty:
                            latest_close = hist['Close'].iloc[-1]
                            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else latest_close
                            change = latest_close - prev_close
                            change_pct = (change / prev_close) * 100 if prev_close != 0 else 0
                            
                            data.append({
                                'symbol': symbol,
                                'regularMarketPrice': latest_close,
                                'regularMarketChange': change,
                                'regularMarketChangePercent': change_pct
                            })
                    except Exception as e:
                        print(f"Historical data error for {symbol}: {e}")
                        continue
                print(f"Historical data success: {len(data)} symbols")
            except Exception as e:
                print(f"Historical data error: {e}")
        
        # Method 6: Try direct web scraping as last resort
        if not data:
            try:
                import requests
                from bs4 import BeautifulSoup
                
                # Try to get data from a reliable financial website
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                # Try NSE official website
                try:
                    url = "https://www.nseindia.com/api/allIndices"
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        nse_data = response.json()
                        for item in nse_data.get('data', []):
                            if item.get('index') in ['NIFTY 50', 'NIFTY BANK', 'NIFTY MIDCAP 50']:
                                symbol_map = {
                                    'NIFTY 50': 'NIFTY',
                                    'NIFTY BANK': 'BANKNIFTY', 
                                    'NIFTY MIDCAP 50': 'MIDCPNIFTY'
                                }
                                label = symbol_map.get(item.get('index'))
                                if label:
                                    data.append({
                                        'symbol': item.get('index'),
                                        'regularMarketPrice': item.get('last'),
                                        'regularMarketChange': item.get('variation'),
                                        'regularMarketChangePercent': item.get('percentChange')
                                    })
                        print(f"NSE API success: {len(data)} symbols")
                except Exception as e:
                    print(f"NSE API error: {e}")
                    
            except ImportError:
                print("BeautifulSoup not available for web scraping")
            except Exception as e:
                print(f"Web scraping error: {e}")

        resp = []
        by_symbol = {itm.get("symbol"): itm for itm in data}

        # Helper to compute values using yfinance when Yahoo batch lacks data
        def fallback_with_yf(symbol: str):
            try:
                if yf is None:
                    return None
                tk = yf.Ticker(symbol)
                finfo = getattr(tk, "fast_info", object())
                last_price = getattr(finfo, "last_price", None)
                prev_close = getattr(finfo, "previous_close", None)
                if last_price is None or prev_close is None:
                    # Try info dict
                    info = getattr(tk, "info", {}) or {}
                    last_price = last_price or info.get("regularMarketPrice") or info.get("currentPrice")
                    prev_close = prev_close or info.get("regularMarketPreviousClose")
                if last_price is None and prev_close is not None:
                    last_price = prev_close
                if last_price is None:
                    # final fallback: small history
                    df = yf.download(symbol, period="5d", interval="1d", progress=False, auto_adjust=False)
                    if df is not None and not df.empty:
                        last_price = float(df["Close"].iloc[-1])
                        if len(df) >= 2:
                            prev_close = float(df["Close"].iloc[-2])
                if last_price is None:
                    return None
                change = None
                change_pct = None
                if prev_close and isinstance(prev_close, (int, float)) and prev_close > 0:
                    change = float(last_price) - float(prev_close)
                    change_pct = (change / float(prev_close)) * 100
                return {
                    "value": round(float(last_price), 2),
                    "change": 0.0 if change is None else round(change, 2),
                    "change_pct": 0.0 if change_pct is None else round(change_pct, 2),
                }
            except Exception:
                return None

        for label, sym in symbols.items():
            itm = by_symbol.get(sym) or {}
            last = itm.get("regularMarketPrice") or itm.get("regularMarketPreviousClose")
            chg = itm.get("regularMarketChange")
            chgpct = itm.get("regularMarketChangePercent")
            if last is None:
                fb = fallback_with_yf(sym)
                if fb is not None:
                    resp.append({"name": label, **fb})
                    continue
                # If no data available, show error state
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
            
            # Explicit mutual fund keywords
            mf_keywords = ["mutual fund", "mf", "fund", "scheme", "nav", "units", "sip"]
            if any(keyword in text_lower for keyword in mf_keywords):
                # Extract entity (remove keywords to get the fund name)
                entity = text_lower
                for kw in mf_keywords:
                    entity = entity.replace(kw, "").strip()
                return JsonResponse({"intent": "analyze_mutual_fund", "entity": entity or text})
            
            # Explicit stock keywords
            stock_keywords = ["stock", "share", "equity", "ticker", "symbol", "price", "shares"]
            if any(keyword in text_lower for keyword in stock_keywords):
                entity = text_lower
                for kw in stock_keywords:
                    entity = entity.replace(kw, "").strip()
                return JsonResponse({"intent": "analyze_stock", "entity": entity or text})
            
            # Portfolio-related
            if "portfolio" in text_lower or "holdings" in text_lower:
                return JsonResponse({"intent": "show_portfolio"})
            
            # Greetings and casual conversation
            greeting_words = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "how are you", "how's it going", "what's up", "how do you do"]
            if any(word in text_lower for word in greeting_words):
                return JsonResponse({"intent": "greeting"})
            
            # How are you specifically
            if "how are you" in text_lower or "how are things" in text_lower:
                return JsonResponse({"intent": "how_are_you"})
            
            # Help requests
            if any(word in text_lower for word in ["help", "what can you do", "what do you do", "capabilities"]):
                return JsonResponse({"intent": "help"})
            
            # Thanks and appreciation
            if any(word in text_lower for word in ["thank", "thanks", "appreciate", "great", "awesome", "good job"]):
                return JsonResponse({"intent": "thanks"})
            
            # Default: try to determine if it's likely a mutual fund or stock based on common patterns
            # Mutual funds often have words like "growth", "equity", "top", "bluechip"
            mf_patterns = ["growth", "equity", "top", "bluechip", "large cap", "mid cap", "small cap", "index", "liquid"]
            if any(pattern in text_lower for pattern in mf_patterns):
                return JsonResponse({"intent": "analyze_mutual_fund", "entity": text})
            
            # Default to stock analysis for short queries (likely company names)
            word_count = len([w for w in text_lower.split() if w])
            if word_count <= 4 and word_count > 0:
                return JsonResponse({"intent": "analyze_stock", "entity": text})
            
            return JsonResponse({"intent": None, "entity": None})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
