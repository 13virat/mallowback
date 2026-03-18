"""
Custom DRF permissions.
"""
from rest_framework.permissions import BasePermission


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level: allow access only to the object owner or admin users.
    The view must call self.check_object_permissions(request, obj).
    Object must have a .user attribute.
    """
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        return getattr(obj, 'user', None) == request.user


class IsAdminOrReadOnly(BasePermission):
    """Write access for admins only; read-only for all authenticated users."""
    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return bool(request.user and request.user.is_staff)
