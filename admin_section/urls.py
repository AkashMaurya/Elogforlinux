from django.urls import path
from . import views  # For admin_dash, admin_blogs, etc.
from django.contrib.auth import views as auth_views
from .views_file.add_activity_views import (
    add_activity_type,
    edit_activity_type,
    delete_activity_type,
)
from .views_file.CoreDiaProSession_views import (
    core_dia_pro_session_list,
    core_dia_pro_session_create,
    core_dia_pro_session_update,
    core_dia_pro_session_delete,
    get_activity_types_by_department,
)

from .views_file.add_user import add_user, edit_user, delete_user, bulk_delete_users
from .views_file.add_year import add_year, edit_year, delete_year
from .views_file.add_elogyear import add_elogyear, edit_elogyear, delete_elogyear
from .views_file.add_department import add_department, edit_department, delete_department, get_year_sections
from .views_file.add_group import add_group, edit_group, delete_group, get_year_sections as group_get_year_sections
from .views_file.add_student import add_student, remove_from_group, download_sample_csv as student_download_sample_csv, search_students, edit_student, delete_student
from .views_file.add_doctor import add_doctor, remove_from_department, download_sample_csv as doctor_download_sample_csv, edit_doctor, delete_doctor
from .views_file.add_staff import add_staff, remove_from_department as remove_staff_from_department, download_sample_csv as staff_download_sample_csv, edit_staff, delete_staff
from .views_file.add_training_site import add_training_site, edit_training_site, delete_training_site
from .views_file.mapped_attendance_views import (
    mapped_attendance_list,
    mapped_attendance_create,
    mapped_attendance_edit,
    mapped_attendance_delete,
    mapped_attendance_detail,
    get_groups_by_year,
    get_training_sites_by_year,
    get_doctors_by_department,
)


app_name = "admin_section"

