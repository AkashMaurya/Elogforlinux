from django.contrib.auth.models import AnonymousUser


class EnsureUserMiddleware:
    """Middleware to guarantee request.user exists during request handling.

    Some error paths or custom WSGI handlers can produce a request object
    without a `user` attribute. Context processors assume `request.user`
    may exist; this middleware ensures it is present and set to an
    AnonymousUser instance if missing. AuthenticationMiddleware will
    overwrite this with the real user when it runs.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not hasattr(request, "user"):
            request.user = AnonymousUser()
        return self.get_response(request)
