# advisor/serializers.py
from rest_framework import serializers
from .models import Holding, Portfolio

class HoldingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Holding
        fields = ['id', 'ticker', 'quantity', 'average_buy_price']

class PortfolioSerializer(serializers.ModelSerializer):
    holdings = HoldingSerializer(many=True, read_only=True)

    class Meta:
        model = Portfolio
        fields = ['id', 'name', 'user', 'holdings']