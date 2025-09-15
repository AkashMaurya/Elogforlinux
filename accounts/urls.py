from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),  # Add login view
    path('microsoft/direct/', views.microsoft_direct, name='microsoft_direct'),
    path('welcome/', views.welcome, name='welcome'),
    path('microsoft/state/', views.microsoft_state, name='microsoft_state'),
    path('post-login-redirect/', views.post_login_redirect, name='post_login_redirect'),
    path('debug-auth/', views.debug_auth_status, name='debug_auth_status'),  # Debug view - remove in production
    # Intercept allauth's 3rdparty redirect and handle it properly
    path('3rdparty/', views.social_connections_redirect, name='social_connections_redirect'),
]

# Keep this file minimal: allauth registers the standard OAuth endpoints
# when `allauth.urls` is included in the project URLs. The custom routes
# above exist to allow server-side state creation before redirecting to
# the Microsoft authorize endpoint (used by our popup flow).
