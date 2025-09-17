from rest_framework.permissions import BasePermission, SAFE_METHODS


class AdminPermission(BasePermission):
    message = "Access restricted to admin users only."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type.lower() == "admin"


class ArtisanPermission(BasePermission):
    message = "Only artisans can edit."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.user_type.upper() == 'ADMIN':
            return True

        if request.method in SAFE_METHODS:
            return True

        if request.user.user_type.upper() == 'ARTISAN':
            return True

        return False

    def has_object_permission(self, request, view, obj):
        if request.user.user_type.upper() == 'ADMIN':
            return True

        if request.method in SAFE_METHODS:
            return True

        if request.user.user_type.upper() == 'ARTISAN':
            return obj.artisan == request.user

        return False
