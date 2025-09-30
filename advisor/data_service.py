# advisor/data_service.py
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from gnews import GNews # New import

def calculate_sma(data, window):
    """Calculate Simple Moving Average"""
    return data.rolling(window=window).mean()

def calculate_rsi(data, window=14):
    """Calculate Relative Strength Index"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(data, fast=12, slow=26, signal=9):
    """Calculate MACD"""
    ema_fast = data.ewm(span=fast).mean()
    ema_slow = data.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(data, window=20, std_dev=2):
    """Calculate Bollinger Bands"""
    sma = data.rolling(window=window).mean()
    std = data.rolling(window=window).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return upper_band, sma, lower_band

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

        # Calculate technical indicators manually
        close_prices = data['Close']
        
        # Simple Moving Averages
        data['SMA_20'] = calculate_sma(close_prices, 20)
        data['SMA_50'] = calculate_sma(close_prices, 50)
        data['SMA_200'] = calculate_sma(close_prices, 200)
        
        # RSI
        data['RSI_14'] = calculate_rsi(close_prices, 14)
        
        # MACD
        macd_line, signal_line, histogram = calculate_macd(close_prices)
        data['MACD'] = macd_line
        data['MACD_signal'] = signal_line
        data['MACD_histogram'] = histogram
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(close_prices, 20, 2)
        data['BB_upper'] = bb_upper
        data['BB_middle'] = bb_middle
        data['BB_lower'] = bb_lower
        
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
