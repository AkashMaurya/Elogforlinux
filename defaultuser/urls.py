from django.urls import path
from . import views

app_name = 'defaultuser'

urlpatterns = [
    # Default landing for newly-created or default users
    path('', views.default_user_view, name='default_home'),
    # Additional routes are intentionally kept in the `accounts` app.
]
