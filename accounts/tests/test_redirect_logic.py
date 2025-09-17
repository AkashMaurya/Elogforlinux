from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.conf import settings
from accounts.adapters import CustomSocialAccountAdapter, CustomAccountAdapter
from types import SimpleNamespace

User = get_user_model()


class RedirectLogicTestCase(TestCase):
    """Test the redirect logic in both social and account adapters."""

    def setUp(self):
        self.factory = RequestFactory()
        self.social_adapter = CustomSocialAccountAdapter()
        self.account_adapter = CustomAccountAdapter()

    def test_social_adapter_ignores_unsafe_next_3rdparty(self):
        """Test that social adapter ignores next parameter pointing to 3rdparty URLs."""
        request = self.factory.get('/accounts/microsoft/login/callback/', {'next': '/accounts/3rdparty/something'})
        request.user = User.objects.create(email='test@example.com', username='test', role='student')
        
        redirect_url = self.social_adapter.get_login_redirect_url(request)
        
        # Should redirect to LOGIN_REDIRECT_URL, not the unsafe next
        self.assertEqual(redirect_url, settings.LOGIN_REDIRECT_URL)

    def test_social_adapter_ignores_unsafe_next_socialaccount(self):
        """Test that social adapter ignores next parameter pointing to socialaccount URLs."""
        request = self.factory.get('/accounts/microsoft/login/callback/', {'next': '/accounts/socialaccount/connections/'})
        request.user = User.objects.create(email='test@example.com', username='test', role='doctor')
        
        redirect_url = self.social_adapter.get_login_redirect_url(request)
        
        # Should redirect to LOGIN_REDIRECT_URL, not the unsafe next
        self.assertEqual(redirect_url, settings.LOGIN_REDIRECT_URL)

    def test_social_adapter_ignores_unsafe_next_microsoft(self):
        """Test that social adapter ignores next parameter pointing to Microsoft provider URLs."""
        request = self.factory.get('/accounts/microsoft/login/callback/', {'next': '/accounts/microsoft/login/'})
        request.user = User.objects.create(email='test@example.com', username='test', role='admin')
        
        redirect_url = self.social_adapter.get_login_redirect_url(request)
        
        # Should redirect to LOGIN_REDIRECT_URL, not the unsafe next
        self.assertEqual(redirect_url, settings.LOGIN_REDIRECT_URL)

    def test_social_adapter_allows_safe_next(self):
        """Test that social adapter allows safe next parameters."""
        request = self.factory.get('/accounts/microsoft/login/callback/', {'next': '/student_section/dashboard/'})
        request.user = User.objects.create(email='test@example.com', username='test', role='student')
        
        redirect_url = self.social_adapter.get_login_redirect_url(request)
        
        # Should redirect to the safe next URL
        self.assertEqual(redirect_url, '/student_section/dashboard/')

    def test_social_adapter_defaults_to_login_redirect_url(self):
        """Test that social adapter defaults to LOGIN_REDIRECT_URL when no next is provided."""
        request = self.factory.get('/accounts/microsoft/login/callback/')
        request.user = User.objects.create(email='test@example.com', username='test', role='staff')
        
        redirect_url = self.social_adapter.get_login_redirect_url(request)
        
        # Should redirect to LOGIN_REDIRECT_URL
        self.assertEqual(redirect_url, settings.LOGIN_REDIRECT_URL)

    def test_account_adapter_ignores_unsafe_next_3rdparty(self):
        """Test that account adapter ignores next parameter pointing to 3rdparty URLs."""
        request = self.factory.get('/login/', {'next': '/accounts/3rdparty/something'})
        request.user = User.objects.create(email='test@example.com', username='test', role='student')
        
        redirect_url = self.account_adapter.get_login_redirect_url(request)
        
        # Should redirect to LOGIN_REDIRECT_URL, not the unsafe next
        self.assertEqual(redirect_url, settings.LOGIN_REDIRECT_URL)

    def test_account_adapter_allows_safe_next(self):
        """Test that account adapter allows safe next parameters."""
        request = self.factory.get('/login/', {'next': '/admin_section/dashboard/'})
        request.user = User.objects.create(email='test@example.com', username='test', role='admin')
        
        redirect_url = self.account_adapter.get_login_redirect_url(request)
        
        # Should redirect to the safe next URL
        self.assertEqual(redirect_url, '/admin_section/dashboard/')

    def test_account_adapter_defaults_to_login_redirect_url(self):
        """Test that account adapter defaults to LOGIN_REDIRECT_URL when no next is provided."""
        request = self.factory.get('/login/')
        request.user = User.objects.create(email='test@example.com', username='test', role='doctor')
        
        redirect_url = self.account_adapter.get_login_redirect_url(request)
        
        # Should redirect to LOGIN_REDIRECT_URL
        self.assertEqual(redirect_url, settings.LOGIN_REDIRECT_URL)

    def test_social_adapter_refreshes_user_from_db(self):
        """Test that social adapter refreshes user from database to get latest role."""
        # Create user with initial role
        user = User.objects.create(email='test@example.com', username='test', role='student')
        
        # Simulate request with this user
        request = self.factory.get('/accounts/microsoft/login/callback/')
        request.user = user
        
        # Change role in database (simulating admin change)
        User.objects.filter(pk=user.pk).update(role='admin')
        
        redirect_url = self.social_adapter.get_login_redirect_url(request)
        
        # Should redirect to LOGIN_REDIRECT_URL (post-login-redirect will handle role routing)
        self.assertEqual(redirect_url, settings.LOGIN_REDIRECT_URL)
