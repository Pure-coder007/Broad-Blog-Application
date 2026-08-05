from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from .models import UserSession



class UpdateSessionActivityMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        
        if request.user.is_authenticated:   
            refresh = request.headers.get("X-Refresh-Token")
        
            if refresh:
                UserSession.objects.filter(
                user=request.user,
                refresh_token=refresh,
                is_active=True,
            ).update(
                last_activity=timezone.now()
            )
            
            
        return response