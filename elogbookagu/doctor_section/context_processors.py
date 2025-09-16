from .models import Notification

def notification_count(request):
    """
    Context processor to add unread notification count to all templates
    """
    if request.user.is_authenticated and hasattr(request.user, 'doctor_profile'):
        try:
            doctor = request.user.doctor_profile
            unread_notifications_count = Notification.objects.filter(recipient=doctor, is_read=False).count()
            return {'unread_notifications_count': unread_notifications_count}
        except:
            pass
    return {'unread_notifications_count': 0}
