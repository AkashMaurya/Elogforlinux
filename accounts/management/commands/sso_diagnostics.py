from django.core.management.base import BaseCommand
from django.conf import settings
from urllib.parse import urlparse
import os

from decouple import config

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site


def mask(s):
    if not s:
        return '<missing>'
    if len(s) <= 8:
        return '*******'
    return s[:4] + '...' + s[-4:]


class Command(BaseCommand):
    help = 'Run quick diagnostics for Microsoft SSO configuration (SocialApp, Site, redirect URI)'

    def handle(self, *args, **options):
        self.stdout.write('\n=== SSO DIAGNOSTICS ===\n')

        # Environment / settings
        ms_client_id = getattr(settings, 'MICROSOFT_CLIENT_ID', None) or os.environ.get('MICROSOFT_CLIENT_ID')
        ms_client_secret = getattr(settings, 'MICROSOFT_CLIENT_SECRET', None) or os.environ.get('MICROSOFT_CLIENT_SECRET')
        ms_redirect = getattr(settings, 'REDIRECT_URI', None) or os.environ.get('MICROSOFT_REDIRECT_URI')
        tenant = getattr(settings, 'TENANT_ID', None) or os.environ.get('TENANT_ID')

        self.stdout.write(f'MICROSOFT_CLIENT_ID: {mask(ms_client_id)}')
        self.stdout.write(f'MICROSOFT_CLIENT_SECRET: {mask(ms_client_secret)}')
        self.stdout.write(f'TENANT_ID: {mask(tenant)}')
        self.stdout.write(f'Configured REDIRECT_URI: {ms_redirect or "<not set>"}\n')

        # Parse host from redirect
        redirect_host = None
        if ms_redirect:
            try:
                parsed = urlparse(ms_redirect)
                redirect_host = parsed.hostname
                self.stdout.write(f'Parsed redirect host: {redirect_host} (scheme={parsed.scheme}, path={parsed.path})')
            except Exception as exc:
                self.stdout.write(f'Could not parse REDIRECT_URI: {exc}')

        # Sites framework
        try:
            site = Site.objects.get(pk=getattr(settings, 'SITE_ID', 1))
            self.stdout.write(f"Site (SITE_ID={settings.SITE_ID}): domain='{site.domain}', name='{site.name}'")
        except Exception as exc:
            self.stdout.write(f'Could not read Site for SITE_ID={getattr(settings, "SITE_ID", None)}: {exc}')

        # SocialApp entries
        apps = SocialApp.objects.filter(provider='microsoft')
        count = apps.count()
        self.stdout.write(f"SocialApp rows for provider='microsoft': {count}")
        for a in apps:
            site_domains = ','.join([s.domain for s in a.sites.all()])
            self.stdout.write(f" - id={a.id} name={a.name} client_id={mask(a.client_id)} sites=[{site_domains}]")

        # ALLOWED_HOSTS and CSRF
        allowed = getattr(settings, 'ALLOWED_HOSTS', [])
        self.stdout.write(f'ALLOWED_HOSTS: {allowed}')
        csrf = getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])
        self.stdout.write(f'CSRF_TRUSTED_ORIGINS: {csrf}\n')

        # Quick checks / suggestions
        self.stdout.write('--- Quick checks ---')
        if not ms_client_id or not ms_client_secret:
            self.stdout.write(' * ERROR: MICROSOFT client id/secret not set. Run: python manage.py create_ms_socialapp after setting env vars')
        else:
            self.stdout.write(' * OK: microsoft client id/secret appear set')

        if count == 0:
            self.stdout.write(' * WARNING: No SocialApp for provider "microsoft" found in the DB. Run: python manage.py create_ms_socialapp')
        elif count > 1:
            self.stdout.write(' * NOTICE: Multiple SocialApp rows found. The CustomSocialAccountAdapter prefers a site-linked app, but duplicate rows can confuse the flow.')

        if redirect_host and site and redirect_host != getattr(site, 'domain', None):
            self.stdout.write(f" * MISMATCH: Redirect host '{redirect_host}' does not match Site.domain '{site.domain}'. Azure redirect must match exactly the URL your app sends to Microsoft.")

        if redirect_host and redirect_host not in allowed:
            self.stdout.write(f" * WARNING: Redirect host '{redirect_host}' not in ALLOWED_HOSTS; this may cause DisallowedHost on callback.")

        self.stdout.write('\n--- Suggested next steps ---')
        self.stdout.write(' 1) Ensure the Redirect URI registered in Azure exactly matches the callback URL:')
        self.stdout.write('    e.g. https://elog.agu.edu.bh/accounts/microsoft/login/callback/')
        self.stdout.write(' 2) Ensure MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, TENANT_ID and MICROSOFT_REDIRECT_URI are set in the production environment')
        self.stdout.write(' 3) Run: python manage.py create_ms_socialapp  (this will create/update the SocialApp and attach it to the current Site)')
        self.stdout.write(' 4) Verify Site.domain matches your public host and that host is listed in ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS')
        self.stdout.write(' 5) Check server time (ntp) and ensure HTTPS/SSL termination passes X-Forwarded-Proto correctly if behind a proxy')

        self.stdout.write('\nDone. If callback still fails, enable DEBUG logging and post relevant logs from sso-debug.log (it is located at the project root).')
