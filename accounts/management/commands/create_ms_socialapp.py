from django.core.management.base import BaseCommand
from django.conf import settings
from decouple import config

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

class Command(BaseCommand):
    help = 'Create or update Microsoft SocialApp from environment variables'

    def handle(self, *args, **options):
        client_id = config('MICROSOFT_CLIENT_ID', default=None)
        client_secret = config('MICROSOFT_CLIENT_SECRET', default=None)
        if not client_id or not client_secret:
            self.stdout.write(self.style.ERROR('MICROSOFT_CLIENT_ID or MICROSOFT_CLIENT_SECRET not set in environment'))
            return

        site, _ = Site.objects.get_or_create(pk=settings.SITE_ID, defaults={'domain': 'elog.agu.edu.bh', 'name': 'ElogBook'})

        app, created = SocialApp.objects.update_or_create(
            provider='microsoft',
            defaults={
                'client_id': client_id,
                'secret': client_secret,
                'name': 'Microsoft Office 365',
            }
        )
        # Ensure the app is linked to the site
        app.sites.set([site])
        app.save()

        if created:
            self.stdout.write(self.style.SUCCESS('Created Microsoft SocialApp'))
        else:
            self.stdout.write(self.style.SUCCESS('Updated Microsoft SocialApp'))
