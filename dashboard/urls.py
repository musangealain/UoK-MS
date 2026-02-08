from django.urls import path
from dashboard.views.student import student_dashboard, applicant_dashboard
from dashboard.views.lecturer import lecturer_dashboard
from dashboard.views.admin import (
    admin_dashboard,
    admin_students,
    admin_lecturers,
    admin_applications,
    application_decision,
    application_delete,
    user_delete,
)
urlpatterns = [
    path('student/', student_dashboard, name='student_dashboard'),
    path('applicant/', applicant_dashboard, name='applicant_dashboard'),
    path('lecturer/', lecturer_dashboard, name='lecturer_dashboard'),
    path('admin/', admin_dashboard, name='admin_dashboard'),
    path('admin/students/', admin_students, name='admin_students'),
    path('admin/lecturers/', admin_lecturers, name='admin_lecturers'),
    path('admin/applications/', admin_applications, name='admin_applications'),
    path('admin/applications/<int:application_id>/decision/', application_decision, name='application_decision'),
    path('admin/applications/<int:application_id>/delete/', application_delete, name='application_delete'),
    path('admin/users/<int:user_id>/delete/', user_delete, name='user_delete'),
]
