from django.contrib import admin
from .models import StaffSupportTicket, StaffNotification, StaffEmergencyAttendance

# Register your models here.
@admin.register(StaffSupportTicket)
class StaffSupportTicketAdmin(admin.ModelAdmin):
    list_display = ('subject', 'staff', 'date_created', 'status')
    list_filter = ('status',)
    search_fields = ('subject', 'description', 'staff__user__username', 'staff__user__first_name')
    readonly_fields = ('date_created',)
    date_hierarchy = 'date_created'

    fieldsets = (
        ('Ticket Information', {
            'fields': ('staff', 'subject', 'description', 'date_created')
        }),
        ('Status', {
            'fields': ('status', 'admin_comments', 'resolved_date')
        }),
    )


@admin.register(StaffNotification)
class StaffNotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'created_at', 'is_read')
    list_filter = ('is_read',)
    search_fields = ('recipient__user__username', 'recipient__user__first_name', 'title', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Notification Information', {
            'fields': ('recipient', 'log_entry', 'title', 'message')
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(StaffEmergencyAttendance)
class StaffEmergencyAttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'staff', 'department', 'training_site', 'date', 'status', 'is_emergency', 'marked_at')
    list_filter = ('status', 'is_emergency', 'date', 'department', 'training_site')
    search_fields = ('student__user__username', 'student__user__first_name', 'student__student_id', 'staff__user__username')
    readonly_fields = ('marked_at', 'updated_at')
    date_hierarchy = 'date'

    fieldsets = (
        ('Emergency Attendance Information', {
            'fields': ('student', 'staff', 'department', 'training_site', 'group', 'date', 'status', 'is_emergency')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('marked_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student__user', 'staff__user', 'department', 'training_site', 'group')
