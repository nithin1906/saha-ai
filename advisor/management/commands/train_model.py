import pandas as pd
from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from advisor.data_service import get_stock_data, get_macro_data
from advisor.ml_service import get_sentiment_score
import joblib
from django.core.management.base import BaseCommand
import time

class Command(BaseCommand):
    help = 'Trains a generalized AI model using NIFTY 50 and macroeconomic data.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting AI model training process..."))
        
        # ... (nifty50_tickers list remains the same)
        nifty50_tickers = [
            'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'INFY.NS', 
            'HINDUNILVR.NS', 'BHARTIARTL.NS', 'SBIN.NS', 'LICI.NS', 'ITC.NS',
            'HCLTECH.NS', 'KOTAKBANK.NS', 'LT.NS', 'BAJFINANCE.NS', 'AXISBANK.NS',
            'MARUTI.NS', 'ASIANPAINT.NS', 'SUNPHARMA.NS', 'TITAN.NS', 'WIPRO.NS',
            'ULTRACEMCO.NS', 'ADANIENT.NS', 'NESTLEIND.NS', 'ONGC.NS', 'NTPC.NS',
            'JSWSTEEL.NS', 'TATAMOTORS.NS', 'M&M.NS', 'ADANIPORTS.NS', 'BAJAJFINSV.NS',
            'POWERGRID.NS', 'COALINDIA.NS', 'SBILIFE.NS', 'GRASIM.NS', 'HDFCLIFE.NS',
            'BRITANNIA.NS', 'INDUSINDBK.NS', 'HINDALCO.NS', 'EICHERMOT.NS', 'CIPLA.NS',
            'DRREDDY.NS', 'DIVISLAB.NS', 'TECHM.NS', 'APOLLOHOSP.NS', 'TATASTEEL.NS',
            'HEROMOTOCO.NS', 'BAJAJ-AUTO.NS', 'TATACONSUM.NS', 'UPL.NS', 'BPCL.NS'
        ]
        
        self.stdout.write("Fetching macroeconomic data...")
        macro_data = get_macro_data()
        repo_rate = macro_data.get('repo_rate', 6.50)
        self.stdout.write(f"Current Repo Rate: {repo_rate}%")

        all_data = []
        for i, ticker in enumerate(nifty50_tickers):
            self.stdout.write(f"({i+1}/{len(nifty50_tickers)}) Fetching training data for {ticker}...")
            data = get_stock_data(ticker)
            if data is not None and not data.empty:
                sentiment_score = get_sentiment_score(ticker)
                data['sentiment'] = sentiment_score
                data['repo_rate'] = repo_rate # Add macro data as a feature
                all_data.append(data)
            else:
                self.stdout.write(self.style.WARNING(f"Could not fetch data for {ticker}. Skipping."))
            time.sleep(1)

        # ... (rest of the file is the same as before, but with the new 'repo_rate' feature)
        if not all_data:
            self.stderr.write(self.style.ERROR("Could not fetch any training data. Aborting."))
            return

        self.stdout.write("Combining all datasets...")
        combined_df = pd.concat(all_data)

        self.stdout.write("Preparing features and target variables...")
        features = [
            'Volume', 'SMA_20', 'SMA_50', 'SMA_200', 'RSI_14',
            'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9',
            'BBL_5_2.0', 'BBM_5_2.0', 'BBU_5_2.0', 'BBB_5_2.0', 'BBP_5_2.0',
            'trailingPE', 'forwardPE', 'pegRatio', 'priceToBook', 'sentiment',
            'repo_rate' # Add new feature here
        ]
        
        future_price = combined_df['Close'].shift(-10)
        price_change = (future_price - combined_df['Close']) / combined_df['Close']
        
        y = pd.Series(1, index=combined_df.index)
        y[price_change > 0.03] = 2
        y[price_change < -0.03] = 0
        
        X = combined_df[features]

        final_df = pd.concat([X, y.rename('target')], axis=1)
        final_df_cleaned = final_df.dropna()
        
        X_train = final_df_cleaned[features]
        y_train = final_df_cleaned['target']

        self.stdout.write("Starting hyperparameter tuning...")
        param_grid = { 'n_estimators': [100], 'max_depth': [10, 20], 'min_samples_leaf': [2, 4], 'class_weight': ['balanced']}
        grid_search = GridSearchCV(estimator=RandomForestClassifier(random_state=42), param_grid=param_grid, cv=3, n_jobs=-1, verbose=2)
        grid_search.fit(X_train, y_train)

        best_model = grid_search.best_estimator_
        self.stdout.write(f"Best parameters found: {grid_search.best_params_}")

        joblib.dump(best_model, 'saha_ai_model.joblib')
        self.stdout.write(self.style.SUCCESS("Successfully trained and saved the new generalized AI model."))
