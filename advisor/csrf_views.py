from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json

class CustomCSRFFailureView(View):
    """Custom CSRF failure view that handles cross-domain scenarios"""
    
    def get(self, request, *args, **kwargs):
        # Check if this is a mobile user trying to access PC service
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        mobile_patterns = [
            'mobile', 'android', 'iphone', 'ipad', 'tablet',
            'blackberry', 'windows phone', 'opera mini', 'iemobile'
        ]
        
        is_mobile = any(pattern in user_agent for pattern in mobile_patterns)
        
        if is_mobile:
            # Redirect mobile users to mobile service
            import os
            mobile_service_url = os.environ.get('MOBILE_SERVICE_URL')
            if mobile_service_url:
                from django.http import HttpResponseRedirect
                redirect_url = f"{mobile_service_url}{request.path}"
                return HttpResponseRedirect(redirect_url)
        
        # For desktop users or if no mobile service, show standard CSRF error
        if request.headers.get('Accept', '').startswith('application/json'):
            return JsonResponse({
                'error': 'CSRF verification failed',
                'message': 'Please refresh the page and try again.',
                'csrf_token': request.META.get('CSRF_COOKIE', '')
            }, status=403)
        
        # Return HTML error page
        from django.http import HttpResponse
        return HttpResponse(
            '<html><body><h1>CSRF Verification Failed</h1>'
            '<p>Please refresh the page and try again.</p>'
            '<p><a href="/">Go to Home</a></p></body></html>',
            status=403
        )
    
    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)
