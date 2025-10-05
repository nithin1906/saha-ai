from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import User
from .models import UserProfile, AccessLog
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class InviteOnlyMiddleware(MiddlewareMixin):
    """Middleware to enforce invite-only access"""
    
    def process_request(self, request):
        # Skip middleware for static files, admin, auth pages, health check, and API endpoints
        if (request.path.startswith('/static/') or 
            request.path.startswith('/admin/') or
            request.path.startswith('/users/') or
            request.path.startswith('/api/') or  # Allow all API endpoints
            request.path == '/favicon.ico' or
            request.path == '/health/'):
            return None
        
        # Allow unauthenticated users to access login/register pages
        if not request.user.is_authenticated:
            if request.path in ['/users/login/', '/users/register/', '/users/logout/']:
                return None
            # Preserve the next parameter for mobile redirects
            next_param = f"?next={request.path}" if request.path.startswith('/mobile/') else ""
            return redirect(f'/users/login/{next_param}')
        
        # Check if user is approved
        try:
            profile = UserProfile.objects.get(user=request.user)
            if not profile.is_approved:
                # Log unauthorized access attempt
                AccessLog.objects.create(
                    user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    action='unauthorized_access_attempt',
                    success=False
                )
                logout(request)
                return redirect('/users/login/?message=pending_approval')
        except UserProfile.DoesNotExist:
            # User doesn't have a profile, log them out
            AccessLog.objects.create(
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                action='no_profile_access_attempt',
                success=False
            )
            logout(request)
            return redirect('/users/login/?message=no_profile')
        
        return None

class SecurityLoggingMiddleware(MiddlewareMixin):
    """Middleware to log all requests for security monitoring"""
    
    def process_request(self, request):
        # Skip logging for health check endpoint
        if request.path == '/health/':
            return None
            
        if request.user.is_authenticated:
            # Log access
            AccessLog.objects.create(
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                action=f'access_{request.path.replace("/", "_")}',
                success=True
            )
        
        return None

class IPWhitelistMiddleware(MiddlewareMixin):
    """Optional middleware for IP whitelisting (can be enabled later)"""
    
    def process_request(self, request):
        # This can be enabled later for additional security
        # For now, we'll just log IPs
        ip_address = request.META.get('REMOTE_ADDR')
        logger.info(f"Access from IP: {ip_address} to {request.path}")
        
        return None
