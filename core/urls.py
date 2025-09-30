from django.contrib import admin
from django.urls import path, include
from advisor import views as advisor_views
from django.contrib.auth import views as auth_views
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "healthy", "message": "SAHA-AI is running"})

urlpatterns = [
    path("admin/", admin.site.urls),

    # Health check endpoint
    path("health/", health_check, name="health"),

    # Authentication
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Main pages
    path("", advisor_views.chat_view, name="home"),
    path("profile/", advisor_views.profile_view, name="profile"),
    path("about/", advisor_views.about_view, name="about"),
    path("portfolio-page/", advisor_views.portfolio_page_view, name="portfolio-page"),

    # APIs
    path("api/", include("advisor.urls")),
    path("users/", include("users.urls")),  # if you already have login/signup here
]
