# core/urls.py
from django.contrib import admin
from django.urls import path, include
from advisor import views as advisor_views 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('advisor.urls')),
    path('accounts/', include('users.urls')),
    # This line will now work correctly
    path('', advisor_views.chat_view, name='home'),
    path('about/', advisor_views.about_view, name='about'),
    path('profile/', advisor_views.profile_view, name='profile'),
]