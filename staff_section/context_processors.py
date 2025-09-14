from .models import StaffNotification

def staff_notification_count(request):
    """
    Context processor to add unread staff notification count to all templates
    """
    try:
        user = getattr(request, 'user', None)
        if not user:
            return {'staff_unread_notifications_count': 0}

        if getattr(user, 'is_authenticated', False) and hasattr(user, 'staff_profile'):
            staff = user.staff_profile
            staff_unread_notifications_count = StaffNotification.objects.filter(recipient=staff, is_read=False).count()
            return {'staff_unread_notifications_count': staff_unread_notifications_count}
    except Exception:
        pass
    return {'staff_unread_notifications_count': 0}
