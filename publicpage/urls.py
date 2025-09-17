from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("", views.home, name="home_page"),
    # path("about/", views.about, name="about_page"),
    # path("resources/", views.resources, name="resources_page"),
    path("update/", views.update, name="update_page"),
    path("blog/<int:blog_id>/", views.blog_detail, name="blog_detail"),
    path("ebookjournals/", views.ebookjournals, name="ebookjournals_page"),
    path(
        "ebookjournals/<str:pdf_name>/",
        views.ebookjournals,
        name="ebookjournals_download",
    ),



    path("login/", views.login, name="login"),
    # Password reset URLs
    path(
        "password_reset/", auth_views.PasswordResetView.as_view(), name="password_reset"
    ),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
