from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),  # Add login view
    path('microsoft/direct/', views.microsoft_direct, name='microsoft_direct'),
    path('welcome/', views.welcome, name='welcome'),
    path('microsoft/state/', views.microsoft_state, name='microsoft_state'),
    path('post-login-redirect/', views.post_login_redirect, name='post_login_redirect'),
]

# Keep this file minimal: allauth registers the standard OAuth endpoints
# when `allauth.urls` is included in the project URLs. The custom routes
# above exist to allow server-side state creation before redirecting to
# the Microsoft authorize endpoint (used by our popup flow).
