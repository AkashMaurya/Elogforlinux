from django.contrib import admin
from .models import DoctorConfig

@admin.register(DoctorConfig)
class DoctorConfigAdmin(admin.ModelAdmin):
    list_display = ('enable_attendance_tracking',)
    list_editable = ('enable_attendance_tracking',)