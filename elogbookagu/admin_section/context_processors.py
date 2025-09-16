from .models import AdminNotification

def admin_notification_count(request):
    """
    Context processor to add unread admin notification count to all templates
    """
    if request.user.is_authenticated and request.user.role == 'admin':
        try:
            admin_unread_notifications_count = AdminNotification.objects.filter(recipient=request.user, is_read=False).count()
            return {'admin_unread_notifications_count': admin_unread_notifications_count}
        except:
            pass
    return {'admin_unread_notifications_count': 0}
