# advisor/management/commands/fetch_data.py
from django.core.management.base import BaseCommand, CommandError
from advisor.data_service import get_stock_data
from advisor.ml_service import train_and_predict
from advisor.personalization_service import personalize_signal

class Command(BaseCommand):
    help = 'Runs the full AI pipeline to generate a personalized stock recommendation.'

    def add_arguments(self, parser):
        parser.add_argument('ticker', type=str, help='The stock ticker symbol (e.g., RELIANCE.NS)')
        parser.add_argument('buy_price', type=float, help='The user\'s average buy price for the stock.')
        # **FIX IS HERE:** Add the new num_shares argument
        parser.add_argument('num_shares', type=int, help='The number of shares the user holds.')

    def handle(self, *args, **options):
        ticker = options['ticker']
        buy_price = options['buy_price']
        num_shares = options['num_shares'] # Get the new argument
        
        # --- Step 1: Data Ingestion & Analysis ---
        self.stdout.write(self.style.NOTICE(f"Step 1: Fetching and analyzing data for {ticker}..."))
        data = get_stock_data(ticker)
        if data is None:
            raise CommandError(f"Failed to fetch or analyze data for {ticker}.")
        self.stdout.write(self.style.SUCCESS("...Analysis complete."))
        
        # --- Step 2: Machine Learning Signal Generation ---
        self.stdout.write(self.style.NOTICE(f"Step 2: Generating core AI signal..."))
        ml_signal = train_and_predict(data)
        if "Error" in ml_signal or "Not Enough Data" in ml_signal:
             raise CommandError(f"Could not generate an ML signal. Reason: {ml_signal}")
        self.stdout.write(self.style.SUCCESS(f"...Core signal is '{ml_signal}'."))

        # --- Step 3: Personalization ---
        self.stdout.write(self.style.NOTICE(f"Step 3: Personalizing signal for {num_shares} shares at a buy price of {buy_price}..."))
        current_price = data['Close'].iloc[-1]
        final_signal, explanation = personalize_signal(ml_signal, buy_price, current_price, num_shares)
        self.stdout.write(self.style.SUCCESS("...Personalization complete."))

        # --- Final Output ---
        self.stdout.write(self.style.SUCCESS(f"\n========================================================"))
        self.stdout.write(self.style.SUCCESS(f"  SAHA-AI Recommendation for {ticker}"))
        self.stdout.write(self.style.SUCCESS(f"========================================================"))
        self.stdout.write(f"  Your Position:          {num_shares} shares at {buy_price:.2f}")
        self.stdout.write(f"  Current Market Price:   {current_price:.2f}")
        self.stdout.write(f"  Generic AI Signal:      {ml_signal}")
        self.stdout.write(f"  ------------------------------------------------------")
        self.stdout.write(f"  Personalized Advice:    {self.style.WARNING(final_signal)}")
        self.stdout.write(f"  Reasoning:              {explanation}")
        self.stdout.write(self.style.SUCCESS(f"========================================================"))