# admin_section/views_file/__init__.py
from .add_activity_views import (
    add_activity_type,
    edit_activity_type,
    delete_activity_type,
)
from .CoreDiaProSession_views import (
    core_dia_pro_session_list,
    core_dia_pro_session_create,
    core_dia_pro_session_update,
    core_dia_pro_session_delete,
    get_activity_types_by_department,  # Added this import
)


from .resources import CoreDiaProSessionResource

from .add_user import add_user
from .add_year import add_year
from .add_elogyear import add_elogyear
from .add_department import add_department
from .add_group import add_group
from .add_student import add_student
from .add_doctor import add_doctor
from .add_training_site import add_training_site, edit_training_site, delete_training_site
from .mapped_attendance_views import (
    mapped_attendance_list,
    mapped_attendance_create,
    mapped_attendance_edit,
    mapped_attendance_delete,
    mapped_attendance_detail,
    get_groups_by_year,
    get_training_sites_by_year,
)
