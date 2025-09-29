from django.urls import path
from . import views   # import whole views module for function-based views

from .views import (
    StockAnalysisView,
    StockSearchView,
    StockHistoryView,
    PortfolioView,
    HoldingDetailView,
    StockNewsView,
    PortfolioHealthView,
    ParseIntentView,
    PortfolioDetailView,
    MarketSnapshotView,
    DevVersionView,
    MutualFundHistoryView
)

urlpatterns = [
    # Natural Language Understanding Endpoint
    path("parse/", ParseIntentView.as_view(), name="parse-intent"),

    # Portfolio Management Endpoints
    path("portfolio/health/", PortfolioHealthView.as_view(), name="portfolio-health"),
    path("portfolio/details/", PortfolioDetailView.as_view(), name="portfolio-details"),
    path("portfolio/", PortfolioView.as_view(), name="portfolio-add-update"),
    path("portfolio/holding/<int:holding_id>/", HoldingDetailView.as_view(), name="holding-detail"),

    # Mutual Fund Endpoints (must come before general search pattern)
    path("search/MF/<str:query>/", views.search_mutual_funds, name="mf-search"),
    path("analyze_mf/<str:scheme_id>/<str:buy_nav>/<str:units>/", views.analyze_mutual_fund, name="mf-analyze"),
    path("history_mf/<str:scheme_id>/", MutualFundHistoryView.as_view(), name="mf-history"),

    # Stock Data Endpoints
    path("news/<str:ticker>/", StockNewsView.as_view(), name="stock-news"),
    path("search/<str:exchange>/<str:query>/", StockSearchView.as_view(), name="stock-search"),
    path("history/<str:ticker>/", StockHistoryView.as_view(), name="stock-history"),

    # Stock Analysis Endpoint
    path("analyze/<str:ticker>/<str:buy_price>/<int:num_shares>/", StockAnalysisView.as_view(), name="stock-analysis"),

    # Market snapshot
    path("market/snapshot/", MarketSnapshotView.as_view(), name="market-snapshot"),

    # Dev live-reload version
    path("dev/version/", DevVersionView.as_view(), name="dev-version"),
]
