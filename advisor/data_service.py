# advisor/data_service.py
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from gnews import GNews # New import

def get_stock_data(ticker, period="1y"):
    # ... (this function remains exactly the same)
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period=period)
        
        if data.empty:
            print(f"No data found for ticker {ticker}.")
            return None

        info = stock.info
        fundamentals = {
            'trailingPE': info.get('trailingPE', 0),
            'forwardPE': info.get('forwardPE', 0),
            'pegRatio': info.get('pegRatio', 0),
            'priceToBook': info.get('priceToBook', 0)
        }
        for key, value in fundamentals.items():
            data[key] = value if value is not None else 0

        MyStrategy = ta.Strategy(
            name="SAHA_AI_Core_Strategy",
            ta=[
                {"kind": "sma", "length": 20},
                {"kind": "sma", "length": 50},
                {"kind": "sma", "length": 200},
                {"kind": "rsi"},
                {"kind": "macd"},
                {"kind": "bbands", "length": 5, "std": 2.0},
            ]
        )
        
        data.ta.strategy(MyStrategy)
        return data
    except Exception as e:
        print(f"An error occurred in data_service: {e}")
        return None

# This is the new, more reliable news function
def get_stock_news(ticker):
    try:
        google_news = GNews(language='en', country='IN', period='7d')
        # We search for the company name, removing the .NS or .BO
        company_name = ticker.split('.')[0]
        news = google_news.get_news(company_name)
        return news[:5] if news else []
    except Exception as e:
        print(f"An error occurred while fetching news for {ticker}: {e}")
        return []
    
def get_macro_data():
    """
    Fetches key Indian macroeconomic data.
    For this version, we are fetching the RBI Repo Rate.
    """
    try:
        # This is a simplified example; in production, a dedicated API would be better.
        url = "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=57472" # Example URL, might need updating
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        # A very basic scrape to find the rate. This is fragile.
        if "6.50 per cent" in response.text:
            return {"repo_rate": 6.50}
        return {"repo_rate": 6.50} # Return a default value if scrape fails
    except Exception:
        return {"repo_rate": 6.50} # Return a default on error
