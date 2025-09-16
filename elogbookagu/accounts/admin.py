from django.utils.html import format_html  # प्रोफाइल फोटो को दिखाने के लिए
from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("user", "student_id", "group")
    list_filter = ("group",)
    search_fields = (
        "user__username",
        "user__email",
        "student_id",
    )  # ईमेल से भी सर्च कर सकते हैं


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("user", "get_departments")
    list_filter = ("departments__name",)
    search_fields = ("user__username", "user__email")

    def get_departments(self, obj):
        """
        डॉक्टर के सभी डिपार्टमेंट्स को एक स्ट्रिंग में बदल कर दिखाना
        """
        return obj.get_departments()

    get_departments.short_description = "Departments"


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("user","get_departments")
    list_filter = ("departments__name",)
    search_fields = ("user__username", "user__email")


# Custom User Admin with Profile Photo Display
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_staff",
        "profile_photo",
    )
    list_filter = (
        "role",
        "is_staff",
        "is_superuser",
    )
    search_fields = (
        "username",
        "email",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "email",
                    "password",
                    "role",
                    "profile_photo",
                    "city",
                    "country",
                    "phone_no",
                    "bio",
                    "speciality",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "profile_photo",
                )
            },
        ),
    )

    def display_image(self, obj):
        """
        एडमिन पैनल में यूज़र की प्रोफाइल फोटो को थंबनेल के रूप में दिखाने के लिए।
        """
        if obj.profile_photo:
            return format_html(
                '<img src="{}" width="40" height="40" style="border-radius:50%;" />',
                obj.profile_photo.url,
            )
        return "No Image"

    display_image.short_description = "Profile Photo"


# Register the CustomUser model with the custom admin
admin.site.register(CustomUser, CustomUserAdmin)
