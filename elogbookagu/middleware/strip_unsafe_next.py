from urllib.parse import urlparse, urlencode, urlunparse, parse_qs
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import logging

class StripUnsafeNextMiddleware(MiddlewareMixin):
    """Middleware to remove unsafe `next` query parameters.

    If a request contains a `next` query parameter that points to an
    internal provider or otherwise disallowed path (contains '3rdparty',
    'socialaccount' or starts with '/accounts/microsoft'), this middleware
    will rewrite the request's GET querystring (via environ) to remove the
    `next` parameter so downstream login views/adapters will not see it.

    This is intentionally conservative: it only removes `next` when the
    value matches known unsafe patterns.
    """

    UNSAFE_PATTERNS = ('3rdparty', 'socialaccount', '/accounts/microsoft')

    def process_request(self, request):
        # Log every request briefly so we can confirm this middleware runs.
        logging.getLogger('sso_debug').debug('StripUnsafeNextMiddleware: request path=%s qs=%s', request.path, request.META.get('QUERY_STRING', ''))
        # Only act on requests that include a `next` parameter.
        next_val = request.GET.get('next')
        if not next_val:
            return None

        try:
            path = urlparse(next_val).path or ''
        except Exception:
            path = ''

        unsafe = False
        # Treat known unsafe patterns as before
        for p in self.UNSAFE_PATTERNS:
            if p in path or path.startswith(p):
                unsafe = True
                break
        # Also consider the central LOGIN_REDIRECT_URL unsafe when it is
        # present as a `next` value: we don't want the browser to be sent
        # to the central post-login landing page via a query param.
        try:
            central = getattr(settings, 'LOGIN_REDIRECT_URL', '/accounts/post-login-redirect/')
            central_path = urlparse(central).path or ''
            if central_path and central_path == path:
                unsafe = True
        except Exception:
            pass

        ssolog = logging.getLogger('sso_debug')
        if not unsafe:
            ssolog.debug('StripUnsafeNextMiddleware: saw next=%s but considered safe for path=%s on request %s qs=%s', next_val, path, request.path, request.META.get('QUERY_STRING', ''))
            return None

        # Remove `next` from the GET params by reconstructing the QUERY_STRING
        qs = request.META.get('QUERY_STRING', '')
        params = parse_qs(qs, keep_blank_values=True)
        if 'next' in params:
            params.pop('next', None)
            # Rebuild query string
            new_qs = urlencode(params, doseq=True)
            request.META['QUERY_STRING'] = new_qs
            # Also mutate request.GET (QueryDict) to reflect the change
            try:
                mutable = request.GET._mutable
                request.GET._mutable = True
                if 'next' in request.GET:
                    del request.GET['next']
                request.GET._mutable = mutable
            except Exception:
                pass
            ssolog.debug('StripUnsafeNextMiddleware: removed unsafe next=%s from request %s original_qs=%s new_qs=%s', next_val, request.path, qs, new_qs)

        return None

    def process_response(self, request, response):
        """Rewrite redirects to the login page that include an unsafe `next`.

        Many parts of Django/allauth will redirect unauthenticated requests to
        `LOGIN_URL?next=...`. If `next` points to an internal provider path
        (e.g. `/accounts/3rdparty/...`), this can cause the browser to land on
        the login page with an unsafe next. To avoid that UX and potential loops
        rewrite those redirects to the central `LOGIN_REDIRECT_URL`.
        """
        try:
            status = getattr(response, 'status_code', None)
            if status in (301, 302, 303, 307, 308) and response.get('Location'):
                loc = response['Location']
                parsed = urlparse(loc)
                qs = parse_qs(parsed.query, keep_blank_values=True)
                next_vals = qs.get('next') or qs.get('next[]')
                if next_vals:
                    next_val = next_vals[0]
                    path = urlparse(next_val).path or ''
                    rewritten = False
                    # If the next points at known unsafe provider/internal
                    # endpoints, rewrite the whole redirect to the central
                    # post-login URL (existing behaviour).
                    for p in self.UNSAFE_PATTERNS:
                        if p in path or path.startswith(p):
                            new_loc = getattr(settings, 'LOGIN_REDIRECT_URL', '/')
                            logging.getLogger('sso_debug').debug(
                                'StripUnsafeNextMiddleware: rewriting redirect %s -> %s because unsafe next=%s',
                                loc, new_loc, next_val
                            )
                            response['Location'] = new_loc
                            rewritten = True
                            break
                    # (No additional handling for central LOGIN_REDIRECT_URL here)
        except Exception:
            logging.getLogger('sso_debug').exception('StripUnsafeNextMiddleware.process_response error')
        return response
