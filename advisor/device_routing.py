from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
import re

class DeviceDetectionMiddleware(MiddlewareMixin):
    """Middleware to detect device type and route accordingly"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Mobile service URL - will be set via environment variable
        self.mobile_service_url = None
        # Required for Django 4.0+
        self.async_mode = False

    def process_request(self, request):
        # Get mobile service URL from environment
        import os
        self.mobile_service_url = os.environ.get('MOBILE_SERVICE_URL')
        
        # Debug logging
        print(f"DEBUG: MOBILE_SERVICE_URL = {self.mobile_service_url}")
        
        # Only proceed with mobile redirection if mobile service URL is configured
        if not self.mobile_service_url:
            # No mobile service configured, skip redirection
            request.is_mobile = False
            print("DEBUG: No mobile service URL configured, skipping redirection")
            return None
        
        # Get user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        print(f"DEBUG: User Agent = {user_agent}")
        
        # Mobile device patterns
        mobile_patterns = [
            'mobile', 'android', 'iphone', 'ipad', 'tablet',
            'blackberry', 'windows phone', 'opera mini', 'iemobile'
        ]
        
        # Check if it's a mobile device
        is_mobile = any(pattern in user_agent for pattern in mobile_patterns)
        print(f"DEBUG: Is mobile device = {is_mobile}")
        
        # Check for manual override in URL parameters
        if 'mobile' in request.GET:
            is_mobile = request.GET.get('mobile') == '1'
        elif 'desktop' in request.GET:
            is_mobile = request.GET.get('desktop') == '0'
        
        # Store preference in session for future requests
        if 'mobile' in request.GET or 'desktop' in request.GET:
            request.session['force_mobile'] = is_mobile
        
        # Check session for stored preference
        if 'force_mobile' in request.session:
            request.is_mobile = request.session['force_mobile']
        else:
            request.is_mobile = is_mobile
        
        # If this is the PC service and user is on mobile, redirect to mobile service
        # Only redirect if mobile service URL is properly configured
        if (is_mobile and 
            self.mobile_service_url and
            not request.path.startswith('/static/') and 
            not request.path.startswith('/admin/') and
            not request.path.startswith('/api/')):
            
            # Always redirect mobile users to mobile service (including login page)
            # This ensures they log in on the mobile service and get proper sessions
            redirect_url = f"{self.mobile_service_url}{request.path}"
            if request.GET:
                redirect_url += f"?{request.GET.urlencode()}"
            print(f"DEBUG: Redirecting mobile user to {redirect_url}")
            
            return redirect(redirect_url)
        
        print(f"DEBUG: No redirect needed - is_mobile={is_mobile}, path={request.path}")
        return None
