from django.urls import path
from . import views

app_name = 'advisor'

urlpatterns = [
    # Desktop URLs
    path('', views.index, name='index'),
    path('portfolio/', views.portfolio, name='portfolio'),
    path('about/', views.about, name='about'),
    path('profile/', views.profile, name='profile'),
    
    # Mobile URLs
    path('mobile/', views.mobile_index, name='mobile_index'),
    path('mobile/portfolio/', views.mobile_portfolio, name='mobile_portfolio'),
    
    # API URLs
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/portfolio/', views.portfolio_api, name='portfolio_api'),
    path('api/portfolio/add/', views.add_to_portfolio, name='add_to_portfolio'),
    path('api/portfolio/remove/<str:ticker>/', views.remove_from_portfolio, name='remove_from_portfolio'),
    path('api/portfolio/health/', views.portfolio_health, name='portfolio_health'),
    path('api/market-snapshot/', views.market_snapshot, name='market_snapshot'),
    path('api/mutual-fund-search/', views.mutual_fund_search, name='mutual_fund_search'),
    path('api/mutual-fund-analysis/', views.mutual_fund_analysis, name='mutual_fund_analysis'),
    path('api/stock-analysis/', views.stock_analysis, name='stock_analysis'),
]