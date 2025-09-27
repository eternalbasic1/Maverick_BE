# milk_app/permissions.py
from rest_framework.permissions import BasePermission

class IsJWTAuthenticated(BasePermission):
    """
    Custom permission that only allows access to users authenticated via JWT token.
    """
    message = 'Authentication required. Please provide a valid JWT token.'
    
    def has_permission(self, request, view):
        """
        Return True if the request has been authenticated via JWT.
        """
        # Check if the request went through our JWT authentication
        return (
            hasattr(request, 'user') and 
            request.user and 
            hasattr(request, 'auth') and 
            request.auth  # This is the JWT token from our authentication class
        )

class IsAdmin(BasePermission):
    """
    Custom permission that only allows access to admin users.
    """
    message = 'Admin access required.'
    
    def has_permission(self, request, view):
        """
        Return True if the request user is authenticated and has admin role.
        """
        return (
            hasattr(request, 'user') and 
            request.user and
            hasattr(request, 'auth') and 
            request.auth and
            request.user.role == 'admin'
        )

class IsOwnerOrAdmin(BasePermission):
    """
    Custom permission that allows access to object owner or admin users.
    """
    message = 'You can only access your own resources or be an admin.'
    
    def has_object_permission(self, request, view, obj):
        """
        Return True if the request user owns the object or is admin.
        """
        if not (hasattr(request, 'user') and request.user and 
                hasattr(request, 'auth') and request.auth):
            return False
            
        # Admin can access everything
        if request.user.role == 'admin':
            return True
            
        # Owner can access their own objects
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # If object is the user themselves
        return obj == request.user