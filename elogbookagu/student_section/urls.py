# student_section/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
app_name = "student_section"

urlpatterns = [
    path("", views.student_dash, name="student_dash"),

    path("student_support/", views.student_support, name="student_support"),
    path("student_elog/", views.student_elog, name="student_elog"),
    path("student_profile/", views.student_profile, name="student_profile"),
    path(
        "student_final_records/",
        views.student_final_records,
        name="student_final_records",
    ),
    # ye django ka logout class based view jo apne aap logout karwa dega if user want to log out
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # edit profile
    path("update-contact-info/", views.update_contact_info, name="update_contact_info"),
    path("update_biography/", views.update_biography, name="update_biography"),
    path("update_profile_photo/", views.update_profile_photo, name="update_profile_photo"),
    path("get-student-info/", views.get_student_info, name="get_student_info"),
    path(
        "get-departments-by-year/",
        views.get_departments_by_year,
        name="get_departments_by_year",
    ),
    # Log editing and deletion
    path("edit-log/<int:log_id>/", views.edit_log, name="edit_log"),
    path("delete-log/<int:log_id>/", views.delete_log, name="delete_log"),
    path("get-activity-types/", views.get_activity_types, name="get_activity_types"),
    path("get-core-diagnosis/", views.get_core_diagnosis, name="get_core_diagnosis"),
    path("get-tutors/", views.get_tutors, name="get_tutors"),
    path("get-date-restrictions/", views.get_date_restrictions, name="get_date_restrictions"),
    path("generate-records-pdf/", views.generate_records_pdf, name="generate_records_pdf"),
    path("delete-support-ticket/<int:ticket_id>/", views.delete_support_ticket, name="delete_support_ticket"),
    path("notifications/", views.notifications, name="notifications"),
    path("get-log-details/<int:log_id>/", views.get_log_details, name="get_log_details"),
    path("export-final-records-excel/", views.export_final_records_excel, name="export_final_records_excel"),
]
