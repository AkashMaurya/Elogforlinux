from django.db import models
from django.utils import timezone
from accounts.models import Staff, CustomUser, Student
from student_section.models import StudentLogFormModel
from admin_section.models import Department, TrainingSite, Group

# Create your models here.

# Staff Support Ticket Model
class StaffSupportTicket(models.Model):
    # Basic info
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='support_tickets')
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
        verbose_name = "Staff Support Ticket"
        verbose_name_plural = "Staff Support Tickets"

    def __str__(self):
        return f"{self.staff.user.get_full_name()} - {self.subject} ({self.status})"

    def mark_as_solved(self, comments=''):
        self.status = 'solved'
        self.admin_comments = comments
        self.resolved_date = timezone.now()
        self.save()


# Notification Model for Staff
class StaffNotification(models.Model):
    recipient = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='notifications')
    log_entry = models.ForeignKey(StudentLogFormModel, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=100)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Staff Notification"
        verbose_name_plural = "Staff Notifications"

    def __str__(self):
        return f"{self.recipient.user.get_full_name()} - {self.title}"

    def mark_as_read(self):
        self.is_read = True
        self.save()


# Staff Emergency Attendance Model
class StaffEmergencyAttendance(models.Model):
    ATTENDANCE_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='staff_attendances')
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='marked_attendances')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='staff_attendances')
    training_site = models.ForeignKey(TrainingSite, on_delete=models.CASCADE, related_name='staff_attendances', null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='staff_attendances')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=ATTENDANCE_CHOICES)
    marked_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, help_text="Emergency attendance notes")
    is_emergency = models.BooleanField(default=True, help_text="Marks this as emergency attendance")

    class Meta:
        ordering = ['-date', '-marked_at']
        verbose_name = "Staff Emergency Attendance"
        verbose_name_plural = "Staff Emergency Attendances"
        unique_together = ['student', 'date', 'department']  # One emergency attendance record per student per day per department

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.date} - {self.status} (Emergency by {self.staff.user.get_full_name()})"

    @property
    def is_present(self):
        return self.status == 'present'

    @property
    def is_absent(self):
        return self.status == 'absent'
