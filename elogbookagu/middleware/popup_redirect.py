from django.http import HttpResponse
from django.urls import reverse
from django.conf import settings


class PopupRedirectMiddleware:
    """When SSO was initiated from a popup (session flag `sso_popup`),
    convert the normal HTTP redirect response into a small HTML page
    that instructs the opener window to navigate to the target URL and
    then closes the popup.

    If the user is authenticated at the time of the callback, prefer a
    role-based redirect (student/doctor/staff/admin) taken from the DB.
    This ensures that role changes made by admins are respected on next
    login.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        try:
            if request.session.get('sso_popup') and response.status_code in (301, 302, 303, 307):
                # Clear the flag so subsequent requests behave normally
                try:
                    del request.session['sso_popup']
                except Exception:
                    pass

                # Determine best target: prefer a role-based URL when we have
                # an authenticated user; reload from DB to pick up role changes.
                target = response.get('Location')
                try:
                    user = getattr(request, 'user', None)
                    if user and getattr(user, 'is_authenticated', False):
                        try:
                            # Reload user from DB so admin changes to role take effect
                            user = type(user).objects.filter(pk=user.pk).first() or user
                        except Exception:
                            pass

                        role_to_url = {
                            'defaultuser': reverse('defaultuser:default_home'),
                            'student': reverse('student_section:student_dash'),
                            'doctor': reverse('doctor_section:doctor_dash'),
                            'staff': reverse('staff_section:staff_dash'),
                            'admin': reverse('admin_section:admin_dash'),
                        }
                        role_target = role_to_url.get(getattr(user, 'role', None))
                        if role_target:
                            target = role_target

                except Exception:
                    # If anything goes wrong while computing role target, fall
                    # back to the original Location header.
                    pass

                if not target:
                    return response

                html = f"""
                <!doctype html>
                <html>
                <head>
                <meta charset='utf-8'>
                <title>Signing in…</title>
                <script>
                  try {{
                    if (window.opener) {{
                      window.opener.location.href = {repr(target)};
                    }} else {{
                      window.location.href = {repr(target)};
                    }}
                  }} catch (e) {{
                    document.write('<p><a href="' + {repr(target)} + '">Continue</a></p>');
                  }}
                  setTimeout(function() {{ window.close(); }}, 1500);
                </script>
                </head>
                <body>
                <p>Signing in… If you are not redirected, <a href="{target}">click here</a>.</p>
                </body>
                </html>
                """
                return HttpResponse(html)
        except Exception:
            pass

        return response
