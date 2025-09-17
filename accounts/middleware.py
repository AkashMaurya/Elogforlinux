from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.db import DatabaseError
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class RefreshUserMiddleware(MiddlewareMixin):
    """Reload `request.user` from the database on each request.

    This ensures that role changes performed in the admin UI take effect
    immediately for redirect decisions and permission checks during the
    same user's next requests.
    """

    def process_request(self, request):
        try:
            # Skip refresh during SSO-related paths to avoid interfering with authentication
            sso_paths = [
                '/accounts/microsoft/login/callback/',
                '/accounts/3rdparty/',
                '/accounts/post-login-redirect/',
            ]
            if any(request.path.startswith(path) for path in sso_paths):
                logger.debug('RefreshUserMiddleware: skipping refresh for SSO path: %s', request.path)
                return

            user = getattr(request, 'user', None)
            if user and getattr(user, 'is_authenticated', False):
                # Refresh from DB to pick up role or other field changes
                try:
                    fresh = User.objects.filter(pk=user.pk).first()
                    if fresh:
                        request.user = fresh
                        logger.debug('RefreshUserMiddleware: refreshed user %s', getattr(fresh, 'pk', None))
                except DatabaseError:
                    logger.exception('Database error while refreshing user %s', getattr(user, 'pk', None))
        except Exception:
            logger.exception('Unexpected error in RefreshUserMiddleware')
