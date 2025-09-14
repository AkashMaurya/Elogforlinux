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
        ssolog.debug('social.get_login_redirect_url: deferring to LOGIN_REDIRECT_URL for user=%s', getattr(user, 'pk', None))
        return getattr(settings, 'LOGIN_REDIRECT_URL', '/')

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
                except Exception:
                    pass
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


User = get_user_model()
logger = logging.getLogger(__name__)
ssolog = logging.getLogger('sso_debug')


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
  """Custom adapter for django-allauth social logins (Microsoft/Azure OIDC).

  Behaviour:
  - Link social accounts to existing users by email when possible.
  - Create new users with `role='student'` when no user exists.
  - Provide a resilient `get_app` to avoid MultipleObjectsReturned when
    multiple SocialApp rows exist for the same provider.

  Production notes:
  - Register the exact Redirect URI in Azure (e.g. https://elog.agu.edu.bh/accounts/microsoft/login/callback/)
  - Set `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `TENANT_ID`, and `MICROSOFT_REDIRECT_URI` in your production env.
  """

  def get_app(self, request, provider, *args, **kwargs):
    """Return a SocialApp instance for the given provider, handling duplicates.

    If multiple SocialApp rows exist for the same provider, prefer the one
    attached to the current SITE_ID. Falls back to the first available.
    """
    try:
      return super().get_app(request, provider, *args, **kwargs)
    except MultipleObjectsReturned:
      from allauth.socialaccount.models import SocialApp

      apps = SocialApp.objects.filter(provider=provider)
      # Prefer site-specific app
      site_apps = apps.filter(sites__id=getattr(settings, 'SITE_ID', None))
      if site_apps.exists():
        return site_apps.first()
      # Fallback
      return apps.first()

  def pre_social_login(self, request, sociallogin):
    """Link by email if an account exists to avoid duplicate users."""
    email = getattr(sociallogin.user, 'email', None)
    if not email:
      logger.warning("Social login did not provide an email address; redirecting to welcome.")
      ssolog.debug('pre_social_login: missing email on sociallogin; sociallogin=%s', getattr(sociallogin, 'account', None))
      raise ImmediateHttpResponse(redirect('accounts_welcome'))

    try:
      existing_user = User.objects.filter(email__iexact=email).first()
      ssolog.debug('pre_social_login: found existing_user=%s for email=%s', getattr(existing_user, 'pk', None), email)
      if existing_user:
        # Link the social account to the existing user and let the flow continue
        sociallogin.state['process'] = 'connect'
        try:
          sociallogin.connect(request, existing_user)
          ssolog.info('pre_social_login: connected social account to existing user pk=%s email=%s', existing_user.pk, email)
        except Exception:
          logger.exception("Error connecting sociallogin to existing user %s", email)
        # If the existing user is pending, show welcome page instead of logging in
        if getattr(existing_user, 'role', None) == 'pending':
          ssolog.info("pre_social_login: existing user %s is pending; redirecting to welcome.", email)
          raise ImmediateHttpResponse(redirect('accounts_welcome'))
    except Exception as exc:
      logger.exception("Error while trying to link social account for %s: %s", email, exc)
      ssolog.exception('pre_social_login exception for email=%s', email)

  def get_login_redirect_url(self, request, socialaccount=None):
    """Return post-login redirect URL for social logins based on the linked user's role.

    This mirrors the behaviour of the account adapter but runs in contexts
    where allauth dispatches via the social adapter. It looks for the
    authenticated user (or the socialaccount's user) and routes accordingly.
    """
    # Prefer the authenticated user if available. Always re-fetch from DB to
    # ensure we use the latest `role` value (admin may have changed it).
    user = getattr(request, 'user', None)
    if user and getattr(user, 'is_authenticated', False):
      try:
        user = type(user).objects.filter(pk=user.pk).first() or user
      except Exception:
        # Fallback to the original request user if DB access fails
        pass
    else:
      # Fallback to the socialaccount's user if provided
      if socialaccount and getattr(socialaccount, 'user', None):
        try:
          social_user = socialaccount.user
          user = type(social_user).objects.filter(pk=social_user.pk).first() or social_user
        except Exception:
          user = socialaccount.user

    # Centralized safe-next checking. We want to allow `next` only when it's
    # host-safe and not pointing to provider/internal endpoints (which often
    # include '3rdparty' or 'socialaccount' or start with '/accounts/microsoft').
    def _safe_next(url):
      if not url:
        return None
      try:
        login_path = reverse('login')
      except Exception:
        login_path = getattr(settings, 'LOGIN_URL', '/login/')
      parsed = urlparse(url)
      path = parsed.path or ''
      is_provider_path = ('3rdparty' in path) or ('socialaccount' in path) or path.startswith('/accounts/microsoft')
      is_allowed = url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}, require_https=request.is_secure())
      if is_allowed and not is_provider_path and not (url == login_path or url.endswith('/login/') or url == getattr(settings, 'LOGIN_URL', '/login/')):
        return url
      return None

    next_url = request.GET.get('next') or request.POST.get('next')
    ssolog.debug('get_login_redirect_url called: user=%s auth=%s next=%s', getattr(user, 'pk', None), bool(user and getattr(user, 'is_authenticated', False)), next_url)
    safe = _safe_next(next_url)
    if safe:
      ssolog.debug('get_login_redirect_url: returning safe next_url=%s', safe)
      return safe
    # Otherwise always defer to the central post-login view so we can
    # consistently route by role server-side.
    ssolog.debug('get_login_redirect_url: deferring to central post-login for next=%s', next_url)
    return getattr(settings, 'LOGIN_REDIRECT_URL', '/')

    # Send the user to the central post-login redirect URL so that a single
    # view (`/accounts/post-login-redirect/`) can perform role-based routing.
    # This avoids leaking provider/internal endpoints via `next` and keeps
    # redirect logic in one place.
    ssolog.debug('get_login_redirect_url: deferring to LOGIN_REDIRECT_URL=%s for user=%s role=%s', getattr(settings, 'LOGIN_REDIRECT_URL', '/'), getattr(user, 'pk', None), getattr(user, 'role', None))
    return getattr(settings, 'LOGIN_REDIRECT_URL', '/')

  @transaction.atomic
  def save_user(self, request, sociallogin, form=None):
    """Create or connect a user for the given sociallogin.

    Behaviour:
    - If a User with the social email exists, connect the social account to it.
    - Otherwise create a new user with role='defaultuser' and ensure any
      necessary profile exists.
    - Catch unexpected exceptions, attempt a safe fallback, and log details
      instead of allowing an uncaught exception to produce a 500 response.
    """

    user = sociallogin.user
    email = getattr(user, 'email', None)

    if not email:
      raise ValueError("Social account did not provide an email address")

    try:
      # Try to lock rows with this email to avoid concurrent duplicate creation
      try:
        existing = User.objects.select_for_update().filter(email__iexact=email).first()
      except Exception:
        existing = User.objects.filter(email__iexact=email).first()

      if existing:
        sociallogin.state['process'] = 'connect'
        try:
          sociallogin.connect(request, existing)
        except Exception:
          logger.exception("Failed to connect sociallogin to existing user %s", email)

        logger.info("save_user: connected social account to existing user %s", email)

        # Update existing user's basic profile fields from SSO authoritative data.
        # By default do not overwrite role here; admins control role in the
        # application. If `settings.SSO_ROLE_OVERRIDE` is True and a mapping
        # is provided via `settings.SSO_ROLE_MAPPING`, the adapter will map
        # SSO claim values to internal roles.
        try:
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
          # Normalize email to lowercase and update if changed
          if s_email and existing.email.lower() != s_email.lower():
            changes['email'] = [existing.email, s_email.lower()]
            existing.email = s_email.lower()
            updated = True

          # Optional: map SSO claim(s) to local role
          try:
            extra = getattr(sociallogin, 'account', None) and getattr(sociallogin.account, 'extra_data', {}) or {}
            # Candidate claim keys to inspect
            claim_vals = []
            for key in ('app_role', 'role', 'roles', 'groups'):
              val = extra.get(key)
              if val:
                if isinstance(val, (list, tuple)):
                  claim_vals.extend(val)
                else:
                  claim_vals.append(val)

            # settings.SSO_ROLE_MAPPING should be a dict like {'azure_role':'student',...}
            mapping = getattr(settings, 'SSO_ROLE_MAPPING', {}) or {}
            override = getattr(settings, 'SSO_ROLE_OVERRIDE', False)
            mapped_role = None
            if mapping and claim_vals:
              for cv in claim_vals:
                if cv in mapping:
                  mapped_role = mapping[cv]
                  break

            if override and mapped_role and existing.role != mapped_role:
              changes['role'] = [existing.role, mapped_role]
              existing.role = mapped_role
              updated = True
          except Exception:
            logger.exception("Error while evaluating SSO role mapping for %s", email)

          if updated:
            existing.save()
            logger.info("Updated existing user %s from SSO data: %s", existing.email, list(changes.keys()))

            # Record audit log if the model for SSOAuditLog exists. If the
            # migration hasn't been applied (table missing) we must not raise
            # a ProgrammingError that aborts the login flow — log and continue.
            try:
              from .models import SSOAuditLog
              provider = getattr(sociallogin, 'account', None) and getattr(sociallogin.account, 'provider', '') or ''
              try:
                SSOAuditLog.objects.create(user=existing, provider=provider, changed_fields=changes)
              except (ProgrammingError, DatabaseError) as db_exc:
                logger.warning("SSOAuditLog write skipped due to DB error (is migration applied?): %s", db_exc)
                ssolog.exception('SSOAuditLog write skipped for user=%s provider=%s', getattr(existing, 'email', None), provider)
            except Exception:
              logger.exception("Failed to import or write SSOAuditLog for %s", getattr(existing, 'email', None))
        except Exception:
          logger.exception("Failed to update existing user profile from SSO for %s", email)
        # Ensure Student profile exists when role is student
        try:
          if getattr(existing, 'role', None) == 'student':
            from .models import Student

            Student.objects.get_or_create(user=existing, defaults={
              'student_id': f"SSO{existing.pk}",
            })
        except Exception:
          logger.exception("Failed to ensure Student profile for existing user %s", email)

        # If the existing user is pending, redirect to welcome instead of logging in
        if getattr(existing, 'role', None) == 'pending':
          logger.info("Existing user %s is pending; redirecting to welcome.", email)
          raise ImmediateHttpResponse(redirect('accounts_welcome'))

        # Ensure sociallogin.user points to the DB-backed user instance so
        # downstream code (redirects, templates) reads the authoritative role.
        try:
          sociallogin.user = existing
        except Exception:
          pass
        return existing

  # Create new user from social data
      username = getattr(user, 'username', None) or email.split('@')[0]
      first_name = getattr(user, 'first_name', '') or ''
      last_name = getattr(user, 'last_name', '') or ''

      base_username = username
      counter = 0
      while User.objects.filter(username=username).exists():
        counter += 1
        username = f"{base_username}{counter}"

      user.username = username
      user.email = email
      user.first_name = first_name
      user.last_name = last_name
      user.set_unusable_password()
      try:
        # New SSO users default to the 'defaultuser' role per project requirements
        # Only set role on creation; do not overwrite if model or admin expects otherwise.
        user.role = getattr(user, 'role', None) or 'defaultuser'
      except Exception:
        # If the user model doesn't have role or it's read-only, ignore
        pass

      user.save()
      try:
        sociallogin.connect(request, user)
      except Exception:
        logger.exception("Failed to connect sociallogin to newly created user %s", email)

      # Ensure sociallogin.user references the saved DB user
      try:
        sociallogin.user = type(user).objects.filter(pk=user.pk).first() or user
      except Exception:
        sociallogin.user = user

      logger.info("Created new SSO user: %s", email)

      # Newly created users default to 'pending' so show welcome page
      if getattr(user, 'role', None) == 'pending':
        logger.info("New SSO user %s created as pending; redirecting to welcome.", email)
        raise ImmediateHttpResponse(redirect('accounts_welcome'))

      return user

    except Exception as exc:
      # Catch-all to avoid 500 responses from unexpected errors during SSO
      logger.exception("Unexpected error in save_user for social login (%s): %s", email, exc)

      # If a user with this email exists return it as a last resort
      try:
        fallback = User.objects.filter(email__iexact=email).first()
        if fallback:
          try:
            sociallogin.state['process'] = 'connect'
            sociallogin.connect(request, fallback)
          except Exception:
            logger.exception("Failed to connect sociallogin to fallback user %s", getattr(fallback, 'email', None))
          return fallback
      except Exception:
        logger.exception("Error during fallback lookup for social user %s", email)

      # Re-raise original exception so calling code can handle it if necessary
      raise


