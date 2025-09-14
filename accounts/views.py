from django.contrib.auth.views import LoginView

def login_view(request):
    """Custom login view to handle authentication"""
    return LoginView.as_view(template_name='registration/login.html')(request)
from django.shortcuts import render
from django.shortcuts import render
from django.conf import settings
import logging
from django.shortcuts import redirect
from django.conf import settings
from urllib.parse import urlencode


def welcome(request):
    """Simple welcome page for pending users or when SSO cannot proceed.

    This page informs the user that their account is pending and that the
    team will add them to the directory soon.
    """
    return render(request, "accounts/welcome.html", status=200)

logger = logging.getLogger(__name__)

# Other account views (if any) should go here. The Microsoft provider login
# flow intentionally uses django-allauth's built-in views so that the OAuth
# state is created on the server before redirecting to the provider.


def microsoft_direct(request):
    """Build a tenant-aware Microsoft authorize URL, stash the allauth state,
    and redirect the user directly to the Microsoft authorize endpoint.

    This view uses allauth's `statekit.stash_state` so the server-side state
    is stored in the session before redirecting to Microsoft. The resulting
    redirect goes straight to `login.microsoftonline.com/<TENANT>/oauth2/v2.0/authorize`.
    """
    from allauth.socialaccount.internal import statekit

    # Build minimal state expected by allauth. Keep 'process' to allow
    # downstream handling if required.
    state = {
        'process': 'login',
    }

    state_id = statekit.stash_state(request, state)


    # Prefer explicit settings; fall back to the tenant/client the user
    # requested so the URL matches their expectation.
    client_id = getattr(settings, 'MICROSOFT_CLIENT_ID', '') or '2b3039c5-ff38-4ab1-9250-22e791e33999'
    tenant = getattr(settings, 'TENANT_ID', '') or '9c021be8-508f-4638-b1df-52b0e3c615ac'

    # Use the more typical OIDC scope ordering requested by the user.
    scope = 'profile openid User.Read email'

    params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': getattr(settings, 'REDIRECT_URI', ''),
        'scope': scope,
        'state': state_id,
    }
    authorize_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{urlencode(params)}"
    return redirect(authorize_url)


def microsoft_state(request):
    """AJAX-friendly endpoint that stashes an allauth state and returns the
    full Microsoft authorize URL as JSON. This allows client-side code to open
    the provider directly (to avoid the intermediate /accounts/.../login page)
    while still ensuring the server has stored the expected state.
    """
    from allauth.socialaccount.internal import statekit
    from django.http import JsonResponse
    from django.conf import settings
    from urllib.parse import urlencode

    state = {'process': 'login'}
    state_id = statekit.stash_state(request, state)

    params = {
        'client_id': getattr(settings, 'MICROSOFT_CLIENT_ID', ''),
        'response_type': 'code',
        'redirect_uri': getattr(settings, 'REDIRECT_URI', ''),
        'scope': ' '.join(getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {}).get('microsoft', {}).get('SCOPE', [])),
        'state': state_id,
    }
    tenant = getattr(settings, 'TENANT_ID', 'common')
    authorize_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{urlencode(params)}"
    # Log the generated URL for debugging (non-sensitive; the URL contains state)
    import logging
    logging.getLogger('sso_debug').debug('Generated authorize_url=%s', authorize_url)
    return JsonResponse({'authorize_url': authorize_url})


def post_login_redirect(request):
    """Central redirect view after login.

    Both the account adapter and settings will point to this view so that
    every login (social or local) goes through a single role-based
    redirect decision. This ensures admin role changes are respected on
    next login because we re-load the user from the DB in the adapter and
    this view trusts the session-authenticated user to exist.
    """
    from django.shortcuts import redirect
    from django.urls import reverse
    from django.conf import settings

    user = getattr(request, 'user', None)
    if not user or not getattr(user, 'is_authenticated', False):
        return redirect('login')

    # Reload user from DB to pick up recent role changes
    try:
        user = type(user).objects.filter(pk=user.pk).first() or user
    except Exception:
        pass

    # Respect a safe `next` parameter but avoid redirect loops back to login
    next_url = request.GET.get('next') or request.POST.get('next')
    try:
        login_path = reverse('login')
    except Exception:
        login_path = getattr(settings, 'LOGIN_URL', '/login/')

    if next_url:
        from urllib.parse import urlparse
        from django.utils.http import url_has_allowed_host_and_scheme

        parsed = urlparse(next_url)
        path = parsed.path or ''
        is_provider_path = '3rdparty' in path or 'socialaccount' in path or path.startswith('/accounts/microsoft')
        is_allowed = url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure())
        if is_allowed and not is_provider_path and not (next_url == login_path or next_url.endswith('/login/') or next_url == getattr(settings, 'LOGIN_URL', '/login/')):
            return redirect(next_url)

    # Map roles to named URLs (reverse-safe)
    role_to_name = {
        'defaultuser': 'defaultuser:default_home',
        'student': 'student_section:student_dash',
        'staff': 'staff_section:staff_dash',
        'doctor': 'doctor_section:doctor_dash',
        'admin': 'admin_section:admin_dash',
    }

    role = getattr(user, 'role', None)
    if role in role_to_name:
        try:
            return redirect(reverse(role_to_name[role]))
        except Exception:
            # Fallback to path-based redirect if reversing fails
            fallback_paths = {
                'defaultuser': '/defaultuser/',
                'student': '/student_section/',
                'staff': '/staff_section/',
                'doctor': '/doctor_section/',
                'admin': '/admin_section/',
            }
            return redirect(fallback_paths.get(role, '/'))

    # Default fallback
    return redirect(getattr(settings, 'LOGIN_REDIRECT_URL', '/'))
