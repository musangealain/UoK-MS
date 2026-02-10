"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.urls import path, include
from website.views import (
    home,
    portal_student,
    portal_lecturer,
    portal_admin,
    portal_staff,
    StudentLoginView,
    LecturerLoginView,
    AdminLoginView,
    StaffLoginView,
    student_signup,
    lecturer_signup,
    admin_signup,
    apply_step1,
    apply_step2,
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', home, name='home'),
    path('portal/student/', portal_student, name='portal_student'),
    path('portal/lecturer/', portal_lecturer, name='portal_lecturer'),
    path('portal/admin/', portal_admin, name='portal_admin'),
    path('portal/staff/', portal_staff, name='portal_staff'),
    path('portal/student/login/', StudentLoginView.as_view(), name='student_login'),
    path('portal/lecturer/login/', LecturerLoginView.as_view(), name='lecturer_login'),
    path('portal/admin/login/', AdminLoginView.as_view(), name='admin_login'),
    path('portal/staff/login/', StaffLoginView.as_view(), name='staff_login'),
    path('portal/student/signup/', student_signup, name='student_signup'),
    path('portal/lecturer/signup/', lecturer_signup, name='lecturer_signup'),
    path('portal/admin/signup/', admin_signup, name='admin_signup'),
    path('apply/', apply_step1, name='apply_step1'),
    path('apply/program/', apply_step2, name='apply_step2'),
    path('dashboard/', include('dashboard.urls')),
]
