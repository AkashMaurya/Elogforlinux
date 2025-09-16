from .models import StudentNotification

def student_notification_count(request):
    """
    Context processor to add unread student notification count to all templates
    """
    if request.user.is_authenticated and hasattr(request.user, 'student'):
        try:
            student = request.user.student
            student_unread_notifications_count = StudentNotification.objects.filter(recipient=student, is_read=False).count()
            return {'student_unread_notifications_count': student_unread_notifications_count}
        except:
            pass
    return {'student_unread_notifications_count': 0}
