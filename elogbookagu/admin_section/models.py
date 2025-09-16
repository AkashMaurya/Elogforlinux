from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.urls import reverse
from accounts.models import CustomUser

# LogYear Model
class LogYear(models.Model):
    year_name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.year_name

# LogYearSection Model
class LogYearSection(models.Model):
    year_section_name = models.CharField(max_length=20)
    year_name = models.ForeignKey(LogYear, on_delete=models.CASCADE, related_name="log_year_sections")
    is_deleted = models.BooleanField(default=False)

    # Validation moved to LogYearSectionForm to avoid duplication

    def __str__(self):
        return self.year_section_name

# Department Model
class Department(models.Model):
    name = models.CharField(max_length=50)
    log_year = models.ForeignKey(LogYear, on_delete=models.CASCADE, related_name="department_log_year")
    log_year_section = models.ForeignKey(
        LogYearSection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="department_log_year_section",
        db_index=True,
    )
    
    def __str__(self):
        return f"{self.name}"

# Group Model
class Group(models.Model):
    group_name = models.CharField(max_length=50)
    log_year = models.ForeignKey(LogYear, on_delete=models.CASCADE, related_name="groups_log_year")
    log_year_section = models.ForeignKey(
        LogYearSection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="groups_log_year_section",
    )

    def __str__(self):
        return f"{self.group_name} ({self.log_year.year_name}) - {self.log_year_section.year_section_name if self.log_year_section else 'No Section'}"

# TrainingSite Model
class TrainingSite(models.Model):
    name = models.CharField(max_length=100, unique=True)
    log_year = models.ForeignKey(LogYear, on_delete=models.CASCADE, related_name='training_sites')

    def __str__(self):
        return f"{self.name} ({self.log_year})"

# ActivityType Model
class ActivityType(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="activity_types")

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ["name", "department"]

# CoreDiaProSession Model
class CoreDiaProSession(models.Model):
    name = models.CharField(max_length=200)
    activity_type = models.ForeignKey(ActivityType, on_delete=models.CASCADE, related_name="core_dia_pro_sessions")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="core_dia_pro_sessions")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Core Diagnosis Procedure Session"
        verbose_name_plural = "Core Diagnosis Procedure Sessions"


# Date Restriction Settings Model
class DateRestrictionSettings(models.Model):
    # Original fields (for backward compatibility)
    past_days_limit = models.PositiveIntegerField(
        default=7,
        help_text="Maximum number of days in the past a student can select"
    )
    allow_future_dates = models.BooleanField(
        default=False,
        help_text="Whether students can select future dates"
    )
    future_days_limit = models.PositiveIntegerField(
        default=0,
        help_text="Maximum number of days in the future a student can select (if future dates are allowed)"
    )

    # Last updated timestamp
    updated_at = models.DateTimeField(auto_now=True)

    # Updated by
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='date_restriction_updates'
    )

    # Doctor review period settings
    doctor_review_period = models.PositiveIntegerField(
        default=30,
        help_text="Number of days doctors have to review student logs"
    )
    doctor_review_enabled = models.BooleanField(
        default=True,
        help_text="Whether to enforce the review period deadline"
    )
    doctor_notification_days = models.PositiveIntegerField(
        default=3,
        help_text="Number of days before deadline to send notification to doctors"
    )

    # Specific days of week settings (for reference)
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    class Meta:
        verbose_name = "Date Restriction Setting"
        verbose_name_plural = "Date Restriction Settings"

    def __str__(self):
        return f"Date Restrictions (Past: {self.past_days_limit} days, Future: {'Allowed' if self.allow_future_dates else 'Not Allowed'})"

    # Properties for student settings
    @property
    def student_past_days_limit(self):
        return self.past_days_limit

    @property
    def student_allow_future_dates(self):
        return self.allow_future_dates

    @property
    def student_future_days_limit(self):
        return self.future_days_limit

    # Doctor settings
    doctor_past_days_limit = models.PositiveIntegerField(
        default=30,
        help_text="Maximum number of days in the past a doctor can review logs"
    )
    doctor_allow_future_dates = models.BooleanField(
        default=False,
        help_text="Whether doctors can review future-dated logs"
    )
    doctor_future_days_limit = models.PositiveIntegerField(
        default=0,
        help_text="Maximum number of days in the future a doctor can review logs (if future dates are allowed)"
    )

    # Allowed days settings
    allowed_days_for_students = models.CharField(
        max_length=20,
        default='0,1,2,3,4,5,6',
        help_text="Comma-separated list of allowed days of week for students (0=Monday, 6=Sunday)"
    )
    allowed_days_for_doctors = models.CharField(
        max_length=20,
        default='0,1,2,3,4,5,6',
        help_text="Comma-separated list of allowed days of week for doctors (0=Monday, 6=Sunday)"
    )

    # Active status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether date restrictions are active"
    )

    # Attendance tracking settings
    attendance_tracking_enabled = models.BooleanField(
        default=True,
        help_text="Whether doctors can track student attendance"
    )

    # Helper methods for getting allowed days as lists
    def get_allowed_days_for_students(self):
        return [int(day) for day in self.allowed_days_for_students.split(',') if day.strip()]

    def get_allowed_days_for_doctors(self):
        return [int(day) for day in self.allowed_days_for_doctors.split(',') if day.strip()]

