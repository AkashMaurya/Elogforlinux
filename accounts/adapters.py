import logging
from urllib.parse import urlparse
from django.core.exceptions import MultipleObjectsReturned
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db import DatabaseError
from django.db.utils import ProgrammingError
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse

User = get_user_model()
logger = logging.getLogger(__name__)
ssolog = logging.getLogger('sso_debug')


def _safe_next(request, url):
    """Return the `url` if it's a safe host-level redirect and not a
    provider/internal path; otherwise return None.

    Rules:
    - Must pass `url_has_allowed_host_and_scheme` for current host and scheme.
    - Path must not contain '3rdparty', 'socialaccount' or start with
      '/accounts/microsoft'.
    - Must not be the login path.
    """
    if not url:
        return None
    try:
        login_path = reverse('login')
    except Exception:
        login_path = getattr(settings, 'LOGIN_URL', '/login/')

    parsed = urlparse(url)
    path = parsed.path or ''
    # provider/internal detection
    is_provider_path = ('3rdparty' in path) or ('socialaccount' in path) or path.startswith('/accounts/microsoft')
    is_allowed = url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}, require_https=request.is_secure())
    if is_allowed and not is_provider_path and not (url == login_path or url.endswith('/login/') or url == getattr(settings, 'LOGIN_URL', '/login/')):
        return url
    return None


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Social adapter that links by email and enforces central post-login
    redirect handling.
    """

    def get_app(self, request, provider, *args, **kwargs):
        try:
            return super().get_app(request, provider, *args, **kwargs)
        except Exception:
            # Fall back to default behaviour; the parent handles MultipleObjects
            from allauth.socialaccount.models import SocialApp

            apps = SocialApp.objects.filter(provider=provider)
            site_apps = apps.filter(sites__id=getattr(settings, 'SITE_ID', None))
            if site_apps.exists():
                return site_apps.first()
            return apps.first()

    def pre_social_login(self, request, sociallogin):
        email = getattr(sociallogin.user, 'email', None)
        if not email:
            ssolog.warning('pre_social_login: missing email; redirecting to welcome')
            raise ImmediateHttpResponse(redirect('accounts_welcome'))

        try:
            existing = User.objects.filter(email__iexact=email).first()
            ssolog.debug('pre_social_login: existing=%s for email=%s', getattr(existing, 'pk', None), email)
            if existing:
                sociallogin.state['process'] = 'connect'
                try:
                    sociallogin.connect(request, existing)
                    ssolog.info('pre_social_login: connected social to existing user pk=%s', existing.pk)
                except Exception:
                    logger.exception('pre_social_login: failed to connect social to existing user %s', email)
                if getattr(existing, 'role', None) == 'pending':
                    ssolog.info('pre_social_login: existing user pending; redirecting to welcome')
                    raise ImmediateHttpResponse(redirect('accounts_welcome'))
        except Exception:
            logger.exception('pre_social_login: exception while linking social account for %s', email)

    def get_login_redirect_url(self, request, socialaccount=None):
        """Return safe `next` when appropriate, otherwise defer to
        `LOGIN_REDIRECT_URL` which should point to `/accounts/post-login-redirect/`.

        This function always re-loads the authenticated user from the DB so
        admin role changes take effect immediately after they log in.
        """
        # Prefer authenticated user, but fall back to socialaccount.user
        user = getattr(request, 'user', None)
        socialaccount_user = socialaccount.user if socialaccount else None

        ssolog.debug('social.get_login_redirect_url: CALLED with request.user=%s socialaccount.user=%s',
                    getattr(user, 'pk', None), getattr(socialaccount_user, 'pk', None))

        if user and getattr(user, 'is_authenticated', False):
            try:
                user = type(user).objects.filter(pk=user.pk).first() or user
            except Exception:
                pass
        else:
            if socialaccount and getattr(socialaccount, 'user', None):
                try:
                    su = socialaccount.user
                    user = type(su).objects.filter(pk=su.pk).first() or su
                except Exception:
                    user = socialaccount.user

        next_url = request.GET.get('next') or request.POST.get('next')
        ssolog.debug('social.get_login_redirect_url: user=%s next=%s', getattr(user, 'pk', None), next_url)
        safe = _safe_next(request, next_url)
        if safe:
            ssolog.debug('social.get_login_redirect_url: returning safe next=%s', safe)
            return safe

        redirect_url = getattr(settings, 'LOGIN_REDIRECT_URL', '/')
        ssolog.debug('social.get_login_redirect_url: deferring to LOGIN_REDIRECT_URL=%s for user=%s', redirect_url, getattr(user, 'pk', None))
        return redirect_url

    def get_connect_redirect_url(self, request, socialaccount):
        """Override the redirect URL for social account connections.

        This method is called when a social account is connected to an existing user.
        The key issue is that allauth connects the account but doesn't log the user in.
        We need to manually log them in before redirecting.
        """
        user = socialaccount.user
        ssolog.debug('social.get_connect_redirect_url: CALLED for user=%s', getattr(user, 'pk', None))

        # The user exists and the social account is connected, but they're not logged in
        # We need to manually log them in
        try:
            from django.contrib.auth import login
            login(request, user, backend='allauth.account.auth_backends.AuthenticationBackend')
            ssolog.debug('social.get_connect_redirect_url: manually logged in user %s', user.pk)
        except Exception as e:
            ssolog.exception('social.get_connect_redirect_url: error logging in user %s: %s', user.pk, e)

        # Always redirect to our central post-login redirect
        redirect_url = getattr(settings, 'LOGIN_REDIRECT_URL', '/')
        ssolog.debug('social.get_connect_redirect_url: redirecting to %s', redirect_url)
        return redirect_url

    @transaction.atomic
    def save_user(self, request, sociallogin, form=None):
        # Keep existing behaviour for connecting/creating users. This method
        # intentionally focuses on resilience: do not raise DB errors for the
        # optional audit log.
        user = sociallogin.user
        email = getattr(user, 'email', None)
        if not email:
            raise ValueError('Social account did not provide an email')

        try:
            try:
                existing = User.objects.select_for_update().filter(email__iexact=email).first()
            except Exception:
                existing = User.objects.filter(email__iexact=email).first()

            if existing:
                sociallogin.state['process'] = 'connect'
                try:
                    sociallogin.connect(request, existing)
                except Exception:
                    logger.exception('save_user: failed to connect social to existing %s', email)

                # Update basic fields but do not override admin-controlled role
                updated = False
                changes = {}
                s_first = getattr(user, 'first_name', '') or ''
                s_last = getattr(user, 'last_name', '') or ''
                s_email = getattr(user, 'email', '') or ''
                if s_first and existing.first_name != s_first:
                    changes['first_name'] = [existing.first_name, s_first]
                    existing.first_name = s_first
                    updated = True
                if s_last and existing.last_name != s_last:
                    changes['last_name'] = [existing.last_name, s_last]
                    existing.last_name = s_last
                    updated = True
                if s_email and existing.email.lower() != s_email.lower():
                    changes['email'] = [existing.email, s_email.lower()]
                    existing.email = s_email.lower()
                    updated = True

                # Optionally map SSO claims to roles if configured
                try:
                    extra = getattr(sociallogin, 'account', None) and getattr(sociallogin.account, 'extra_data', {}) or {}
                    claim_vals = []
                    for key in ('app_role', 'role', 'roles', 'groups'):
                        val = extra.get(key)
                        if val:
                            if isinstance(val, (list, tuple)):
                                claim_vals.extend(val)
                            else:
                                claim_vals.append(val)
                    mapping = getattr(settings, 'SSO_ROLE_MAPPING', {}) or {}
                    override = getattr(settings, 'SSO_ROLE_OVERRIDE', False)
                    mapped = None
                    if mapping and claim_vals:
                        for cv in claim_vals:
                            if cv in mapping:
                                mapped = mapping[cv]
                                break
                    if override and mapped and existing.role != mapped:
                        changes['role'] = [existing.role, mapped]
                        existing.role = mapped
                        updated = True
                except Exception:
                    logger.exception('save_user: error evaluating SSO role mapping for %s', email)

                if updated:
                    existing.save()
                    logger.info('save_user: updated existing user %s fields=%s', existing.email, list(changes.keys()))
                    # Write audit log if present; do not let missing table break login
                    try:
                        from .models import SSOAuditLog
                        provider = getattr(sociallogin, 'account', None) and getattr(sociallogin.account, 'provider', '') or ''
                        try:
                            SSOAuditLog.objects.create(user=existing, provider=provider, changed_fields=changes)
                        except (ProgrammingError, DatabaseError) as db_exc:
                            logger.warning('SSOAuditLog write skipped: %s', db_exc)
                            ssolog.exception('SSOAuditLog write skipped for user=%s provider=%s', getattr(existing, 'email', None), provider)
                    except Exception:
                        logger.exception('save_user: failed to write SSOAuditLog for %s', getattr(existing, 'email', None))

                try:
                    if getattr(existing, 'role', None) == 'student':
                        from .models import Student
                        Student.objects.get_or_create(user=existing, defaults={'student_id': f'SSO{existing.pk}'})
                except Exception:
                    logger.exception('save_user: failed to ensure student profile for %s', email)

                if getattr(existing, 'role', None) == 'pending':
                    raise ImmediateHttpResponse(redirect('accounts_welcome'))

                try:
                    sociallogin.user = existing
                    ssolog.debug('save_user: set sociallogin.user to existing user pk=%s', existing.pk)
                except Exception:
                    pass

                # Ensure the user is properly authenticated in the request
                try:
                    from django.contrib.auth import login
                    # Note: We can't call login() here because we don't have access to the request
                    # The authentication should be handled by allauth's flow
                    ssolog.debug('save_user: returning existing user pk=%s for authentication', existing.pk)
                except Exception as e:
                    ssolog.exception('save_user: error during authentication setup: %s', e)

                return existing

            # Create new user
            username = getattr(user, 'username', None) or email.split('@')[0]
            base = username
            counter = 0
            while User.objects.filter(username=username).exists():
                counter += 1
                username = f"{base}{counter}"
            user.username = username
            user.email = email
            user.first_name = getattr(user, 'first_name', '') or ''
            user.last_name = getattr(user, 'last_name', '') or ''
            user.set_unusable_password()
            try:
                user.role = getattr(user, 'role', None) or 'defaultuser'
            except Exception:
                pass
            user.save()
            try:
                sociallogin.connect(request, user)
            except Exception:
                logger.exception('save_user: failed to connect social to new user %s', email)
            try:
                sociallogin.user = type(user).objects.filter(pk=user.pk).first() or user
            except Exception:
                sociallogin.user = user
            logger.info('save_user: created new SSO user %s', email)
            if getattr(user, 'role', None) == 'pending':
                raise ImmediateHttpResponse(redirect('accounts_welcome'))
            return user

        except Exception:
            logger.exception('save_user: unexpected exception for social user %s', email)
            # Fallback to existing user by email if available
            try:
                fallback = User.objects.filter(email__iexact=email).first()
                if fallback:
                    try:
                        sociallogin.state['process'] = 'connect'
                        sociallogin.connect(request, fallback)
                    except Exception:
                        logger.exception('save_user: failed to connect social to fallback %s', getattr(fallback, 'email', None))
                    return fallback
            except Exception:
                logger.exception('save_user: error during fallback lookup for %s', email)
            raise


class CustomAccountAdapter(DefaultAccountAdapter):
    """Account adapter ensuring consistent redirect handling for non-social logins."""

    def get_login_redirect_url(self, request):
        next_url = request.GET.get('next') or request.POST.get('next')
        ssolog.debug('account.get_login_redirect_url: next=%s user=%s', next_url, getattr(request.user, 'pk', None))
        safe = _safe_next(request, next_url)
        if safe:
            ssolog.debug('account.get_login_redirect_url: returning safe next=%s', safe)
            return safe
        ssolog.debug('account.get_login_redirect_url: deferring to LOGIN_REDIRECT_URL')
        return getattr(settings, 'LOGIN_REDIRECT_URL', '/')







