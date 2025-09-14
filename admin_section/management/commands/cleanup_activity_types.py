from django.core.management.base import BaseCommand
from admin_section.models import ActivityType, CoreDiaProSession
from django.db import transaction

class Command(BaseCommand):
    help = 'Cleanup duplicate ActivityType entries'

    def handle(self, *args, **options):
        self.stdout.write('Starting cleanup...')
        
        with transaction.atomic():
            # Get all ActivityTypes
            activity_types = ActivityType.objects.all()
            
            # Track processed combinations
            processed = set()
            
            for activity_type in activity_types:
                key = (activity_type.name, activity_type.department_id)
                
                if key in processed:
                    continue
                    
                # Find duplicates
                duplicates = ActivityType.objects.filter(
                    name=activity_type.name,
                    department=activity_type.department
                ).order_by('id')
                
                if duplicates.count() > 1:
                    # Keep the first one, delete the rest
                    primary = duplicates.first()
                    for duplicate in duplicates[1:]:
                        # Update any related CoreDiaProSessions to point to the primary
                        CoreDiaProSession.objects.filter(activity_type=duplicate).update(
                            activity_type=primary
                        )
                        duplicate.delete()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Merged duplicates for "{primary.name}" in department "{primary.department}"'
                        )
                    )
                
                processed.add(key)
        
        self.stdout.write(self.style.SUCCESS('Cleanup completed successfully'))
