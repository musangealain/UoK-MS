from django.urls import path
from dashboard.views.student import student_dashboard
from dashboard.views.lecturer import lecturer_dashboard
from dashboard.views.admin import admin_dashboard
urlpatterns = [
    path('student/', student_dashboard, name='student_dashboard'),
    path('lecturer/', lecturer_dashboard, name='lecturer_dashboard'),
    path('admin/', admin_dashboard, name='admin_dashboard'),
]
