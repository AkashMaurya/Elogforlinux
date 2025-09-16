from .models import StaffNotification

def staff_notification_count(request):
    """
    Context processor to add unread staff notification count to all templates
    """
    if request.user.is_authenticated and hasattr(request.user, 'staff_profile'):
        try:
            staff = request.user.staff_profile
            staff_unread_notifications_count = StaffNotification.objects.filter(recipient=staff, is_read=False).count()
            return {'staff_unread_notifications_count': staff_unread_notifications_count}
        except:
            pass
    return {'staff_unread_notifications_count': 0}
