import re
from django.urls import resolve
from .utils import log_user_activity

class UserActivityMiddleware:
    """
    Middleware to automatically log user activities for certain views
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Compile patterns for URLs we want to track
        self.tracked_url_patterns = [
            (r'/calendar/$', 'view', 'Viewed calendar'),
            (r'/tasks/$', 'view', 'Viewed tasks'),
            (r'/admin/tasks/$', 'view', 'Viewed admin tasks'),
            (r'/admin/dashboard/$', 'view', 'Viewed admin dashboard'),
            # Add more URL patterns as needed
        ]
        self.compiled_patterns = [(re.compile(pattern), action_type, detail) 
                                 for pattern, action_type, detail in self.tracked_url_patterns]
        
    def __call__(self, request):
        # Process the request
        response = self.get_response(request)
        
        # Only log for authenticated users
        if request.user.is_authenticated:
            path = request.path
            
            # Check if the current path matches any of our tracked patterns
            for pattern, action_type, detail in self.compiled_patterns:
                if pattern.match(path):
                    # Get the IP address
                    ip_address = self.get_client_ip(request)
                    
                    # Get the actual user from the session if available
                    user = request.user
                    
                    # Debug information
                    print(f"Middleware logging for user: {user.username} (ID: {user.id})")
                    print(f"Request path: {path}")
                    print(f"IP Address: {ip_address}")
                    
                    # Check if we're in admin view or regular view
                    if '/admin/' in path and hasattr(request, 'session') and 'auth_user_id' in request.session:
                        # For admin views, use the actual user ID from session
                        try:
                            from django.contrib.auth.models import User
                            actual_user_id = request.session.get('auth_user_id')
                            if actual_user_id and int(actual_user_id) != user.id:
                                actual_user = User.objects.get(id=actual_user_id)
                                print(f"Using actual user from session: {actual_user.username} (ID: {actual_user.id})")
                                user = actual_user
                        except Exception as e:
                            print(f"Error getting actual user: {str(e)}")
                    
                    # Log the activity with the correct user
                    log_user_activity(
                        user=user,
                        action_type=action_type,
                        action_detail=detail,
                        ip_address=ip_address
                    )
                    break
        
        return response
    
    def get_client_ip(self, request):
        """Get the client's IP address from the request"""
        # Try multiple headers to find the real IP
        headers = [
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_REAL_IP',
            'HTTP_CLIENT_IP',
            'REMOTE_ADDR'
        ]
        
        for header in headers:
            ip = request.META.get(header)
            if ip:
                # If it's a comma-separated list, take the first one
                if ',' in ip:
                    ip = ip.split(',')[0].strip()
                # Don't return localhost if we can help it
                if ip != '127.0.0.1' and ip != 'localhost':
                    return ip
        
        # If we got here, use REMOTE_ADDR as fallback
        return request.META.get('REMOTE_ADDR', '')
