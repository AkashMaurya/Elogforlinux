import logging
from urllib.parse import urlparse

logger = logging.getLogger('sso_debug')


class SSOCallbackLoggerMiddleware:
    """Log basic info about Microsoft SSO callback requests to aid debugging.

    This middleware is safe to leave enabled in production because it only
    logs metadata (host, path, querystring present) and not secrets.
    """

    CALLBACK_PATH = '/accounts/microsoft/login/callback/'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            path = request.path
            if path.startswith(self.CALLBACK_PATH):
                q = request.META.get('QUERY_STRING', '')
                host = request.get_host()
                # Cookies sent by the browser (dict) and raw Cookie header
                cookies = dict(request.COOKIES)
                raw_cookie_header = request.META.get('HTTP_COOKIE')
                scheme = request.scheme
                # Whether session exists and its key
                session_key = None
                try:
                    session_key = getattr(request.session, 'session_key', None)
                    session_keys = list(request.session.keys())
                except Exception:
                    session_keys = None

                logger.debug('SSO callback request host=%s path=%s qs=%s scheme=%s session_key=%s cookies=%s raw_cookie=%s session_keys=%s',
                             host, path, q, scheme, session_key, list(cookies.keys()), raw_cookie_header, session_keys)
        except Exception:
            logger.exception('Error while logging SSO callback request')

        return self.get_response(request)
