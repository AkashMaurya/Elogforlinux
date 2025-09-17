from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model


User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class PostLoginRedirectTests(TestCase):
    def setUp(self):
        # Create a set of users with different roles
        self.users = {}
        base = dict(password='testpass123')
        roles = ['defaultuser', 'student', 'staff', 'doctor', 'admin']
        for i, role in enumerate(roles, start=1):
            email = f'user{i}@example.com'
            username = f'user{i}'
            # CustomUser.USERNAME_FIELD is 'email' — ensure we create user correctly
            user = User.objects.create_user(email=email, username=username, password=base['password'])
            user.role = role
            # ensure superuser remains admin if created as such
            if role == 'admin':
                user.is_superuser = False
            user.save()
            self.users[role] = user

        self.client = Client()

    def _assert_redirect_for_role(self, role):
        user = self.users[role]
        # Ensure user role was saved correctly
        user.refresh_from_db()
        self.assertEqual(user.role, role, f"Test setup error: user.role for {user.email} is {user.role} expected {role}")
        # Derive expected path by reversing the same named routes used by the view
        role_to_name = {
            'defaultuser': 'defaultuser:default_home',
            'student': 'student_section:student_dash',
            'staff': 'staff_section:staff_dash',
            'doctor': 'doctor_section:doctor_dash',
            'admin': 'admin_section:admin_dash',
        }
        expected_path = reverse(role_to_name.get(role))
        # Simulate authenticated session (SSO callback would authenticate)
        self.client.force_login(user)
        resp = self.client.get('/accounts/post-login-redirect/')
        # Should be a redirect
        self.assertIn(resp.status_code, (302, 301))
        # response.url is the redirect target in Django test client
        # It may be absolute (http://testserver/...) or a path; check endswith
        target = resp.url if hasattr(resp, 'url') else resp['Location']
        if not target.endswith(expected_path):
            # Add debug information to failure
            self.fail(f"Role {role} redirected to {target}, expected to end with {expected_path}")

    def test_defaultuser_redirects_to_defaultuser(self):
        self._assert_redirect_for_role('defaultuser')

    def test_student_redirects_to_student_section(self):
        self._assert_redirect_for_role('student')

    def test_staff_redirects_to_staff_section(self):
        self._assert_redirect_for_role('staff')

    def test_doctor_redirects_to_doctor_section(self):
        self._assert_redirect_for_role('doctor')

    def test_admin_redirects_to_admin_section(self):
        self._assert_redirect_for_role('admin')
