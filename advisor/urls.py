from django.urls import path
from . import views   # import whole views module for function-based views

from .views import (
    PortfolioView,
    MarketSnapshotView,
    ParseIntentView,
    ChatView,
    MutualFundView,
    PortfolioHealthView,
    StockSearchView,
    MutualFundSearchView,
    StockAnalysisView,
    StockHistoryView,
    MutualFundAnalysisView,
    MutualFundHistoryView,
    DevVersionView,
    MutualFundCategoriesView,
    MutualFundDetailsView
)

urlpatterns = [
    # Natural Language Understanding Endpoint
    path("parse/", ParseIntentView.as_view(), name="parse-intent"),

    # Portfolio Management Endpoints
    path("portfolio/", PortfolioView.as_view(), name="portfolio-add-update"),
    path("portfolio/health/", PortfolioHealthView.as_view(), name="portfolio-health"),
    path("portfolio/details/", PortfolioView.as_view(), name="portfolio-details"),

    # Mutual Fund Endpoints
    path("mutual-fund/", MutualFundView.as_view(), name="mutual-fund"),
    path("mutual-fund/categories/", MutualFundCategoriesView.as_view(), name="mutual-fund-categories"),
    path("mutual-fund/<str:scheme_id>/", MutualFundDetailsView.as_view(), name="mutual-fund-details"),

    # Market snapshot
    path("market/snapshot/", MarketSnapshotView.as_view(), name="market-snapshot"),

    # Chat endpoint
    path("chat/", ChatView.as_view(), name="chat"),

    # Search endpoints
    path("search/MF/<str:query>/", MutualFundSearchView.as_view(), name="mutual-fund-search"),
    path("search/<str:exchange>/<str:query>/", StockSearchView.as_view(), name="stock-search"),

    # Analysis endpoints
    path("analyze/<str:ticker>/<str:buy_price>/<str:shares>/", StockAnalysisView.as_view(), name="stock-analysis"),
    path("analyze_mf/<str:scheme_id>/<str:buy_nav>/<str:units>/", MutualFundAnalysisView.as_view(), name="mutual-fund-analysis"),

    # History endpoints
    path("history/<str:ticker>/", StockHistoryView.as_view(), name="stock-history"),
    path("history_mf/<str:scheme_id>/", MutualFundHistoryView.as_view(), name="mutual-fund-history"),

    # Development endpoints
    path("dev/version/", DevVersionView.as_view(), name="dev-version"),
]