# Admin Notification Model
class AdminNotification(models.Model):
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='admin_notifications', limit_choices_to={'role': 'admin'})
    title = models.CharField(max_length=100)
    message = models.TextField()
    support_ticket_type = models.CharField(max_length=20, choices=[
        ('student', 'Student Support'),
        ('doctor', 'Doctor Support'),
        ('staff', 'Staff Support')
    ])
    ticket_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Admin Notification"
        verbose_name_plural = "Admin Notifications"

    def __str__(self):
        return f"{self.recipient.get_full_name()} - {self.title}"

    def mark_as_read(self):
        self.is_read = True
        self.save()


# Blog Model
class Blog(models.Model):
    CATEGORY_CHOICES = [
        ('news', 'News'),
        ('announcement', 'Announcement'),
        ('feature', 'Feature'),
        ('update', 'Update'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    summary = models.CharField(max_length=300, help_text="A brief summary of the blog post (max 300 characters)")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='news')
    attachment = models.FileField(upload_to='blog_attachments/', null=True, blank=True)
    attachment_name = models.CharField(max_length=100, blank=True, help_text="Name to display for the attachment")
    featured_image = models.ImageField(upload_to='blog_images/', null=True, blank=True)
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='blogs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('admin_section:blog_detail', args=[str(self.id)])

    def get_attachment_name(self):
        """Returns the attachment name or the filename if no name is provided"""
        if self.attachment_name:
            return self.attachment_name
        elif self.attachment:
            return self.attachment.name.split('/')[-1]
        return None


# Mapped Attendance Model
class MappedAttendance(models.Model):
    name = models.CharField(max_length=100, help_text="Name for this attendance mapping")
    training_site = models.ForeignKey(TrainingSite, on_delete=models.CASCADE, related_name='mapped_attendances')
    doctors = models.ManyToManyField('accounts.Doctor', blank=True, related_name='mapped_attendances')
    groups = models.ManyToManyField(Group, blank=True, related_name='mapped_attendances')
    log_year = models.ForeignKey(LogYear, on_delete=models.CASCADE, related_name='mapped_attendances')
    log_year_section = models.ForeignKey(
        LogYearSection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mapped_attendances'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Mapped Attendance"
        verbose_name_plural = "Mapped Attendances"
        unique_together = ['name', 'training_site', 'log_year']

    def __str__(self):
        return f"{self.name} - {self.training_site.name} ({self.log_year.year_name})"

    def get_doctors_list(self):
        """Get comma-separated list of mapped doctors"""
        doctors = [doctor.user.get_full_name() or doctor.user.username for doctor in self.doctors.all()]
        return ", ".join(doctors) if doctors else "No Doctors Mapped"

    def get_groups_list(self):
        """Get comma-separated list of mapped groups"""
        groups = [group.group_name for group in self.groups.all()]
        return ", ".join(groups) if groups else "No Groups Mapped"

    def get_students_count(self):
        """Get total count of students in mapped groups"""
        from accounts.models import Student
        return Student.objects.filter(group__in=self.groups.all()).count()