urlpatterns = [
    # Other URLs
    path("", views.admin_dash, name="admin_dash"),
    path("date_restrictions/", views.date_restrictions, name="date_restrictions"),

    # Blog URLs
    path("admin_blogs/", views.admin_blogs, name="admin_blogs"),
    path("blog/create/", views.blog_create, name="blog_create"),
    path("blog/<int:blog_id>/", views.blog_detail, name="blog_detail"),
    path("blog/<int:blog_id>/edit/", views.blog_edit, name="blog_edit"),
    path("blog/<int:blog_id>/delete/", views.blog_delete, name="blog_delete"),

    path("admin_support/", views.admin_support, name="admin_support"),
    path("admin_reviews/", views.admin_reviews, name="admin_reviews"),
    path("admin_profile/", views.admin_profile, name="admin_profile"),
    path("admin_final_records/", views.final_records, name="admin_final_records"),

    # Report URLs
    path("department_report/", views.department_report, name="department_report"),
    path("student_report/", views.student_report, name="student_report"),
    path("tutor_report/", views.tutor_report, name="tutor_report"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # Activity Type URLs
    path("add_activity_type/", add_activity_type, name="add_activity_type"),
    path(
        "edit_activity_type/<int:activity_type_id>/",
        edit_activity_type,
        name="edit_activity_type",
    ),
    path(
        "delete_activity_type/<int:activity_type_id>/",
        delete_activity_type,
        name="delete_activity_type",
    ),
    path(
        "api/activity-types/<int:department_id>/",
        get_activity_types_by_department,
        name="get_activity_types_by_department",
    ),
    path("add_user/", add_user, name="add_user"),
    path("add_year/", add_year, name="add_year"),
    path("add_elogyear/", add_elogyear, name="add_elogyear"),
    path("add_department/", add_department, name="add_department"),
    path("add_group/", add_group, name="add_group"),
    path("add_student/", add_student, name="add_student"),
    path("add_doctor/", add_doctor, name="add_doctor"),
    # Core Diagnosis Procedure Sessions URLs
    path("sessions/", core_dia_pro_session_list, name="core_dia_pro_session_list"),
    path(
        "sessions/create/",
        core_dia_pro_session_create,
        name="core_dia_pro_session_create",
    ),
    path(
        "sessions/edit/<int:pk>/",
        core_dia_pro_session_update,
        name="core_dia_pro_session_update",
    ),
    path(
        "sessions/delete/<int:pk>/",
        core_dia_pro_session_delete,
        name="core_dia_pro_session_delete",
    ),
    # Support Ticket URLs
    path(
        "resolve_ticket/<int:ticket_id>/", views.resolve_ticket, name="resolve_ticket"
    ),
    # Profile URLs
    path(
        "update-profile-photo/", views.update_profile_photo, name="update_profile_photo"
    ),
    path("update-contact-info/", views.update_contact_info, name="update_contact_info"),
    # Review URLs
    path("review-log/<int:log_id>/", views.review_log, name="review_log"),
    path("batch-review/", views.batch_review, name="batch_review"),
    path("notifications/", views.notifications, name="notifications"),
    path("delete-all-notifications/", views.delete_all_notifications, name="delete_all_notifications"),

    # Bulk Import URLs
    path("bulk-import-users/", views.bulk_import_users, name="bulk_import_users"),
    path("download-sample-csv/", views.download_sample_csv, name="download_sample_csv"),

    # Year Management URLs
    path("edit-year/<int:year_id>/", edit_year, name="edit_year"),
    path("delete-year/<int:year_id>/", delete_year, name="delete_year"),

    # User Management URLs
    path("edit-user/<int:user_id>/", edit_user, name="edit_user"),
    path("delete-user/<int:user_id>/", delete_user, name="delete_user"),
    path("bulk-delete-users/", bulk_delete_users, name="bulk_delete_users"),

    # Year Section Management URLs
    path("edit-elogyear/<int:section_id>/", edit_elogyear, name="edit_elogyear"),
    path("delete-elogyear/<int:section_id>/", delete_elogyear, name="delete_elogyear"),

    # Department Management URLs
    path("edit-department/<int:department_id>/", edit_department, name="edit_department"),
    path("delete-department/<int:department_id>/", delete_department, name="delete_department"),
    path("api/year-sections/<int:year_id>/", get_year_sections, name="get_year_sections"),

    # Group Management URLs
    path("edit-group/<int:group_id>/", edit_group, name="edit_group"),
    path("delete-group/<int:group_id>/", delete_group, name="delete_group"),
    path("api/group-year-sections/<int:year_id>/", group_get_year_sections, name="group_get_year_sections"),

    # Student Management URLs
    path("edit-student/<int:student_id>/", edit_student, name="edit_student"),
    path("delete-student/<int:student_id>/", delete_student, name="delete_student"),
    path("remove-student-from-group/<int:student_id>/", remove_from_group, name="remove_from_group"),
    path("download-student-sample-csv/", student_download_sample_csv, name="student_download_sample_csv"),

    # Doctor Management URLs
    path("edit-doctor/<int:doctor_id>/", edit_doctor, name="edit_doctor"),
    path("delete-doctor/<int:doctor_id>/", delete_doctor, name="delete_doctor"),
    path("remove-doctor-from-department/<int:doctor_id>/<int:department_id>/", remove_from_department, name="remove_from_department"),
    path("download-doctor-sample-csv/", doctor_download_sample_csv, name="doctor_download_sample_csv"),

    # Staff Management URLs
    path("add_staff/", add_staff, name="add_staff"),
    path("edit-staff/<int:staff_id>/", edit_staff, name="edit_staff"),
    path("delete-staff/<int:staff_id>/", delete_staff, name="delete_staff"),
    path("remove-staff-from-department/<int:staff_id>/<int:department_id>/", remove_staff_from_department, name="remove_staff_from_department"),
    path("download-staff-sample-csv/", staff_download_sample_csv, name="download_staff_sample_csv"),

    # Training Site Management URLs
    path("add_training_site/", add_training_site, name="add_training_site"),
    path("edit-training-site/<int:training_site_id>/", edit_training_site, name="edit_training_site"),
    path("delete-training-site/<int:training_site_id>/", delete_training_site, name="delete_training_site"),

    # Mapped Attendance URLs
    path("mapped-attendance/", mapped_attendance_list, name="mapped_attendance_list"),
    path("mapped-attendance/create/", mapped_attendance_create, name="mapped_attendance_create"),
    path("mapped-attendance/<int:pk>/", mapped_attendance_detail, name="mapped_attendance_detail"),
    path("mapped-attendance/<int:pk>/edit/", mapped_attendance_edit, name="mapped_attendance_edit"),
    path("mapped-attendance/<int:pk>/delete/", mapped_attendance_delete, name="mapped_attendance_delete"),
    path("api/doctors-by-department/", get_doctors_by_department, name="get_doctors_by_department"),

    # Bulk Add Users URLs
    path('bulk-add-users/', views.bulk_add_users, name='bulk_add_users'),
    path('download-user-template/', views.download_user_template, name='download_user_template'),
    path('export-users/', views.export_users, name='export_users'),
    path('export-department-logs/', views.export_department_logs, name='export_department_logs'),

    # AJAX endpoints
    path('api/get-user-data/', views.get_user_data, name='get_user_data'),
    path('api/search-students/', search_students, name='search_students'),
    path('api/groups-by-year/', get_groups_by_year, name='get_groups_by_year'),
    path('api/training-sites-by-year/', get_training_sites_by_year, name='get_training_sites_by_year'),
]
