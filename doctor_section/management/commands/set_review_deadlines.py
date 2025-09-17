from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from student_section.models import StudentLogFormModel
from admin_section.models import DateRestrictionSettings


class Command(BaseCommand):
    help = 'Set review deadlines for existing logs that do not have them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Update all logs, even those that already have a deadline',
        )

    def handle(self, *args, **options):
        # Get settings
        settings = DateRestrictionSettings.objects.first()
        if not settings:
            self.stdout.write(self.style.ERROR('Date restriction settings not found. Creating default settings.'))
            settings = DateRestrictionSettings.objects.create(
                doctor_review_period=30,
                doctor_review_enabled=True,
                doctor_notification_days=3
            )
        
        # Get review period from settings
        review_period = settings.doctor_review_period
        
        # Get logs that need deadlines
        if options['all']:
            logs = StudentLogFormModel.objects.all()
            self.stdout.write(self.style.WARNING(f'Updating ALL logs ({logs.count()}) with review deadlines'))
        else:
            logs = StudentLogFormModel.objects.filter(review_deadline__isnull=True)
            self.stdout.write(self.style.WARNING(f'Setting review deadlines for {logs.count()} logs without deadlines'))
        
        # Set deadlines
        count = 0
        for log in logs:
            # Calculate deadline based on creation date and review period
            log.review_deadline = log.created_at + timedelta(days=review_period)
            log.save(update_fields=['review_deadline'])
            count += 1
            
            # Print progress every 100 logs
            if count % 100 == 0:
                self.stdout.write(self.style.SUCCESS(f'Processed {count} logs...'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully set review deadlines for {count} logs'))
