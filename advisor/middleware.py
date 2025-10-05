from django.utils.deprecation import MiddlewareMixin
import re

class DeviceDetectionMiddleware(MiddlewareMixin):
    """Middleware to detect device type and route accordingly"""
    
    def process_request(self, request):
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
        
        # Add device info to request
        request.is_mobile = is_mobile
        
        # Store preference in session for future requests
        if 'mobile' in request.GET or 'desktop' in request.GET:
            request.session['force_mobile'] = is_mobile
        
        # Check session for stored preference
        if 'force_mobile' in request.session:
            request.is_mobile = request.session['force_mobile']
        
        return None
