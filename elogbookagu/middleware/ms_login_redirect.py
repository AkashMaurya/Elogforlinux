from django.shortcuts import redirect


class MSLoginRedirectMiddleware:
    """Intercept requests to the allauth provider login URL and redirect
    the user to the Microsoft authorize endpoint while stashing allauth
    state in the session. This avoids rendering the local
    `/accounts/microsoft/login/` page.
    """

    LOGIN_PATH = '/accounts/microsoft/login/'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            if request.path == self.LOGIN_PATH and request.method == 'GET':
                # Avoid importing heavy packages at module import time
                from allauth.socialaccount.internal import statekit
                from django.conf import settings
                from urllib.parse import urlencode
                import logging

                ssolog = logging.getLogger('sso_debug')

                # Stash minimal state expected by allauth
                state = {'process': 'login'}
                state_id = statekit.stash_state(request, state)
                ssolog.debug('MSLoginRedirectMiddleware: stashed state_id=%s in session keys=%s', state_id, list(request.session.keys()))

                # Also persist a lightweight copy of the state to the DB as a
                # fallback in case the browser doesn't send the sessionid cookie
                # back on the provider callback. This helps make the SSO flow
                # resilient to SameSite/secure cookie issues.
                try:
                    from accounts.models import SSOState
                    SSOState.objects.update_or_create(state_id=state_id, defaults={'payload': state})
                except Exception:
                    ssolog.exception('Failed to persist SSOState fallback for state_id=%s', state_id)

                client_id = getattr(settings, 'MICROSOFT_CLIENT_ID', '') or '2b3039c5-ff38-4ab1-9250-22e791e33999'
                tenant = getattr(settings, 'TENANT_ID', '') or '9c021be8-508f-4638-b1df-52b0e3c615ac'
                scope = 'profile openid User.Read email'
                params = {
                    'client_id': client_id,
                    'response_type': 'code',
                    'redirect_uri': getattr(settings, 'REDIRECT_URI', ''),
                    'scope': scope,
                    'state': state_id,
                }
                authorize_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{urlencode(params)}"
                ssolog.debug('MSLoginRedirectMiddleware: redirecting to authorize_url=%s state_id=%s', authorize_url, state_id)
                return redirect(authorize_url)
        except Exception:
            # Fail open — if middleware errors, allow request to continue
            pass

        return self.get_response(request)
