from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
from accounts.models import Student, CustomUser, Doctor
from admin_section.models import LogYear, LogYearSection, Group, Department, TrainingSite, ActivityType, CoreDiaProSession, DateRestrictionSettings

# Create your models here.


# Elog Form Model


class StudentLogFormModel(models.Model):
    # Basic info
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='log_forms')
    date = models.DateField()

    # Academic info
    log_year = models.ForeignKey(LogYear, on_delete=models.CASCADE)
    log_year_section = models.ForeignKey(LogYearSection, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    # Department and supervision
    department = models.ForeignKey(Department, on_delete=models.CASCADE)  # Changed from department to departments
    tutor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='supervised_logs')
    training_site = models.ForeignKey(TrainingSite, on_delete=models.CASCADE)

    # Activity details
    activity_type = models.ForeignKey(ActivityType, on_delete=models.CASCADE)
    core_diagnosis = models.ForeignKey(
        CoreDiaProSession,
        on_delete=models.CASCADE,
        related_name='log_forms'
    )

    # Optional fields
    patient_id = models.CharField(max_length=4, blank=True)
    patient_age = models.CharField(max_length=3, blank=True, null=True)
    patient_gender = models.CharField(max_length=10, blank=True, null=True,
                                     choices=[('Male', 'Male'), ('Female', 'Female')])
    description = models.TextField(blank=True)

    # Participation type
    PARTICIPATION_CHOICES = [
        ("Observed", "Observed"),
        ("Assisted", "Assisted")
    ]
    participation_type = models.CharField(
        max_length=50,
        choices=PARTICIPATION_CHOICES
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Review status
    is_reviewed = models.BooleanField(default=False)
    review_date = models.DateTimeField(null=True, blank=True)
    reviewer_comments = models.TextField(blank=True)
    review_deadline = models.DateTimeField(null=True, blank=True, help_text="Deadline by which the doctor must review this log")

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Student Log Form"
        verbose_name_plural = "Student Log Forms"

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.date}"

    def get_status(self):
        return "Reviewed" if self.is_reviewed else "Pending Review"


# Support Ticket Model
class SupportTicket(models.Model):
    # Basic info
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=100)
    description = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)

    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('solved', 'Solved')
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Admin response
    admin_comments = models.TextField(blank=True)
    resolved_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date_created']
        verbose_name = "Support Ticket"
        verbose_name_plural = "Support Tickets"

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.subject} ({self.status})"

    def mark_as_solved(self, comments=''):
        self.status = 'solved'
        self.admin_comments = comments
        self.resolved_date = timezone.now()
        self.save()


# Student Notification Model
class StudentNotification(models.Model):
    recipient = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='notifications')
    log_entry = models.ForeignKey(StudentLogFormModel, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=100)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Student Notification"
        verbose_name_plural = "Student Notifications"

    def __str__(self):
        return f"{self.recipient.user.get_full_name()} - {self.title}"

    def mark_as_read(self):
        self.is_read = True
        self.save()


# Signal to set review_deadline when a log is created
@receiver(post_save, sender=StudentLogFormModel)
def set_review_deadline(sender, instance, created, **kwargs):
    if created:
        # Only set deadline for newly created logs
        try:
            # Get the review period from settings
            settings = DateRestrictionSettings.objects.first()
            if settings and settings.doctor_review_enabled:
                # Calculate deadline based on creation date and review period
                review_period = settings.doctor_review_period
                instance.review_deadline = instance.created_at + timedelta(days=review_period)
                # Save without triggering the signal again
                StudentLogFormModel.objects.filter(pk=instance.pk).update(
                    review_deadline=instance.review_deadline
                )
        except Exception as e:
            print(f"Error setting review deadline: {e}")
            # Use default 30 days if there's an error
            instance.review_deadline = instance.created_at + timedelta(days=30)
            StudentLogFormModel.objects.filter(pk=instance.pk).update(
                review_deadline=instance.review_deadline
            )
