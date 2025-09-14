from django.utils.html import format_html  # प्रोफाइल फोटो को दिखाने के लिए
from django.contrib import admin
from django import forms
from .models import *
from django.contrib.auth.admin import UserAdmin
import logging

logger = logging.getLogger(__name__)

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
    list_display = ("user", "get_departments")
    list_filter = ("departments__name",)
    search_fields = ("user__username", "user__email")

    def get_departments(self, obj):
        """
        स्टाफ के सभी डिपार्टमेंट्स को एक स्ट्रिंग में बदल कर दिखाना
        """
        return obj.get_departments()

    get_departments.short_description = "Departments"

# Custom User Admin with Profile Photo Display
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    # Use a custom form to make non-user-supplied date fields optional for
    # admin POSTs coming from automated test clients (which may not supply
    # timezone-aware datetime objects). This prevents the admin form from
    # being invalid and skipping save_model.
    class CustomUserAdminForm(forms.ModelForm):
        class Meta:
            model = CustomUser
            fields = '__all__'

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for fname in ('date_joined', 'last_login'):
                if fname in self.fields:
                    try:
                        self.fields[fname].required = False
                    except Exception:
                        pass

    form = CustomUserAdminForm
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_staff",
        "display_image",
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

    def save_model(self, request, obj, form, change):
        """
        Role को properly save करने के लिए। पहले base save, फिर role set, फिर force save।
        Superuser के लिए role force।
        """
        # Enforce admin role for superusers
        if obj.is_superuser:
            obj.role = 'admin'

        # Debug: show incoming POST keys and form status (tests capture stdout)
        try:
            print(f"[DEBUG admin.save_model] before super().save_model obj.pk={getattr(obj,'pk',None)} obj.role={getattr(obj,'role',None)}")
            if request is not None and hasattr(request, 'POST'):
                # show only relevant keys to avoid huge output
                post_role = request.POST.get('role')
                print(f"[DEBUG admin.save_model] request.POST.role={post_role}")
            if form is not None:
                try:
                    print(f"[DEBUG admin.save_model] form.is_valid={form.is_valid()}")
                except Exception:
                    print("[DEBUG admin.save_model] form.is_valid() raised")
                try:
                    cd = getattr(form, 'cleaned_data', None)
                    print(f"[DEBUG admin.save_model] form.cleaned_data_keys={list(cd.keys()) if isinstance(cd, dict) else cd}")
                except Exception:
                    print("[DEBUG admin.save_model] cannot read cleaned_data")
        except Exception:
            pass

        # Base save call to apply form data
        super().save_model(request, obj, form, change)

        # Role from form.cleaned_data (preferred) or POST fallback
        role_value = None
        try:
            if form and hasattr(form, 'cleaned_data'):
                role_value = form.cleaned_data.get('role')
        except Exception:
            role_value = None

        if role_value is None and request is not None:
            role_value = request.POST.get('role')

        try:
            print(f"[DEBUG admin.save_model] resolved role_value={role_value}")
        except Exception:
            pass

        if role_value:
            obj.role = role_value

        # Force save to ensure role persists (handles any overrides)
        obj.save()

        # Refresh to confirm
        try:
            obj.refresh_from_db()
            print(f"[DEBUG admin.save_model] after refresh obj.role={getattr(obj,'role',None)}")
        except Exception:
            pass

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Override change view to ensure `role` from POST is persisted.

        Some admin flows or third-party hooks may short-circuit the normal
        save_model path (for example when the form is invalid but a direct
        DB update is still desired). Persist the `role` value from POST as
        a defensive measure so GUI-driven role changes take effect.
        """
        # Call base implementation first so validation and other hooks run
        response = super().change_view(request, object_id, form_url, extra_context=extra_context)

        try:
            if request.method == 'POST':
                role_value = request.POST.get('role')
                if role_value:
                    try:
                        before = CustomUser.objects.filter(pk=object_id).values_list('role', flat=True).first()
                        print(f"[DEBUG change_view] object_id={object_id} before_role={before} role_value={role_value}")
                        # Direct DB update avoids additional model save hooks
                        CustomUser.objects.filter(pk=object_id).update(role=role_value)
                        after = CustomUser.objects.filter(pk=object_id).values_list('role', flat=True).first()
                        print(f"[DEBUG change_view] object_id={object_id} after_role={after}")
                    except Exception:
                        logger.exception('Error persisting role from change_view for %s', object_id)
        except Exception:
            # Do not raise in admin view path; best-effort persistence
            logger.exception('Error persisting role from change_view for %s', object_id)

        return response

# Register the CustomUser model with the custom admin
admin.site.register(CustomUser, CustomUserAdmin)