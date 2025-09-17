from .models import StudentNotification

def student_notification_count(request):
    """
    Context processor to add unread student notification count to all templates
    """
    try:
        user = getattr(request, 'user', None)
        if not user:
            return {'student_unread_notifications_count': 0}

        if getattr(user, 'is_authenticated', False) and hasattr(user, 'student'):
            student = user.student
            student_unread_notifications_count = StudentNotification.objects.filter(recipient=student, is_read=False).count()
            return {'student_unread_notifications_count': student_unread_notifications_count}
    except Exception:
        pass
    return {'student_unread_notifications_count': 0}
