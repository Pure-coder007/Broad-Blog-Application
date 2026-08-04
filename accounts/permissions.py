from rest_framework.permissions import BasePermission
from accounts.models import User

class IsAdmin(BasePermission):
    
    # Allows access only to admin users
    def has_permission(self, request, view):
        return (request.user.is_authenticated and request.user.role == User.ADMIN)
    
    
    
    

class IsModerator(BasePermission):
    
    # Allows access only to moderator 
    def has_permission(self, request, view):
        return (request.user.is_authenticated and request.user.role == User.MODERATOR)
    
    
    
    
    

class IsAdminOrModerator(BasePermission):
    
    # Allows access only to admin users
    def has_permission(self, request, view):
        return (request.user.is_authenticated and request.user.role in [User.ADMIN, User.MODERATOR])