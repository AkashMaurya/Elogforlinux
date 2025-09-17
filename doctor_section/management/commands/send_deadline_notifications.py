from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings as django_settings

from student_section.models import StudentLogFormModel
from doctor_section.models import Notification
from admin_section.models import DateRestrictionSettings


class Command(BaseCommand):
    help = 'Send notifications to doctors about logs approaching review deadline'

    def handle(self, *args, **options):
        # Get settings
        settings = DateRestrictionSettings.objects.first()
        if not settings or not settings.doctor_review_enabled:
            self.stdout.write(self.style.WARNING('Review period feature is disabled. No notifications sent.'))
            return

        # Calculate the date range for notifications
        # We want to notify about logs that will expire in exactly notification_days days
        notification_days = settings.doctor_notification_days
        target_date = timezone.now() + timedelta(days=notification_days)
        
        # Find logs that will expire on the target date (within a 24-hour window)
        start_window = target_date - timedelta(hours=12)
        end_window = target_date + timedelta(hours=12)
        
        logs_to_notify = StudentLogFormModel.objects.filter(
            is_reviewed=False,  # Only unreviewed logs
            review_deadline__gte=start_window,
            review_deadline__lte=end_window
        )
        
        notification_count = 0
        
        # Group logs by doctor to avoid sending multiple notifications
        doctor_logs = {}
        for log in logs_to_notify:
            doctor = log.tutor
            if doctor.id not in doctor_logs:
                doctor_logs[doctor.id] = {
                    'doctor': doctor,
                    'logs': []
                }
            doctor_logs[doctor.id]['logs'].append(log)
        
        # Send notifications to each doctor
        for doctor_id, data in doctor_logs.items():
            doctor = data['doctor']
            logs = data['logs']
            
            if not logs:
                continue
                
            # Create notification message
            log_count = len(logs)
            notification_title = f"Action Required: {log_count} log(s) approaching review deadline"
            
            notification_message = f"You have {log_count} student log(s) that will reach their review deadline in {notification_days} days. "
            notification_message += f"Please review these logs before they expire. After the deadline, you will no longer be able to review them.\n\n"
            
            # Add details for each log
            for i, log in enumerate(logs[:5], 1):  # Limit to first 5 logs to avoid very long messages
                student_name = log.student.user.get_full_name() or log.student.user.username
                notification_message += f"{i}. Student: {student_name}, Department: {log.department.name}, Date: {log.date}\n"
                
            if log_count > 5:
                notification_message += f"\n...and {log_count - 5} more log(s). Please check your review page for the complete list."
            
            # Create notification in database
            Notification.objects.create(
                recipient=doctor,
                title=notification_title,
                message=notification_message
            )
            
            # Send email notification
            try:
                send_mail(
                    subject=notification_title,
                    message=notification_message,
                    from_email=django_settings.EMAIL_HOST_USER,
                    recipient_list=[doctor.user.email],
                    fail_silently=True,
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error sending email to {doctor.user.email}: {e}"))
            
            notification_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully sent notifications to {notification_count} doctors about approaching review deadlines'))
