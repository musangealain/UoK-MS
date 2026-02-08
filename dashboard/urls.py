from django.urls import path
from dashboard.views.student import student_dashboard, applicant_dashboard
from dashboard.views.lecturer import lecturer_dashboard
from dashboard.views.admin import admin_dashboard, application_decision, application_delete, user_delete
urlpatterns = [
    path('student/', student_dashboard, name='student_dashboard'),
    path('applicant/', applicant_dashboard, name='applicant_dashboard'),
    path('lecturer/', lecturer_dashboard, name='lecturer_dashboard'),
    path('admin/', admin_dashboard, name='admin_dashboard'),
    path('admin/applications/<int:application_id>/decision/', application_decision, name='application_decision'),
    path('admin/applications/<int:application_id>/delete/', application_delete, name='application_delete'),
    path('admin/users/<int:user_id>/delete/', user_delete, name='user_delete'),
]
