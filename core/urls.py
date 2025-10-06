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

    # Mobile pages (main entry points for mobile service)
    path("", advisor_views.index, name="home"),
    path("portfolio/", advisor_views.portfolio, name="portfolio"),
    path("profile/", advisor_views.profile, name="profile"),
    path("about/", advisor_views.about, name="about"),
    
    # Mobile-specific URLs
    path("mobile/", advisor_views.mobile_index, name="mobile_index"),
    path("mobile/portfolio/", advisor_views.mobile_portfolio, name="mobile_portfolio"),
    path("mobile/profile/", advisor_views.mobile_profile, name="mobile_profile"),
    path("mobile/about/", advisor_views.mobile_about, name="mobile_about"),

    # APIs
    path("api/", include("advisor.urls")),
    path("users/", include("users.urls")),  # if you already have login/signup here
]
