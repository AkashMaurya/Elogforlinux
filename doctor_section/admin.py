from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import DoctorSupportTicket, Notification, StudentAttendance

# Register your models here.

@admin.register(DoctorSupportTicket)
class DoctorSupportTicketAdmin(ImportExportModelAdmin):
    list_display = ('doctor', 'subject', 'date_created', 'status')
    list_filter = ('status',)
    search_fields = ('doctor__user__username', 'doctor__user__first_name', 'subject', 'description')
    readonly_fields = ('date_created', 'resolved_date')
    date_hierarchy = 'date_created'

    fieldsets = (
        ('Ticket Information', {
            'fields': ('doctor', 'subject', 'description')
        }),
        ('Status', {
            'fields': ('status', 'admin_comments', 'resolved_date')
        }),
        ('Timestamps', {
            'fields': ('date_created',),
            'classes': ('collapse',)
        }),
    )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
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


@admin.register(StudentAttendance)
class StudentAttendanceAdmin(ImportExportModelAdmin):
    list_display = ('student', 'doctor', 'training_site', 'group', 'date', 'status', 'marked_at')
    list_filter = ('status', 'date', 'training_site', 'group')
    search_fields = ('student__user__username', 'student__user__first_name', 'student__student_id', 'doctor__user__username')
    readonly_fields = ('marked_at', 'updated_at')
    date_hierarchy = 'date'

    fieldsets = (
        ('Attendance Information', {
            'fields': ('student', 'doctor', 'training_site', 'group', 'date', 'status')
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
        return super().get_queryset(request).select_related('student__user', 'doctor__user', 'training_site', 'group')
