from django.urls import path
from .views import (
    StockAnalysisView, 
    StockSearchView, 
    StockHistoryView, 
    PortfolioView, 
    HoldingDetailView,
    StockNewsView,
    PortfolioHealthView,
    ParseIntentView
)

urlpatterns = [
    path('parse/', ParseIntentView.as_view(), name='parse-intent'),
    path('portfolio/health/', PortfolioHealthView.as_view(), name='portfolio-health'),
    path('portfolio/', PortfolioView.as_view(), name='portfolio-list'),
    path('portfolio/holding/<int:holding_id>/', HoldingDetailView.as_view(), name='holding-detail'),
    path('news/<str:ticker>/', StockNewsView.as_view(), name='stock-news'),
    path('search/<str:exchange>/<str:query>/', StockSearchView.as_view(), name='stock-search'),
    path('history/<str:ticker>/', StockHistoryView.as_view(), name='stock-history'),
    path('analyze/<str:ticker>/<str:buy_price>/<int:num_shares>/', StockAnalysisView.as_view(), name='stock-analysis'),
]

