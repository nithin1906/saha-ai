import pandas as pd
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from .data_service import get_stock_news, get_macro_data
import joblib

try:
    model = joblib.load('saha_ai_model.joblib')
    print("AI model loaded successfully.")
except FileNotFoundError:
    print("Model file not found. Please run 'python manage.py train_model' first.")
    model = None

def get_sentiment_score(ticker):
    # ... (this function is unchanged)
    news = get_stock_news(ticker)
    if not news:
        return 0
    analyzer = SentimentIntensityAnalyzer()
    total_score = 0
    for article in news:
        score = analyzer.polarity_scores(article['title'])['compound']
        total_score += score
    return total_score / len(news) if news else 0

def train_and_predict(data, ticker):
    if model is None:
        return "Model Not Trained"

    sentiment_score = get_sentiment_score(ticker)
    macro_data = get_macro_data() # Fetch live macro data
    data['sentiment'] = sentiment_score
    data['repo_rate'] = macro_data.get('repo_rate', 6.50)
    
    features = [
        'Volume', 'SMA_20', 'SMA_50', 'SMA_200', 'RSI_14',
        'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9',
        'BBL_5_2.0', 'BBM_5_2.0', 'BBU_5_2.0', 'BBB_5_2.0', 'BBP_5_2.0',
        'trailingPE', 'forwardPE', 'pegRatio', 'priceToBook', 'sentiment',
        'repo_rate' # Add new feature
    ]
    
    latest_data = data[features].iloc[-1].values.reshape(1, -1)
    
    prediction_code = model.predict(latest_data)[0]
    
    signal_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
    return signal_map.get(prediction_code, "Error")
