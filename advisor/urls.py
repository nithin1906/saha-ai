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
    path('mobile/profile/', views.mobile_profile, name='mobile_profile'),
    path('mobile/about/', views.mobile_about, name='mobile_about'),
    
    # API URLs
    path('chat/', views.chat_api, name='chat_api'),
    path('mobile-chat/', views.mobile_chat_api, name='mobile_chat_api'),
    path('portfolio/', views.portfolio_api, name='portfolio_api'),
    path('portfolio/details/', views.portfolio_api, name='portfolio_details'),
    path('portfolio/add/', views.add_to_portfolio, name='add_to_portfolio'),
    path('portfolio/remove/<str:ticker>/', views.remove_from_portfolio, name='remove_from_portfolio'),
    path('portfolio/health/', views.portfolio_health, name='portfolio_health'),
    path('market-snapshot/', views.market_snapshot, name='market_snapshot'),
    path('stock-search/', views.stock_search, name='stock_search'),
    path('mutual-fund-search/', views.mutual_fund_search, name='mutual_fund_search'),
    path('mutual-fund-analysis/', views.mutual_fund_analysis, name='mutual_fund_analysis'),
    path('stock-analysis/', views.stock_analysis, name='stock_analysis'),
]