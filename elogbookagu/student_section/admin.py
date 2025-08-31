from django.contrib import admin
from .models import StudentLogFormModel, SupportTicket, StudentNotification
from import_export.admin import ImportExportModelAdmin



@admin.register(StudentLogFormModel)
class StudentLogFormAdmin(ImportExportModelAdmin):
    list_display = ('student', 'date', 'department', 'activity_type', 'is_reviewed', 'get_status')
    list_filter = ('is_reviewed', 'department', 'log_year', 'log_year_section', 'group')
    search_fields = ('student__user__username', 'student__user__first_name', 'patient_id', 'description')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'date'

    fieldsets = (
        ('Basic Information', {
            'fields': ('student', 'date', 'patient_id')
        }),
        ('Academic Details', {
            'fields': ('log_year', 'log_year_section', 'group')
        }),
        ('Department & Supervision', {
            'fields': ('department', 'tutor', 'training_site')
        }),
        ('Activity Information', {
            'fields': ('activity_type', 'core_diagnosis', 'participation_type', 'description')
        }),
        ('Review Status', {
            'fields': ('is_reviewed', 'review_date', 'reviewer_comments')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SupportTicket)
class SupportTicketAdmin(ImportExportModelAdmin):
    list_display = ('student', 'subject', 'date_created', 'status')
    list_filter = ('status',)
    search_fields = ('student__user__username', 'student__user__first_name', 'subject', 'description')
    readonly_fields = ('date_created', 'resolved_date')
    date_hierarchy = 'date_created'

    fieldsets = (
        ('Ticket Information', {
            'fields': ('student', 'subject', 'description')
        }),
        ('Status', {
            'fields': ('status', 'admin_comments', 'resolved_date')
        }),
        ('Timestamps', {
            'fields': ('date_created',),
            'classes': ('collapse',)
        }),
    )


@admin.register(StudentNotification)
class StudentNotificationAdmin(admin.ModelAdmin):
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
