from django.contrib.auth.views import LoginView
from django.shortcuts import render
from django.shortcuts import render
from django.conf import settings
import logging
from django.shortcuts import redirect
from django.conf import settings
from urllib.parse import urlencode
from allauth.socialaccount.internal import statekit
from django.http import JsonResponse
from django.conf import settings
from urllib.parse import urlencode
from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlparse
import logging



ssolog = logging.getLogger('sso_debug')

def login_view(request):
    """Custom login view to handle authentication"""
    return LoginView.as_view(template_name='registration/login.html')(request)


@login_required
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
    ssolog = logging.getLogger('sso_debug')
    ssolog.debug('microsoft_direct: CALLED - method=%s path=%s user=%s',
                request.method, request.path, getattr(request.user, 'pk', 'Anonymous'))

    try:
        from allauth.socialaccount.internal import statekit

        # Build minimal state expected by allauth. Keep 'process' to allow
        # downstream handling if required.
        state = {
            'process': 'login',
        }

        state_id = statekit.stash_state(request, state)
        ssolog.debug('microsoft_direct: stashed state_id=%s', state_id)

        # Persist lightweight copy of state to DB as a fallback for missing session
        try:
            from .models import SSOState
            SSOState.objects.update_or_create(state_id=state_id, defaults={'payload': state})
            ssolog.debug('microsoft_direct: persisted SSOState state_id=%s', state_id)
        except Exception:
            ssolog.exception('microsoft_direct: failed to persist SSOState for state_id=%s', state_id)
    except Exception as e:
        ssolog.exception('microsoft_direct: error in state handling: %s', e)
        # Don't fail completely, continue with the redirect
        state_id = 'fallback_state'


    try:
        # Prefer explicit settings; fall back to the tenant/client the user
        # requested so the URL matches their expectation.
        client_id = getattr(settings, 'MICROSOFT_CLIENT_ID', '') or '2b3039c5-ff38-4ab1-9250-22e791e33999'
        tenant = getattr(settings, 'TENANT_ID', '') or '9c021be8-508f-4638-b1df-52b0e3c615ac'
        redirect_uri = getattr(settings, 'REDIRECT_URI', '')

        ssolog.debug('microsoft_direct: client_id=%s tenant=%s redirect_uri=%s',
                    client_id[:10] + '...', tenant, redirect_uri)

        # Use the more typical OIDC scope ordering requested by the user.
        scope = 'profile openid User.Read email'

        params = {
            'client_id': client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'scope': scope,
            'state': state_id,
        }
        authorize_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{urlencode(params)}"
        ssolog.debug('microsoft_direct: redirecting to Microsoft OAuth URL: %s', authorize_url[:100] + '...')
        return redirect(authorize_url)
    except Exception as e:
        ssolog.exception('microsoft_direct: error building OAuth URL: %s', e)
        # Fallback to login page with error message
        from django.contrib import messages
        messages.error(request, 'Error initiating Microsoft login. Please try again.')
        return redirect('/login/')


def microsoft_state(request):
    """AJAX-friendly endpoint that stashes an allauth state and returns the
    full Microsoft authorize URL as JSON. This allows client-side code to open
    the provider directly (to avoid the intermediate /accounts/.../login page)
    while still ensuring the server has stored the expected state.
    """


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
    # Also persist state to DB so callback restore can work when session cookie is missing
    try:
        from accounts.models import SSOState
        SSOState.objects.update_or_create(state_id=state_id, defaults={'payload': state})
        logging.getLogger('sso_debug').debug('microsoft_state: persisted SSOState state_id=%s', state_id)
    except Exception:
        logging.getLogger('sso_debug').exception('microsoft_state: failed to persist SSOState for state_id=%s', state_id)

    logging.getLogger('sso_debug').debug('Generated authorize_url=%s', authorize_url)
    return JsonResponse({'authorize_url': authorize_url})




ssolog = logging.getLogger('sso_debug')


