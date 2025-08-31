from django.urls import path
from . import views
from . import attendance_views
from django.contrib.auth import views as auth_views


app_name = "doctor_section"  # This is crucial for namespacing URLs

urlpatterns = [

    path("", views.doctor_dash, name="doctor_dash"),

    path("doctor_help/", views.doctor_help, name="doctor_help"),
    path("doctor_reviews/", views.doctor_reviews, name="doctor_reviews"),
    path("doctor_profile/", views.doctor_profile, name="doctor_profile"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # edit profile
    path("update-contact-info/", views.update_contact_info, name="update_contact_info"),
    path('update-profile-photo/', views.update_profile_photo, name='update_profile_photo'),
    path('get-date-restrictions/', views.get_date_restrictions, name='get_date_restrictions'),
    path("delete-support-ticket/<int:ticket_id>/", views.delete_support_ticket, name="delete_support_ticket"),
    path("review-log/<int:log_id>/", views.review_log, name="review_log"),
    path("batch-review/", views.batch_review, name="batch_review"),
    path("notifications/", views.notifications, name="notifications"),
    path("export-logs/", views.export_logs, name="export_logs"),

    # Attendance URLs
    path("take-attendance/", attendance_views.take_attendance, name="take_attendance"),
    path("attendance-history/", attendance_views.attendance_history, name="attendance_history"),
    path("attendance-summary/", attendance_views.attendance_summary, name="attendance_summary"),
    path("export-attendance/", attendance_views.export_attendance, name="export_attendance"),
    path("test-export/", attendance_views.test_export, name="test_export"),
    path("api/get-students-for-site/", attendance_views.get_students_for_site, name="get_students_for_site"),
    path("debug-doctor-status/", attendance_views.debug_doctor_status, name="debug_doctor_status"),
    path("debug-doctor-reviews/", views.debug_doctor_reviews, name="debug_doctor_reviews"),
]




