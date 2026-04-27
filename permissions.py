from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from rest_framework.permissions import BasePermission
from .models import UserProfile


class TokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        authorization = request.headers.get('Authorization', '')
        if not authorization.startswith('Token '):
            return None

        token = authorization.split(' ', 1)[1].strip()
        if not token:
            return None

        try:
            profile = UserProfile.objects.select_related('user').get(api_token=token)
        except UserProfile.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token.')

        return profile.user, None


class IsReviewer(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            getattr(user, 'is_authenticated', False)
            and getattr(getattr(user, 'profile', None), 'role', None)
            == UserProfile.ROLE_REVIEWER
        )


class IsOwnerOrReviewer(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not getattr(user, 'is_authenticated', False):
            return False
        if getattr(getattr(user, 'profile', None), 'role', None) == UserProfile.ROLE_REVIEWER:
            return True
        return obj.user == user
