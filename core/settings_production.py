"""
Production settings for Railway deployment
"""
import os
from .settings import *

# Production settings
DEBUG = False
ALLOWED_HOSTS = ['*']  # Railway will handle this

# Database - Railway provides DATABASE_URL
if 'DATABASE_URL' in os.environ:
    import dj_database_url
    DATABASES['default'] = dj_database_url.parse(os.environ['DATABASE_URL'])

# Static files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.StaticFilesStorage'

# Additional locations of static files
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'advisor', 'static'),
]

# WhiteNoise configuration for proper MIME types
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

# MIME type configuration
import mimetypes
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('application/json', '.json')
mimetypes.add_type('application/manifest+json', '.webmanifest')

# Add whitenoise middleware for static file serving
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add whitenoise middleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'advisor.middleware.DeviceDetectionMiddleware',
    'users.middleware.SecurityLoggingMiddleware',
]

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS settings for Railway
SECURE_SSL_REDIRECT = False  # Railway handles SSL termination
SESSION_COOKIE_SECURE = False  # Allow HTTP for Railway
CSRF_COOKIE_SECURE = False  # Allow HTTP for Railway

# CSRF settings - comprehensive for cross-domain scenarios
CSRF_TRUSTED_ORIGINS = [
    'https://web-production-db25.up.railway.app',
    'https://saha-ai.up.railway.app',
    'https://saha-ai-mobile.up.railway.app',  # Mobile service
    'http://saha-ai.up.railway.app',  # Allow HTTP for Railway
    'http://saha-ai-mobile.up.railway.app',  # Allow HTTP for Railway mobile
    # Add all possible Railway subdomain variations
    'https://web-production-db25.up.railway.app',
    'https://web-production-db26.up.railway.app',
    'https://web-production-db27.up.railway.app',
    'https://web-production-db28.up.railway.app',
    'https://web-production-db29.up.railway.app',
    'https://web-production-db30.up.railway.app',
]

# Additional CSRF settings for cross-domain compatibility
CSRF_COOKIE_DOMAIN = None  # Allow cookies to work across subdomains
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript access for better handling
CSRF_COOKIE_SAMESITE = 'Lax'  # Allow cross-site requests
CSRF_COOKIE_AGE = 3600  # 1 hour
CSRF_USE_SESSIONS = False  # Use cookies instead of sessions for CSRF

# CORS settings - more permissive
CORS_ALLOWED_ORIGINS = [
    "https://saha-ai.up.railway.app",
    "https://saha-ai-mobile.up.railway.app",
    "http://saha-ai.up.railway.app",
    "http://saha-ai-mobile.up.railway.app",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # Keep this False for security
CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Session settings for cross-domain compatibility
SESSION_COOKIE_DOMAIN = None  # Allow sessions across subdomains
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_SAVE_EVERY_REQUEST = True

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
    },
}