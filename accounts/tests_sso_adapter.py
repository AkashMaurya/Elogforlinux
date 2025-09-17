from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from accounts.adapters import CustomSocialAccountAdapter
from types import SimpleNamespace
from accounts.models import SSOAuditLog

User = get_user_model()


class FakeAccount:
    def __init__(self, provider='microsoft', extra_data=None):
        self.provider = provider
        self.extra_data = extra_data or {}


class FakeSocialLogin:
    def __init__(self, email, first_name='', last_name='', username=None, account_extra=None):
        # allauth typically provides a user model instance (unsaved) here; use real model
        self.user = User(email=email, username=username or email.split('@')[0])
        self.user.first_name = first_name
        self.user.last_name = last_name
        self.account = FakeAccount(provider='microsoft', extra_data=account_extra or {})
        self.state = {}

    def connect(self, request, user):
        # mimic allauth's connect by assigning the db user
        self.user = user


class SSOTestCase(TestCase):

    def setUp(self):
        # create a pre-existing user
        self.user = User.objects.create(email='existing@example.com', username='existing', first_name='Old', last_name='Name')
        self.adapter = CustomSocialAccountAdapter()

    def test_existing_user_updated_and_audit_written(self):
        social = FakeSocialLogin(email='existing@example.com', first_name='NewFirst', last_name='NewLast')
        req = SimpleNamespace(GET={}, POST={}, session={})

        # Call save_user which should link and update existing user
        result = self.adapter.save_user(req, social)
        self.assertEqual(result.pk, self.user.pk)
        u = User.objects.get(pk=self.user.pk)
        self.assertEqual(u.first_name, 'NewFirst')
        self.assertEqual(u.last_name, 'NewLast')
        # Audit log created
        logs = SSOAuditLog.objects.filter(user=u)
        self.assertTrue(logs.exists())
        log = logs.first()
        self.assertIn('first_name', log.changed_fields)
        self.assertIn('last_name', log.changed_fields)

    def test_new_user_created_as_defaultuser(self):
        social = FakeSocialLogin(email='newuser@example.com', first_name='N', last_name='U', username='newuser')
        req = SimpleNamespace(GET={}, POST={}, session={})
        result = self.adapter.save_user(req, social)
        self.assertIsNotNone(result.pk)
        u = User.objects.get(pk=result.pk)
        self.assertEqual(u.role, 'defaultuser')

    @override_settings(SSO_ROLE_MAPPING={'external_staff':'staff'}, SSO_ROLE_OVERRIDE=True)
    def test_role_mapping_override(self):
        # pre-existing user with student role
        u = User.objects.create(email='mapme@example.com', username='mapme', role='student')
        social = FakeSocialLogin(email='mapme@example.com', first_name='X', last_name='Y', account_extra={'roles': ['external_staff']})
        # attach account_extra to FakeSocialLogin properly
        social.account.extra_data = {'roles': ['external_staff']}
        req = SimpleNamespace(GET={}, POST={}, session={})
        res = self.adapter.save_user(req, social)
        u.refresh_from_db()
        self.assertEqual(u.role, 'staff')
        # Audit should include role change
        log = SSOAuditLog.objects.filter(user=u).first()
        self.assertIsNotNone(log)
        self.assertIn('role', log.changed_fields)
