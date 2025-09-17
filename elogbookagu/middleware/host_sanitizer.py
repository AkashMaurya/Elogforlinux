"""Middleware to sanitize malicious or malformed Host headers.

Sometimes proxies or scanners send comma-separated Host headers like
'52.59.219.87,52.59.219.87' which Django rejects with DisallowedHost. This
middleware keeps only the first hostname token and places it back on the
request.META['HTTP_HOST'] so Django's host validation behaves more predictably.

This doesn't replace proper proxy configuration. If you control the reverse
proxy, prefer fixing it at the proxy layer. This middleware is a defensive
measure for handling malformed external traffic.
"""

from typing import Optional


class HostSanitizerMiddleware:
    """Keep only the first host token if comma-separated host headers are present."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Normalize common host headers that Django may read when validating the host.
        # Some scanners or misconfigured proxies send comma-separated host values
        # (e.g. 'a,b') which Django rejects. Keep only the first token.
        for key in ('HTTP_HOST', 'HTTP_X_FORWARDED_HOST', 'SERVER_NAME'):
            val = request.META.get(key)
            if isinstance(val, str) and ',' in val:
                sanitized = val.split(',')[0].strip()
                if sanitized:
                    request.META[key] = sanitized
        return self.get_response(request)
