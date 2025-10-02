from django.urls import path
from . import views   # import whole views module for function-based views

from .views import (
    PortfolioView,
    MarketSnapshotView,
    ParseIntentView,
    ChatView,
    MutualFundView,
    PortfolioHealthView
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

    # Market snapshot
    path("market/snapshot/", MarketSnapshotView.as_view(), name="market-snapshot"),

    # Chat endpoint
    path("chat/", ChatView.as_view(), name="chat"),
]
