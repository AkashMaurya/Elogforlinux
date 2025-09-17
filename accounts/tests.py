from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.contrib.admin.sites import AdminSite
from django.test.client import Client
from django.urls import reverse

from .admin import CustomUserAdmin


User = get_user_model()


class AdminRoleSaveTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.site = AdminSite()

    def test_save_model_persists_role(self):
        # create a user
        u = User.objects.create(username="admintest", email="admintest@example.com")
        u.set_password("pass")
        u.save()

        # prepare admin, form-like object with cleaned_data
        class DummyForm:
            cleaned_data = {"role": "doctor"}

        admin = CustomUserAdmin(User, self.site)
        request = self.factory.post("/admin/")

        # call save_model as admin would
        admin.save_model(request, u, DummyForm(), change=True)

        u.refresh_from_db()
        self.assertEqual(u.role, "doctor")


class SessionInvalidationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_role_change_invalidates_sessions(self):
        # create and login a user to create a session
        u = User.objects.create(username="sessuser", email="sessuser@example.com")
        u.set_password("pass")
        u.save()

        logged = self.client.login(email="sessuser@example.com", password="pass")
        self.assertTrue(logged)

        # ensure there's at least one session in DB
        before = Session.objects.count()

        # change role and save
        u.role = "doctor"
        u.save()

        after = Session.objects.count()

        # sessions should be reduced (our invalidation deletes user's sessions)
        self.assertLessEqual(after, before)

        # ensure no session references this user id
        remaining = 0
        for s in Session.objects.filter(expire_date__isnull=False):
            try:
                data = s.get_decoded()
                if str(data.get("_auth_user_id")) == str(u.pk):
                    remaining += 1
            except Exception:
                pass

        self.assertEqual(remaining, 0)


class AdminGUIRoleChangeTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_admin_change_role_persists(self):
        # create a superuser and a normal user
        admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='adminpass')
        user = User.objects.create(username='target', email='target@example.com')
        user.set_password('pass')
        user.save()

        # force-login the admin to bypass CSRF/login steps
        self.client.force_login(admin)
        change_url = reverse('admin:accounts_customuser_change', args=[user.pk])
        resp = self.client.get(change_url, follow=True)
        self.assertIn(resp.status_code, (200, 302))

        # The admin form is available in context as 'adminform' when rendering
        form = None
        if resp.context and 'adminform' in resp.context:
            form = resp.context['adminform'].form
        else:
            # If the admin page redirected, try to load the change page without follow
            resp2 = self.client.get(change_url)
            if resp2.status_code == 200 and resp2.context and 'adminform' in resp2.context:
                form = resp2.context['adminform'].form

        self.assertIsNotNone(form, msg='Admin change form not found in response context')
        post_data = {}

        # Start with the form's initial data so we include required fields
        if hasattr(form, 'initial') and isinstance(form.initial, dict):
            # Copy only primitive values from initial (avoid FileField/File objects)
            for k, v in form.initial.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    post_data[k] = v
                else:
                    post_data[k] = ''

        # Ensure required fields are present
        post_data.setdefault('username', user.username)
        post_data.setdefault('email', user.email)
        # Change the role to 'doctor'
        post_data['role'] = 'doctor'
        post_data['_save'] = 'Save'

        # Ensure file fields are empty to avoid Storage lookups
        post_data.setdefault('profile_photo', '')

        # sanitize None values which the test client cannot encode
        for k, v in list(post_data.items()):
            if v is None:
                post_data[k] = ''

        post = self.client.post(change_url, post_data, follow=True)
        self.assertIn(post.status_code, (200, 302))

        user.refresh_from_db()
        self.assertEqual(user.role, 'doctor')
