# back_drop/common/permissions.py
from rest_framework.permissions import BasePermission

class IsOwner(BasePermission):
    """
    Object-level permission: only allow owners of an object to access it.
    Expects the model to have a `user` FK.
    """
    def has_object_permission(self, request, view, obj):
        user = getattr(obj, "user", None) == request.user
        return user is not None and user == request.user