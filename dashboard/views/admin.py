from django.contrib.auth.decorators import login_required
import random
import string
import time

from django.contrib.auth.models import User
from django.db import OperationalError
from django.db import transaction
from django.db.models import Max
from django.shortcuts import render, redirect
from dashboard.models import Application, UserProfile


def _is_admin(user):
    profile = getattr(user, "userprofile", None)
    return user.is_staff or user.is_superuser or (profile and profile.role == 'admin')


def _get_students_with_records():
    students = list(
        User.objects.select_related('userprofile')
        .filter(userprofile__role='student', userprofile__student_status='enrolled')
        .exclude(username__startswith='REG')
        .order_by('username')
    )
    student_numbers = [u.username for u in students]
    application_map = {
        a.student_number: a
        for a in Application.objects.filter(student_number__in=student_numbers)
    }
    for u in students:
        u.application_record = application_map.get(u.username)
    return students


def _get_lecturers():
    return (
        User.objects.select_related('userprofile')
        .filter(userprofile__role='lecturer')
        .order_by('username')
    )


def _get_applications():
    return (
        Application.objects.exclude(status='approved')
        .order_by('-created_at')[:50]
    )
@login_required
def admin_dashboard(request):
    if not _is_admin(request.user):
        return redirect('home')
    students = _get_students_with_records()
    lecturers = _get_lecturers()
    return render(
        request,
        'dashboard/admin/index.html',
        {
            'students': students,
            'lecturers': lecturers,
            'current_page': 'dashboard',
        },
    )


@login_required
def admin_students(request):
    if not _is_admin(request.user):
        return redirect('home')
    students = _get_students_with_records()
    return render(
        request,
        'dashboard/admin/students.html',
        {'students': students, 'current_page': 'students'},
    )


@login_required
def admin_lecturers(request):
    if not _is_admin(request.user):
        return redirect('home')
    lecturers = _get_lecturers()
    return render(
        request,
        'dashboard/admin/lecturers.html',
        {'lecturers': lecturers, 'current_page': 'lecturers'},
    )


@login_required
def admin_applications(request):
    if not _is_admin(request.user):
        return redirect('home')
    applications = _get_applications()
    return render(
        request,
        'dashboard/admin/applications.html',
        {'applications': applications, 'current_page': 'applications'},
    )


def _next_student_number():
    last_number = Application.objects.exclude(student_number__isnull=True).aggregate(
        Max('student_number')
    )['student_number__max']
    if last_number:
        next_number = int(last_number) + 1
    else:
        next_number = 26000001
    return f"{next_number:08d}"


def _generate_password(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def _unique_student_number():
    candidate = int(_next_student_number())
    while User.objects.filter(username=f"{candidate:08d}").exists():
        candidate += 1
    return f"{candidate:08d}"


@login_required
def application_decision(request, application_id):
    if not _is_admin(request.user):
        return redirect('home')
    if request.method != 'POST':
        return redirect('admin_dashboard')
    decision = request.POST.get('decision')
    if decision not in {'approve', 'reject'}:
        return redirect('admin_dashboard')

    success = False
    for _ in range(3):
        try:
            with transaction.atomic():
                try:
                    application = Application.objects.get(pk=application_id)
                except Application.DoesNotExist:
                    return redirect('admin_dashboard')
                if application.status != 'under_review':
                    return redirect('admin_dashboard')
                if decision == 'approve':
                    application.status = 'approved'
                    if not application.student_number:
                        application.student_number = _unique_student_number()
                    if not application.issued_password:
                        application.issued_password = _generate_password()
                    application.save(update_fields=['status', 'student_number', 'issued_password'])

                    applicant_user = User.objects.filter(username=application.reg_number).first()
                    if applicant_user and applicant_user.is_active:
                        applicant_user.is_active = False
                        applicant_user.set_unusable_password()
                        applicant_user.save()
                        UserProfile.objects.filter(user=applicant_user).update(student_status='applicant')

                    if not User.objects.filter(username=application.student_number).exists():
                        new_user = User.objects.create_user(
                            username=application.student_number,
                            email=application.email,
                            password=application.issued_password,
                        )
                        profile, _ = UserProfile.objects.get_or_create(user=new_user)
                        profile.role = 'student'
                        profile.student_status = 'enrolled'
                        profile.save()
                else:
                    application.status = 'rejected'
                    application.save(update_fields=['status'])
            success = True
            break
        except OperationalError:
            time.sleep(0.1)
            continue
    if not success:
        return redirect('admin_dashboard')

    return redirect('admin_dashboard')


@login_required
def application_delete(request, application_id):
    if not _is_admin(request.user):
        return redirect('home')
    if request.method != 'POST':
        return redirect('admin_dashboard')
    Application.objects.filter(pk=application_id).delete()
    return redirect('admin_dashboard')


@login_required
def user_delete(request, user_id):
    if not _is_admin(request.user):
        return redirect('home')
    if request.method != 'POST':
        return redirect('admin_dashboard')
    if request.user.id == user_id:
        return redirect('admin_dashboard')
    User.objects.filter(pk=user_id).delete()
    return redirect('admin_dashboard')
