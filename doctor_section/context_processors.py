from .models import Notification


def notification_count(request):
    """Context processor to add unread notification count to all templates.

    This is defensive: during some error handling paths the request object
    may not have a user attribute, or user may not be authenticated. Avoid
    raising exceptions while rendering templates.
    """
    try:
        user = getattr(request, 'user', None)
        if not user:
            return {'unread_notifications_count': 0}

        if getattr(user, 'is_authenticated', False) and hasattr(user, 'doctor_profile'):
            doctor = user.doctor_profile
            unread_notifications_count = Notification.objects.filter(
                recipient=doctor, is_read=False
            ).count()
            return {'unread_notifications_count': unread_notifications_count}
    except Exception:
        # swallow any errors in context processors to avoid breaking error pages
        pass

    return {'unread_notifications_count': 0}
