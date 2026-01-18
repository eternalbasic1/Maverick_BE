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
        # First check if user is authenticated
        if not (hasattr(request, 'user') and request.user and 
                hasattr(request, 'auth') and request.auth):
            self.message = 'Authentication required. Please provide a valid JWT token.'
            return False
        
        # Then check if user is admin
        if request.user.role != 'admin':
            self.message = f'Admin access required. Current role: {request.user.role}.'
            return False
        
        return True

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

class IsDeliveryPartner(BasePermission):
    """
    Custom permission that only allows access to delivery partner users.
    """
    message = 'Delivery partner access required.'
    
    def has_permission(self, request, view):
        """
        Return True if the request user is authenticated and has delivery_partner role.
        """
        # First check if user is authenticated
        if not (hasattr(request, 'user') and request.user and 
                hasattr(request, 'auth') and request.auth):
            self.message = 'Authentication required. Please provide a valid JWT token.'
            return False
        
        # Then check if user is delivery partner
        if request.user.role != 'delivery_partner':
            self.message = f'Delivery partner access required. Current role: {request.user.role}.'
            return False
        
        return True

class IsAdminOrDeliveryPartner(BasePermission):
    """
    Custom permission that allows access to admin users OR delivery partner users.
    """
    message = 'Admin or delivery partner access required.'
    
    def has_permission(self, request, view):
        """
        Return True if the request user is authenticated and has admin or delivery_partner role.
        """
        # First check if user is authenticated
        if not (hasattr(request, 'user') and request.user and 
                hasattr(request, 'auth') and request.auth):
            self.message = 'Authentication required. Please provide a valid JWT token.'
            return False
        
        # Check if user is admin or delivery partner
        if request.user.role not in ['admin', 'delivery_partner']:
            self.message = f'Admin or delivery partner access required. Current role: {request.user.role}.'
            return False
        
        return True