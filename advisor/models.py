from django.db import models
from django.contrib.auth.models import User

class RiskProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    risk_tolerance = models.IntegerField(default=3, help_text="1=Conservative, 5=Aggressive")
    investment_horizon = models.IntegerField(default=5, help_text="Time in years")
    # Add other questions/fields as needed for a comprehensive profile
    
    def __str__(self):
        return f"{self.user.username}'s Risk Profile"

class StockAnalysis(models.Model):
    ticker = models.CharField(max_length=10)
    recommendation = models.CharField(max_length=10) # BUY, SELL, HOLD
    explanation = models.TextField()
    stop_loss = models.DecimalField(max_digits=10, decimal_places=2)
    target_price = models.DecimalField(max_digits=10, decimal_places=2)
    analyzed_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analysis for {self.ticker} at {self.analyzed_at}"
    
class Portfolio(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, default="My Portfolio")

    def __str__(self):
        return f"{self.user.username}'s Portfolio"

class Holding(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='holdings')
    ticker = models.CharField(max_length=20)
    quantity = models.PositiveIntegerField()
    average_buy_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} shares of {self.ticker} in {self.portfolio.user.username}'s portfolio"
