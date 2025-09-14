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
            user = getattr(request, 'user', None)
            if user and getattr(user, 'is_authenticated', False):
                # Refresh from DB to pick up role or other field changes
                try:
                    fresh = User.objects.filter(pk=user.pk).first()
                    if fresh:
                        request.user = fresh
                except DatabaseError:
                    logger.exception('Database error while refreshing user %s', getattr(user, 'pk', None))
        except Exception:
            logger.exception('Unexpected error in RefreshUserMiddleware')
