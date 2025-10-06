from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseRedirect
import os
import re

class DeviceDetectionMiddleware(MiddlewareMixin):
    """Middleware to detect device type and route mobile users to mobile service"""
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.async_mode = False
        self.mobile_service_url = os.environ.get('MOBILE_SERVICE_URL')
    
    def process_request(self, request):
        # Skip redirect for certain paths
        skip_paths = [
            '/static/', '/admin/', '/api/', '/health/', '/favicon.ico',
            '/users/login/', '/users/register/', '/users/logout/'
        ]
        
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # Skip if already on mobile service
        if 'mobile' in request.path:
            return None
        
        # Get user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        
        # Mobile device patterns
        mobile_patterns = [
            'mobile', 'android', 'iphone', 'ipad', 'tablet',
            'blackberry', 'windows phone', 'opera mini', 'iemobile'
        ]
        
        # Check if it's a mobile device
        is_mobile = any(pattern in user_agent for pattern in mobile_patterns)
        
        # Check for manual override in URL parameters
        if 'mobile' in request.GET:
            is_mobile = request.GET.get('mobile') == '1'
        elif 'desktop' in request.GET:
            is_mobile = request.GET.get('desktop') == '0'
        
        # Check session for stored preference
        if 'force_mobile' in request.session:
            is_mobile = request.session['force_mobile']
        
        # Store preference in session for future requests
        if 'mobile' in request.GET or 'desktop' in request.GET:
            request.session['force_mobile'] = is_mobile
        
        # Add device info to request
        request.is_mobile = is_mobile
        
        # Redirect mobile users to mobile service
        if is_mobile and self.mobile_service_url:
            # Preserve the path and query parameters
            redirect_url = f"{self.mobile_service_url}{request.path}"
            if request.GET:
                query_string = request.GET.urlencode()
                redirect_url += f"?{query_string}"
            
            return HttpResponseRedirect(redirect_url)
        
        return None