def post_login_redirect(request):
    """Redirect user to the proper section after login based on role.

    Note: We don't use @login_required here because this view is called
    immediately after SSO authentication, and there can be timing issues
    with session establishment. Instead, we handle authentication manually.
    """

    user = getattr(request, 'user', None)
    session_info = {
        'session_key': getattr(request.session, 'session_key', 'None'),
        'session_keys': list(request.session.keys()) if hasattr(request, 'session') else [],
        'has_socialaccount_states': 'socialaccount_states' in request.session if hasattr(request, 'session') else False,
    }

    ssolog.debug('post_login_redirect: called with user=%s auth=%s session_info=%s',
                getattr(user, 'pk', None),
                bool(user and getattr(user, 'is_authenticated', False)),
                session_info)

    if not user or not getattr(user, 'is_authenticated', False):
        ssolog.warning('post_login_redirect: user not authenticated. user=%s auth=%s session=%s',
                      getattr(user, 'pk', None),
                      bool(user and getattr(user, 'is_authenticated', False)),
                      session_info)

        # Check if this might be a timing issue with SSO callback
        referer = request.META.get('HTTP_REFERER', '')
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Log additional debugging info
        ssolog.warning('post_login_redirect: referer=%s user_agent=%s', referer, user_agent)

        # If this appears to be coming from Microsoft SSO, try a different approach
        if ('microsoft' in referer.lower() or 'login.microsoftonline.com' in referer.lower() or
            'accounts/microsoft' in request.META.get('HTTP_REFERER', '')):
            ssolog.error('post_login_redirect: SSO callback but user not authenticated - possible session/cookie issue')
            # Redirect to a safe landing page with an error message
            from django.contrib import messages
            messages.error(request, 'Authentication completed but session not established. Please try logging in again.')
            return redirect('/')

        # For non-SSO cases, redirect to login
        return redirect(settings.LOGIN_URL)

    # Reload user to pick up any recent role changes
    try:
        user = type(user).objects.filter(pk=user.pk).first() or user
    except Exception:
        pass

    # Handle 'next' parameter safely
    next_url = request.GET.get('next') or request.POST.get('next')
    if next_url:
        parsed = urlparse(next_url)
        path = parsed.path or ''
        # Ignore internal provider URLs
        is_provider_path = any(x in path for x in ['3rdparty', 'socialaccount', '/accounts/microsoft'])
        is_allowed = url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        )
        if not is_provider_path and is_allowed:
            ssolog.debug('post_login_redirect: redirecting to safe next_url=%s', next_url)
            return redirect(next_url)
        else:
            ssolog.debug('post_login_redirect: ignoring unsafe or provider next_url=%s', next_url)

    # Map roles to dashboard URLs
    role_to_name = {
        'defaultuser': 'defaultuser:default_home',
        'student': 'student_section:student_dash',
        'staff': 'staff_section:staff_dash',
        'doctor': 'doctor_section:doctor_dash',
        'admin': 'admin_section:admin_dash',
    }

    role = getattr(user, 'role', None)
    try:
        target_url = reverse(role_to_name.get(role, 'defaultuser:default_home'))
    except Exception:
        # fallback to simple path
        fallback_paths = {
            'defaultuser': '/defaultuser/',
            'student': '/student_section/',
            'staff': '/staff_section/',
            'doctor': '/doctor_section/',
            'admin': '/admin_section/',
        }
        target_url = fallback_paths.get(role, '/')

    ssolog.debug('post_login_redirect: user=%s role=%s redirecting to %s', getattr(user, 'pk', None), role, target_url)
    return redirect(target_url)


def debug_auth_status(request):
    """Debug view to check authentication status - remove in production."""
    from django.http import JsonResponse

    user = getattr(request, 'user', None)
    session_data = dict(request.session) if hasattr(request, 'session') else {}

    # Remove sensitive data from session for logging
    safe_session = {k: v for k, v in session_data.items() if not k.startswith('_')}

    # Check if user exists in database
    user_in_db = None
    if user and hasattr(user, 'pk') and user.pk:
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user_in_db = User.objects.filter(pk=user.pk).first()
        except Exception as e:
            user_in_db = f"Error: {e}"

    debug_info = {
        'user_exists': user is not None,
        'user_authenticated': bool(user and getattr(user, 'is_authenticated', False)),
        'user_id': getattr(user, 'pk', None),
        'user_email': getattr(user, 'email', None),
        'user_role': getattr(user, 'role', None),
        'user_in_db': bool(user_in_db) if user_in_db and not isinstance(user_in_db, str) else str(user_in_db),
        'session_key': getattr(request.session, 'session_key', None),
        'session_keys': list(safe_session.keys()),
        'has_socialaccount_states': 'socialaccount_states' in session_data,
        'request_path': request.path,
        'request_method': request.method,
        'middleware_order': [m.__class__.__name__ for m in getattr(request, '_middleware_chain', [])],
    }

    ssolog.debug('debug_auth_status: %s', debug_info)
    return JsonResponse(debug_info)


def social_connections_redirect(request):
    """Handle redirects from allauth's /accounts/3rdparty/ URL.

    This view intercepts allauth's default social connections redirect
    and sends users to the appropriate role-based dashboard instead.
    """
    user = getattr(request, 'user', None)
    ssolog.debug('social_connections_redirect: called with user=%s auth=%s',
                getattr(user, 'pk', None),
                bool(user and getattr(user, 'is_authenticated', False)))

    if user and getattr(user, 'is_authenticated', False):
        # User is authenticated, redirect to role-based dashboard
        ssolog.debug('social_connections_redirect: user authenticated, redirecting to post-login-redirect')
        return redirect('/accounts/post-login-redirect/')
    else:
        # User not authenticated, redirect to login
        ssolog.warning('social_connections_redirect: user not authenticated, redirecting to login')
        return redirect(settings.LOGIN_URL)
