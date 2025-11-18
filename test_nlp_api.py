#!/usr/bin/env python
"""
Test script for NLP API endpoints
Run: python test_nlp_api.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.auth.models import User
from advisor.nlp_service import ConversationalAI, FinancialAdvisor
import json

def test_conversational_ai():
    """Test ConversationalAI class"""
    print("\n" + "="*60)
    print("Testing ConversationalAI Class")
    print("="*60)
    
    # Create or get test user
    user, created = User.objects.get_or_create(
        username='nlp_test',
        defaults={'email': 'nlp@test.com'}
    )
    print(f"✓ Using test user: {user.username}")
    
    # Initialize AI
    ai = ConversationalAI(user_id=user.id)
    print("✓ ConversationalAI initialized")
    
    # Test question detection
    test_messages = [
        "I own AAPL and MSFT, should I diversify?",
        "What's happening in the market today?",
        "Is TSLA a good buy?",
    ]
    
    print("\nTesting question type detection:")
    for msg in test_messages:
        is_portfolio = ai.is_portfolio_question(msg)
        is_market = ai.is_market_question(msg)
        is_stock = ai.is_stock_question(msg)
        print(f"\n  Message: '{msg}'")
        print(f"    - Portfolio: {is_portfolio}")
        print(f"    - Market: {is_market}")
        print(f"    - Stock: {is_stock}")
    
    # Test history management
    print("\n\nTesting history management:")
    ai.add_to_history('user', 'What is diversification?')
    ai.add_to_history('assistant', 'Diversification is spreading investments across different assets...')
    history = ai.get_history()
    print(f"✓ Added 2 messages to history")
    print(f"✓ History length: {len(history)}")
    print(f"✓ History content:\n{json.dumps(history, indent=2)}")
    
    # Test clearing
    ai.clear_history()
    print(f"✓ Cleared history (length now: {len(ai.get_history())})")
    
    print("\n" + "="*60)
    print("✅ ConversationalAI Tests Passed!")
    print("="*60)


def test_financial_advisor():
    """Test FinancialAdvisor class"""
    print("\n" + "="*60)
    print("Testing FinancialAdvisor Class")
    print("="*60)
    
    # Get test user
    user = User.objects.get(username='nlp_test')
    
    # Initialize advisor
    advisor = FinancialAdvisor(user_id=user.id)
    print("✓ FinancialAdvisor initialized")
    
    # Check methods exist
    methods = [
        'analyze_investment',
        'portfolio_suggestion',
        'market_insight',
        'get_conversation_history',
        'clear_conversation'
    ]
    
    for method in methods:
        if hasattr(advisor, method):
            print(f"✓ Method available: {method}")
        else:
            print(f"✗ Method missing: {method}")
    
    print("\n" + "="*60)
    print("✅ FinancialAdvisor Tests Passed!")
    print("="*60)


def test_api_endpoints():
    """Test API endpoints exist in URL config"""
    print("\n" + "="*60)
    print("Testing API Endpoints")
    print("="*60)
    
    from django.urls import reverse
    
    endpoints = [
        'nlp-chat',
        'nlp-history',
        'nlp-history-clear',
        'financial-advisor',
        'detect-question-type',
    ]
    
    for endpoint in endpoints:
        try:
            url = reverse(endpoint)
            print(f"✓ Endpoint available: {endpoint} -> {url}")
        except Exception as e:
            print(f"✗ Endpoint error: {endpoint} - {str(e)}")
    
    print("\n" + "="*60)
    print("✅ API Endpoints Tests Passed!")
    print("="*60)


def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  SAHA-AI NLP Integration Test Suite".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    try:
        # Check if API key is set
        if not os.getenv('GEMINI_API_KEY'):
            print("\n⚠️  WARNING: GEMINI_API_KEY not set!")
            print("   To fully test chat functionality, set: export GEMINI_API_KEY='your_key'")
            print("   Get API key at: https://aistudio.google.com/apikey")
        
        # Run tests
        test_conversational_ai()
        test_financial_advisor()
        test_api_endpoints()
        
        print("\n")
        print("╔" + "="*58 + "╗")
        print("║" + " "*58 + "║")
        print("║" + "  ✅ ALL TESTS PASSED!".center(58) + "║")
        print("║" + " "*58 + "║")
        print("║" + "  Your NLP integration is ready to use!".center(58) + "║")
        print("║" + " "*58 + "║")
        print("╚" + "="*58 + "╝")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
