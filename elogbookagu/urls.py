"""
URL configuration for elogbookagu project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from .views import set_theme, custom_400, custom_403, custom_404, custom_500
from accounts import views as accounts_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.static import serve


urlpatterns = [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    path("admin1@admin/", admin.site.urls),
    path("", include("publicpage.urls")),
    # Directly register the welcome route to avoid namespace collisions
    path('accounts/welcome/', accounts_views.welcome, name='accounts_welcome'),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("doctors/", include("doctor_section.urls")),
    path("admin_section/", include("admin_section.urls")),
    path("defaultuser/", include(("defaultuser.urls", "defaultuser"), namespace="defaultuser")),
    path("staff_section/", include("staff_section.urls")),
    path("student_section/", include("student_section.urls")),
    path("accounts/", include("allauth.urls")),
    path("set-theme/", set_theme, name="set_theme"),
]



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Error handlers
handler400 = custom_400
handler403 = custom_403
handler404 = custom_404
handler500 = custom_500
