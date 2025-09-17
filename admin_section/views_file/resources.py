from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from admin_section.models import CoreDiaProSession, ActivityType, Department
from django.db.models import Q
from django.db import transaction

class CoreDiaProSessionResource(resources.ModelResource):
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
        fields = ('name', 'activity_type', 'department')
        import_id_fields = ('name', 'activity_type', 'department')
        skip_unchanged = True
        report_skipped = True

    def before_import_row(self, row, **kwargs):
        activity_type_name = row.get('name', '').strip()
        department_name = row.get('department', '').strip()
        
        if not activity_type_name or not department_name:
            raise ValueError("Activity type and department are required")

        try:
            # Get department first
            department = Department.objects.get(name=department_name)
            
            # Use get_or_create instead of filter/create
            activity_type, created = ActivityType.objects.get_or_create(
                name=activity_type_name,
                department=department,
                defaults={'name': activity_type_name}
            )
            
            # Update row with the correct activity type name
            row['activity_type'] = activity_type.name
            row['department'] = department.name

        except Department.DoesNotExist:
            raise ValueError(f"Department '{department_name}' not found")
        except Exception as e:
            raise ValueError(f"Error processing row: {str(e)}")

    def skip_row(self, instance, original):
        # Skip if exact duplicate exists
        return CoreDiaProSession.objects.filter(
            name=instance.name,
            activity_type=instance.activity_type,
            department=instance.department
        ).exists()
