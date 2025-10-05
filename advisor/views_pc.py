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
# Basic View Functions - PC Version Only
# =====================

def index(request):
    """Main index view - PC version only"""
    if not request.user.is_authenticated:
        return render(request, 'users/login.html')
    return render(request, 'advisor/index.html', {
        'user_first_name': request.user.first_name if request.user.is_authenticated else '',
        'csrf_token_value': request.META.get('CSRF_COOKIE', '')
    })

def portfolio(request):
    """Portfolio view - PC version only"""
    if not request.user.is_authenticated:
        return render(request, 'users/login.html')
    return render(request, 'advisor/portfolio.html')

def about(request):
    """About page view"""
    return render(request, 'advisor/about.html')

def profile(request):
    """User profile view - PC version only"""
    if not request.user.is_authenticated:
        return render(request, 'users/login.html')
    return render(request, 'advisor/profile.html')

# =====================
# API Views
# =====================

@csrf_exempt
def chat_api(request):
    """Main chat API - PC version"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message', '').strip()
            
            if not message:
                return JsonResponse({"error": "Message is required"}, status=400)
            
            # Update fallback prices daily
            try:
                from advisor.data_service import stock_data_service
                stock_data_service.update_fallback_prices_daily()
            except Exception as e:
                logger.warning(f"Failed to update fallback prices: {e}")
            
            # Process message and return response
            response = process_chat_message(message)
            
            return JsonResponse({
                "response": response,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Chat API error: {e}")
            return JsonResponse({"error": "Internal server error"}, status=500)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)

def process_chat_message(message):
    """Process chat message and return response"""
    message_lower = message.lower()
    
    # Stock analysis
    if any(word in message_lower for word in ['analyze', 'stock', 'analysis']):
        return "I can help you analyze stocks. Please provide the stock name and your position details."
    
    # Portfolio help
    elif any(word in message_lower for word in ['portfolio', 'holdings']):
        return "I can help you manage your portfolio. You can add stocks, view holdings, and get analysis."
    
    # General help
    elif any(word in message_lower for word in ['help', 'what can you do']):
        return """I'm SAHA-AI, your stock market assistant. I can help you with:
        
• Stock analysis and recommendations
• Portfolio management
• Market insights
• Investment guidance

What would you like to know?"""
    
    # Default response
    else:
        return "I'm here to help with your stock market questions. What would you like to know?"

# =====================
# Portfolio API
# =====================

@csrf_exempt
def portfolio_api(request):
    """Portfolio API - PC version"""
    if request.method == 'GET':
        try:
            holdings = Holding.objects.filter(user=request.user)
            portfolio_data = []
            
            for holding in holdings:
                portfolio_data.append({
                    'ticker': holding.ticker,
                    'shares': holding.shares,
                    'avg_price': float(holding.avg_price),
                    'current_price': get_current_price(holding.ticker),
                    'total_value': float(holding.shares * holding.avg_price)
                })
            
            return JsonResponse({
                'holdings': portfolio_data,
                'total_value': sum(item['total_value'] for item in portfolio_data)
            })
            
        except Exception as e:
            logger.error(f"Portfolio API error: {e}")
            return JsonResponse({"error": "Internal server error"}, status=500)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)

def get_current_price(ticker):
    """Get current stock price"""
    try:
        from advisor.data_service import StockDataService
        data_service = StockDataService()
        return data_service.get_stock_price(ticker)
    except:
        return 0.0

# =====================
# Utility Functions
# =====================

def is_admin(user):
    """Check if user is admin"""
    return user.is_superuser or user.is_staff
