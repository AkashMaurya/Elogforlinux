from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
# Change the import to use relative import
from .models import (
    LogYear,
    LogYearSection,
    Department,
    Group,
    TrainingSite,
    ActivityType,
    CoreDiaProSession,
    DateRestrictionSettings,
    AdminNotification,
    MappedAttendance
)



# Resource class for CoreDiaProSession (for import/export functionality)
class CoreDiaProSessionResource(resources.ModelResource):
    # ForeignKey fields mapped by name instead of ID
    activity_type = fields.Field(
        column_name='activity_type',
        attribute='activity_type',
        widget=ForeignKeyWidget(ActivityType, field='name')
    )
    department = fields.Field(
        column_name='department',
        attribute='department',
        widget=ForeignKeyWidget(Department, field='name')
    )

    class Meta:
        model = CoreDiaProSession
        fields = ("name", "activity_type", "department")
        import_id_fields = ("name",)  # Unique field for identifying records

    # Display names instead of IDs during export
    def dehydrate_activity_type(self, obj):
        return obj.activity_type.name if obj.activity_type else ''

    def dehydrate_department(self, obj):
        return obj.department.name if obj.department else ''


# Admin configuration for LogYear
@admin.register(LogYear)
class LogYearAdmin(admin.ModelAdmin):
    list_display = ("year_name",)
    search_fields = ("year_name",)
    ordering = ("year_name",)


# Admin configuration for LogYearSection
@admin.register(LogYearSection)
class LogYearSectionAdmin(admin.ModelAdmin):
    list_display = ("year_section_name", "year_name", "is_deleted")
    list_filter = ("year_name", "is_deleted")
    search_fields = ("year_section_name", "year_name__year_name")
    ordering = ("year_section_name",)


# Inline for ActivityType (to show in Department admin)
class ActivityTypeInline(admin.TabularInline):
    model = ActivityType
    extra = 1


# Admin configuration for Department
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "log_year", "log_year_section")
    list_filter = ("log_year", "log_year_section")
    search_fields = ("name", "log_year__year_name", "log_year_section__year_section_name")
    inlines = [ActivityTypeInline]  # Show ActivityType inline within Department
    ordering = ("name",)


# Admin configuration for Group
@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("group_name", "log_year", "log_year_section")
    list_filter = ("log_year", "log_year_section")
    search_fields = ("group_name", "log_year__year_name", "log_year_section__year_section_name")
    ordering = ("group_name",)


# Admin configuration for TrainingSite
@admin.register(TrainingSite)
class TrainingSiteAdmin(admin.ModelAdmin):
    list_display = ("name", "log_year")
    list_filter = ("log_year",)
    search_fields = ("name", "log_year__year_name")
    ordering = ("name",)


# Inline for CoreDiaProSession (to show in ActivityType admin)
class CoreDiaProSessionInline(admin.TabularInline):
    model = CoreDiaProSession
    extra = 1


# Admin configuration for ActivityType
@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "department")
    list_filter = ("department",)
    search_fields = ("name", "department__name")
    inlines = [CoreDiaProSessionInline]  # Show CoreDiaProSession inline within ActivityType
    ordering = ("name",)


# Admin configuration for CoreDiaProSession with Import/Export
@admin.register(CoreDiaProSession)
class CoreDiaProSessionAdmin(ImportExportModelAdmin):
    resource_class = CoreDiaProSessionResource  # Enables import/export functionality using the defined resource
    list_display = ("name", "activity_type", "department")  # Columns shown in the list view
    list_filter = ("activity_type", "department")  # Filters shown in the sidebar
    search_fields = ("name", "activity_type__name", "department__name")  # Fields searchable in the search bar
    ordering = ("name",)  # Default ordering of records


# Admin configuration for DateRestrictionSettings
@admin.register(DateRestrictionSettings)
class DateRestrictionSettingsAdmin(admin.ModelAdmin):
    list_display = ("past_days_limit", "allow_future_dates", "future_days_limit", "updated_at", "updated_by")
    readonly_fields = ("updated_at",)

    fieldsets = (
        ('Student Restrictions', {
            'fields': ('past_days_limit', 'allow_future_dates', 'future_days_limit')
        }),
        ('Audit', {
            'fields': ('updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# Admin configuration for AdminNotification
@admin.register(AdminNotification)
class AdminNotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'support_ticket_type', 'created_at', 'is_read')
    list_filter = ('is_read', 'support_ticket_type')
    search_fields = ('recipient__username', 'recipient__first_name', 'title', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Notification Information', {
            'fields': ('recipient', 'title', 'message', 'support_ticket_type', 'ticket_id')
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


# Admin configuration for MappedAttendance
@admin.register(MappedAttendance)
class MappedAttendanceAdmin(admin.ModelAdmin):
    list_display = ('name', 'training_site', 'log_year', 'log_year_section', 'get_doctors_count', 'get_groups_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'log_year', 'log_year_section', 'training_site')
    search_fields = ('name', 'training_site__name', 'log_year__year_name')
    filter_horizontal = ('doctors', 'groups')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'training_site', 'log_year', 'log_year_section', 'is_active')
        }),
        ('Mappings', {
            'fields': ('doctors', 'groups'),
            'description': 'Select doctors and groups to map to this training site'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_doctors_count(self, obj):
        return obj.doctors.count()
    get_doctors_count.short_description = 'Doctors Count'

    def get_groups_count(self, obj):
        return obj.groups.count()
    get_groups_count.short_description = 'Groups Count'
