from django.core.management.base import BaseCommand
from admin_section.models import ActivityType, CoreDiaProSession
from django.db.models import Count
from django.db import transaction

class Command(BaseCommand):
    help = 'Force cleanup of duplicate ActivityType entries'

    def handle(self, *args, **options):
        self.stdout.write('Starting cleanup...')
        
        with transaction.atomic():
            # Get groups of duplicates
            duplicates = ActivityType.objects.values('name', 'department').annotate(
                count=Count('id')
            ).filter(count__gt=1)

            for dup in duplicates:
                # Get all instances of this duplicate
                instances = ActivityType.objects.filter(
                    name=dup['name'],
                    department=dup['department']
                ).order_by('id')
                
                if instances.count() > 1:
                    # Keep the first one
                    primary = instances.first()
                    
                    # Update all related CoreDiaProSessions to point to the primary
                    for instance in instances[1:]:
                        CoreDiaProSession.objects.filter(
                            activity_type=instance
                        ).update(activity_type=primary)
                        
                        self.stdout.write(f'Deleting duplicate: {instance.name} (ID: {instance.id})')
                        instance.delete()
                        
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Merged duplicates for "{primary.name}" in department "{primary.department}"'
                        )
                    )

        self.stdout.write(self.style.SUCCESS('Cleanup completed successfully'))