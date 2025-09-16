from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser, UserManager


class CustomUserManager(UserManager):
    """Custom manager to handle soft-deleted users"""

    def get_queryset(self):
        """By default, exclude soft-deleted users"""
        return super().get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        """Get all users including soft-deleted ones"""
        return super().get_queryset()

    def deleted_only(self):
        """Get only soft-deleted users"""
        return super().get_queryset().filter(is_deleted=True)


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    profile_photo = models.ImageField(
        upload_to="profiles/", blank=True, null=True, default="profiles/default.jpg"
    )
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    phone_no = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    speciality = models.CharField(max_length=100, blank=True)
    ROLE_CHOICES = (
        ("student", "Student"),
        ("doctor", "Doctor"),
        ("staff", "Staff"),
        ("admin", "Admin"),
    )
    # Default to 'pending' so newly created accounts (including SSO) are inactive
    # until an admin approves or updates their role. The welcome page will be
    # shown to pending users.
    ROLE_CHOICES = (
        ("defaultuser", "Default User"),
        ("student", "Student"),
        ("doctor", "Doctor"),
        ("staff", "Staff"),
        ("admin", "Admin"),
        ("pending", "Pending"),
    )

    # New SSO users will default to `defaultuser` so they land on the
    # `/defaultuser/` section until an admin updates their role.
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default="defaultuser")

    # Soft delete fields
    is_deleted = models.BooleanField(default=False, help_text="Soft delete flag - user is hidden but data preserved")
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="When the user was soft deleted")
    deleted_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_users',
        help_text="Admin who performed the soft delete"
    )

    groups = models.ManyToManyField(
        "auth.Group", related_name="customuser_groups", blank=True
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission", related_name="customuser_permissions", blank=True
    )

    # Custom manager
    objects = CustomUserManager()
    all_objects = models.Manager()  # Access to all users including deleted

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def get_role_profile(self):
        if self.role == "doctor":
            return getattr(self, "doctor_profile", None)
        elif self.role == "student":
            return getattr(self, "student", None)
        elif self.role == "staff":
            return getattr(self, "staff_profile", None)
        # Pending/admin or other roles don't have a profile
        return None

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = "admin"
        super().save(*args, **kwargs)

    def soft_delete(self, deleted_by=None):
        """Soft delete the user - hide from normal queries but preserve data"""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by
        self.is_active = False  # Also deactivate the account
        self.save()

        # Invalidate sessions to force logout
        from .signals import invalidate_user_sessions
        invalidate_user_sessions(self)

    def restore(self):
        """Restore a soft-deleted user"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.is_active = True
        self.save()

    def remove_role(self, role_to_remove):
        """Safely remove a role from user without deleting the user account"""
        if self.role == role_to_remove:
            # Remove the role-specific profile but keep the user
            try:
                if role_to_remove == 'student' and hasattr(self, 'student'):
                    self.student.delete()
                elif role_to_remove == 'doctor' and hasattr(self, 'doctor_profile'):
                    self.doctor_profile.delete()
                elif role_to_remove == 'staff' and hasattr(self, 'staff_profile'):
                    self.staff_profile.delete()
            except Exception as e:
                # Profile might already be deleted, continue
                pass

            # Change role to defaultuser
            self.role = 'defaultuser'
            self.save()
            return True
        return False

    def add_role(self, new_role):
        """Safely add a role to user"""
        if new_role in ['student', 'doctor', 'staff', 'admin']:
            self.role = new_role
            self.save()
            # The signal will create the appropriate profile
            return True
        return False

    def __str__(self):
        deleted_indicator = " [DELETED]" if self.is_deleted else ""
        return f"{self.email} ({self.role}), {self.username}{deleted_indicator}"

    def get_redirect_path(self):
        """Return the URL path to redirect the user to based on role.

        This is a convenience used by views/adapters to centralise the
        role-to-section mapping.
        """
        mapping = {
            "defaultuser": "/defaultuser/",
            "student": "/student_section/",
            "staff": "/staff_section/",
            "doctor": "/doctor_section/",
            "admin": "/admin_section/",
        }
        return mapping.get(self.role, "/")


class SSOAuditLog(models.Model):
    """A simple audit log for changes applied to users by SSO flows.

    Records which fields were changed, the provider that caused the change
    and a timestamp. This helps admins review what SSO modified.
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sso_audit_logs')
    provider = models.CharField(max_length=50, blank=True)
    changed_fields = models.JSONField(default=dict)  # {field_name: [old, new]}
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SSOAudit(user={self.user.email},provider={self.provider},ts={self.timestamp})"


class SSOState(models.Model):
    """Optional server-side backup of allauth state used during the
    OAuth redirect round-trip.

    In some environments browsers may not send the session cookie during
    the cross-site callback. To make login resilient we store a minimal
    copy of the allauth state keyed by the `state_id` generated by
    `statekit.stash_state`. The callback middleware will restore the
    state into the session if the session is missing the expected keys.
    """
    state_id = models.CharField(max_length=255, unique=True, db_index=True)
    payload = models.JSONField(default=dict)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SSOState(state_id={self.state_id},created={self.created})"


class Student(models.Model):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="student"
    )
    student_id = models.CharField(max_length=30, unique=True)
    group = models.ForeignKey(
        "admin_section.Group",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )

    def __str__(self):
        return f"{self.user.email} - {self.student_id} ({self.group if self.group else 'No Group'})"


class Doctor(models.Model):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="doctor_profile"
    )
    departments = models.ManyToManyField(
        "admin_section.Department", related_name="doctors", blank=True
    )

    def __str__(self):
        return self.user.username

    def get_departments(self):
        departments = [department.name for department in self.departments.all()]
        return ", ".join(departments) if departments else "No Departments"


class Staff(models.Model):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="staff_profile"
    )
    departments = models.ManyToManyField("admin_section.Department")

    def get_departments(self):
        departments = [department.name for department in self.departments.all()]
        return ", ".join(departments) if departments else "No Departments"

    def __str__(self):
        return self.user.username
