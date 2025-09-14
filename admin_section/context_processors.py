from .models import AdminNotification

def admin_notification_count(request):
    """
    Context processor to add unread admin notification count to all templates
    """
    try:
        user = getattr(request, 'user', None)
        if not user:
            return {'admin_unread_notifications_count': 0}

        if getattr(user, 'is_authenticated', False) and getattr(user, 'role', None) == 'admin':
            admin_unread_notifications_count = AdminNotification.objects.filter(recipient=user, is_read=False).count()
            return {'admin_unread_notifications_count': admin_unread_notifications_count}
    except Exception:
        pass
    return {'admin_unread_notifications_count': 0}
