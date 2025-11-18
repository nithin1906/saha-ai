# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.custom_login, name='login'),
    path('register/', views.register_with_invite, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Admin management
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('manage-invites/', views.manage_invites, name='manage_invites'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('access-logs/', views.access_logs, name='access_logs'),
    path('send-updates/', views.send_updates_to_all_users, name='send_updates'),
]