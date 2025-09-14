from django.core.management.base import BaseCommand
from django.conf import settings
from urllib.parse import urlparse

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp


class Command(BaseCommand):
    help = 'Fix Site.domain to match MICROSOFT_REDIRECT_URI host and attach Microsoft SocialApp to it'

    def handle(self, *args, **options):
        redirect = getattr(settings, 'REDIRECT_URI', None)
        if not redirect:
            self.stdout.write(self.style.ERROR('REDIRECT_URI (MICROSOFT_REDIRECT_URI) not set in settings'))
            return

        try:
            parsed = urlparse(redirect)
            host = parsed.hostname
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Could not parse REDIRECT_URI: {exc}'))
            return

        site_id = getattr(settings, 'SITE_ID', 1)
        site, created = Site.objects.get_or_create(pk=site_id)
        old_domain = site.domain
        site.domain = host
        site.name = host
        site.save()

        self.stdout.write(self.style.SUCCESS(f'Updated Site id={site_id} domain: {old_domain} -> {site.domain}'))

        apps = SocialApp.objects.filter(provider='microsoft')
        if not apps.exists():
            self.stdout.write(self.style.WARNING('No SocialApp with provider "microsoft" found. Run create_ms_socialapp first.'))
            return

        app = apps.first()
        app.sites.set([site])
        app.save()
        self.stdout.write(self.style.SUCCESS(f'Attached SocialApp id={app.id} name="{app.name}" to Site {site.domain}'))
