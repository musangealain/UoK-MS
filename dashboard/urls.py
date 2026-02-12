from django.urls import path
from dashboard.views.student import student_dashboard, applicant_dashboard
from dashboard.views.lecturer import (
    lecturer_dashboard,
    lecturer_courses,
    lecturer_course_assignments,
    lecturer_timetable,
    lecturer_materials,
    lecturer_student_lists,
    lecturer_course_enrollments,
    lecturer_attendance_sessions,
    lecturer_attendance_records,
)
from dashboard.views.admin import (
    admin_dashboard,
    admin_lecturers,
    admin_kpi_monitor,
    admin_placeholder,
    user_delete,
)
from dashboard.views.staff import staff_dashboard, staff_office_dashboard, staff_office_module
urlpatterns = [
    path('student/', student_dashboard, name='student_dashboard'),
    path('applicant/', applicant_dashboard, name='applicant_dashboard'),
    path('lecturer/', lecturer_dashboard, name='lecturer_dashboard'),
    path('lecturer/courses/', lecturer_courses, name='lecturer_courses'),
    path('lecturer/course-assignments/', lecturer_course_assignments, name='lecturer_course_assignments'),
    path('lecturer/timetable/', lecturer_timetable, name='lecturer_timetable'),
    path('lecturer/materials/', lecturer_materials, name='lecturer_materials'),
    path('lecturer/student-lists/', lecturer_student_lists, name='lecturer_student_lists'),
    path('lecturer/course-enrollments/', lecturer_course_enrollments, name='lecturer_course_enrollments'),
    path('lecturer/attendance-sessions/', lecturer_attendance_sessions, name='lecturer_attendance_sessions'),
    path('lecturer/attendance-records/', lecturer_attendance_records, name='lecturer_attendance_records'),
    path('admin/', admin_dashboard, name='admin_dashboard'),
    path('admin/kpis/', admin_kpi_monitor, name='admin_kpi_monitor'),
    path('admin/sm/<path:page>/', admin_placeholder, name='admin_placeholder'),
    path('admin/lecturers/', admin_lecturers, name='admin_lecturers'),
    path('admin/users/<int:user_id>/delete/', user_delete, name='user_delete'),
    path('staff/', staff_dashboard, name='staff_dashboard'),
    path('staff/<str:office_code>/', staff_office_dashboard, name='staff_office_dashboard'),
    path('staff/<str:office_code>/<slug:module_slug>/', staff_office_module, name='staff_office_module'),
]
