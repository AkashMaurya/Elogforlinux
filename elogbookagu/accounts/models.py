from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser


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
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="student")

    groups = models.ManyToManyField(
        "auth.Group", related_name="customuser_groups", blank=True
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission", related_name="customuser_permissions", blank=True
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def get_role_profile(self):
        if self.role == "doctor":
            return getattr(self, "doctor_profile", None)
        elif self.role == "student":
            return getattr(self, "student", None)
        elif self.role == "staff":
            return getattr(self, "staff_profile", None)
        return None

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = "admin"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} ({self.role}), {self.username}"


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
