import requests
import re
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.middleware.csrf import get_token
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import Portfolio, Holding
from .serializers import PortfolioSerializer, HoldingSerializer
from .data_service import get_stock_data, get_stock_news
from .ml_service import train_and_predict
from .personalization_service import personalize_signal
from .portfolio_analyzer import get_portfolio_health

@login_required
def chat_view(request):
    context = {
        'user_first_name': request.user.first_name or request.user.username,
        'csrf_token_value': get_token(request)
    }
    return render(request, 'advisor/index.html', context)

@login_required
def profile_view(request):
    return render(request, 'advisor/profile.html', {'user': request.user})

@login_required
def about_view(request):
    return render(request, 'advisor/about.html')

class ParseIntentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = request.data.get('text', '').lower()
        
        # Simple keyword-based intent recognition
        analysis_keywords = ['analyze', 'analysis', 'check', 'look at', 'what about']
        portfolio_keywords = ['portfolio', 'holdings', 'my stocks']

        if any(keyword in text for keyword in portfolio_keywords):
            return Response({'intent': 'view_portfolio'})

        # For analysis, find the keyword and extract the entity
        for keyword in analysis_keywords:
            if keyword in text:
                # Remove the keyword and surrounding noise to get the entity
                entity = text.replace(keyword, '').strip()
                entity = re.sub(r'^(for|on|me)\s+', '', entity) # remove prepositions
                if entity:
                    return Response({'intent': 'analyze_stock', 'entity': entity})

        return Response({'intent': 'unknown'}, status=status.HTTP_400_BAD_REQUEST)


class PortfolioHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        portfolio, created = Portfolio.objects.get_or_create(user=request.user)
        health_data = get_portfolio_health(portfolio)
        return Response(health_data)

class PortfolioView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        portfolio, created = Portfolio.objects.get_or_create(user=request.user)
        serializer = PortfolioSerializer(portfolio)
        return Response(serializer.data)

    def post(self, request):
        portfolio, created = Portfolio.objects.get_or_create(user=request.user)
        ticker = request.data.get('ticker')
        existing_holding = Holding.objects.filter(portfolio=portfolio, ticker=ticker).first()
        if existing_holding:
            existing_holding.quantity = request.data.get('quantity')
            existing_holding.average_buy_price = request.data.get('average_buy_price')
            existing_holding.save()
            serializer = HoldingSerializer(existing_holding)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            serializer = HoldingSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(portfolio=portfolio)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class HoldingDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, holding_id):
        try:
            holding = Holding.objects.get(id=holding_id, portfolio__user=request.user)
            holding.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Holding.DoesNotExist:
            return Response({"error": "Holding not found."}, status=status.HTTP_404_NOT_FOUND)

class StockSearchView(APIView):
    def get(self, request, exchange, query):
        search_url = f"https://query1.finance.yahoo.com/v1/finance/search?q={query}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            exchange_map = {"NSE": "NSI", "BSE": "BSE"}
            target_exchange_code = exchange_map.get(exchange.upper())
            filtered_stocks = [
                {"symbol": s.get('symbol'), "name": s.get('longname', s.get('shortname', 'N/A'))}
                for s in data.get('quotes', [])
                if s.get('quoteType') == 'EQUITY' and s.get('exchange') == target_exchange_code
            ]
            return Response({"stocks": filtered_stocks}, status=status.HTTP_200_OK)
        except requests.exceptions.RequestException:
            return Response({"error": "Failed to connect to search service."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class StockNewsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, ticker):
        news_list = get_stock_news(ticker)
        formatted_news = [{"title": item.get('title'), "link": item.get('link')} for item in news_list if item.get('title') and item.get('link')]
        return Response({"news": formatted_news}, status=status.HTTP_200_OK)

class StockHistoryView(APIView):
    def get(self, request, ticker):
        try:
            data = get_stock_data(ticker, period="1y")
            if data is None:
                return Response({"error": "Could not fetch historical data."}, status=status.HTTP_404_NOT_FOUND)
            history = data.reset_index()
            history['Date'] = history['Date'].dt.strftime('%Y-%m-%d')
            history_json = history[['Date', 'Close']].to_dict('records')
            return Response({"history": history_json}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StockAnalysisView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, ticker, buy_price, num_shares):
        try:
            data = get_stock_data(ticker)
            if data is None:
                return Response({"error": f"I couldn't fetch live market data for {ticker}. It might be a temporary issue with the data provider. Please try again in a moment."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            ml_signal = train_and_predict(data, ticker)
            if "Error" in ml_signal or "Data" in ml_signal:
                return Response({"error": f"Could not generate an AI signal: {ml_signal}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            current_price = data['Close'].iloc[-1]
            final_signal, explanation = personalize_signal(ml_signal, float(buy_price), current_price, num_shares)
            response_data = {
                'ticker': ticker, 'your_buy_price': float(buy_price), 'num_shares': num_shares,
                'current_market_price': round(current_price, 2), 'generic_ml_signal': ml_signal,
                'personalized_advice': final_signal, 'reasoning': explanation
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "An unexpected error occurred during analysis.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