class CustomAccountAdapter(DefaultAccountAdapter):
  """Account adapter to control post-login redirect based on user role.

  This ensures that both regular and social logins are redirected to the
  appropriate app section (student/doctor/staff/admin) instead of the
  global `LOGIN_REDIRECT_URL` which was previously fixed to the student
  dashboard.
  """

  def get_login_redirect_url(self, request):
    # Preserve 'next' parameter when provided (behaviour consistent with allauth)
    next_url = request.GET.get('next') or request.POST.get('next')
    # Do not allow an incoming `next` that points back to the login page
    # or to allauth/provider internals (these sometimes appear as
    # `/accounts/3rdparty/...` and can trigger login loops). Also verify
    # the URL is host-safe.
    try:
      login_path = reverse('login')
    except Exception:
      login_path = getattr(settings, 'LOGIN_URL', '/login/')
    if next_url:
      parsed = urlparse(next_url)
      path = parsed.path or ''
      is_provider_path = (
        '3rdparty' in path or 'socialaccount' in path or path.startswith('/accounts/microsoft')
      )
      is_allowed = url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure())
      # Harden: never allow redirect to provider/internal paths
      if is_allowed and not is_provider_path and not (
        next_url == login_path or next_url.endswith('/login/') or next_url == getattr(settings, 'LOGIN_URL', '/login/')
      ):
        return next_url
      else:
        # Always route through central post-login view
        return getattr(settings, 'LOGIN_REDIRECT_URL', '/')

    user = getattr(request, 'user', None)
    # Fallback to configured default
    default = getattr(settings, 'LOGIN_REDIRECT_URL', '/')

    # If we have an authenticated user, re-load from DB to pick up any admin
    # changes to `role` that may have happened since the session was created.
    if user and getattr(user, 'is_authenticated', False):
      try:
        user = type(user).objects.filter(pk=user.pk).first() or user
      except Exception:
        pass
    else:
      return default

    # Defer role-based routing to the centralized post-login view.
    return getattr(settings, 'LOGIN_REDIRECT_URL', '/')
