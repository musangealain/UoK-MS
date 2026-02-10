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


def _kpi_traffic_light(value, green_threshold=None, yellow_threshold=None, invert=False):
    """
    Simple helper for placeholder KPIs.
    - If invert=False: higher is better (e.g., retention rate).
    - If invert=True: lower is better (e.g., dropout rate).
    Thresholds define the boundary between green/yellow/red.
    """
    if value is None or green_threshold is None or yellow_threshold is None:
        return "yellow"
    score = -value if invert else value
    green = -green_threshold if invert else green_threshold
    yellow = -yellow_threshold if invert else yellow_threshold
    if score >= green:
        return "green"
    if score >= yellow:
        return "yellow"
    return "red"
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
            'current_page': 'executive.institutional_dashboard',
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
        {'students': students, 'current_page': 'people.student_performance.enrollment_demographics'},
    )


@login_required
def admin_lecturers(request):
    if not _is_admin(request.user):
        return redirect('home')
    lecturers = _get_lecturers()
    return render(
        request,
        'dashboard/admin/lecturers.html',
        {'lecturers': lecturers, 'current_page': 'people.faculty_performance.teaching_load'},
    )


@login_required
def admin_applications(request):
    if not _is_admin(request.user):
        return redirect('home')
    applications = _get_applications()
    return render(
        request,
        'dashboard/admin/applications.html',
        {'applications': applications, 'current_page': 'people.office_performance.admissions_office'},
    )


@login_required
def admin_kpi_monitor(request):
    if not _is_admin(request.user):
        return redirect('home')

    students = _get_students_with_records()
    lecturers = _get_lecturers()
    pending_applications = _get_applications()

    # Placeholder metrics: wire these to real models later.
    total_students = len(students)
    total_lecturers = len(lecturers)
    student_staff_ratio = round(total_students / max(total_lecturers, 1), 1)

    kpis = [
        {
            "group": "Enrollment Health",
            "items": [
                {"label": "Total Students", "value": total_students, "unit": "", "status": "green"},
                {"label": "Growth Trend", "value": 3.2, "unit": "%", "status": "yellow"},
                {"label": "Retention Rate", "value": 88.0, "unit": "%", "status": _kpi_traffic_light(88.0, 90.0, 80.0)},
                {"label": "Dropout Rate", "value": 4.8, "unit": "%", "status": _kpi_traffic_light(4.8, 3.0, 6.0, invert=True)},
            ],
        },
        {
            "group": "Financial Health",
            "items": [
                {"label": "Revenue", "value": 24.5, "unit": "M RWF", "status": "green"},
                {"label": "Expenses", "value": 18.1, "unit": "M RWF", "status": "yellow"},
                {"label": "Program Profitability", "value": 9.6, "unit": "%", "status": "yellow"},
                {"label": "Cash Flow Trend", "value": 1.2, "unit": "%", "status": "green"},
            ],
        },
        {
            "group": "Academic Performance",
            "items": [
                {"label": "Graduation Rate", "value": 74.0, "unit": "%", "status": _kpi_traffic_light(74.0, 80.0, 65.0)},
                {"label": "Pass Rate", "value": 82.0, "unit": "%", "status": _kpi_traffic_light(82.0, 85.0, 75.0)},
                {"label": "Student Satisfaction", "value": 4.1, "unit": "/5", "status": _kpi_traffic_light(4.1, 4.3, 3.8)},
                {"label": "At-Risk Programs", "value": 2, "unit": "", "status": "red"},
            ],
        },
        {
            "group": "Staff Performance",
            "items": [
                {"label": "Total Lecturers", "value": total_lecturers, "unit": "", "status": "green"},
                {"label": "Student-Staff Ratio", "value": student_staff_ratio, "unit": "", "status": _kpi_traffic_light(student_staff_ratio, 18.0, 25.0, invert=True)},
                {"label": "Research Output", "value": 12, "unit": " pubs", "status": "yellow"},
                {"label": "Workload Balance", "value": 0.72, "unit": "", "status": "yellow"},
            ],
        },
    ]

    return render(
        request,
        "dashboard/admin/kpi_monitor.html",
        {
            "current_page": "executive.strategic_kpis",
            "kpis": kpis,
            "pending_applications_count": len(pending_applications),
        },
    )


@login_required
def admin_placeholder(request, page):
    if not _is_admin(request.user):
        return redirect("home")
    title = page.replace("-", " ").replace(".", " / ").replace("/", " / ").title()
    return render(
        request,
        "dashboard/admin/placeholder.html",
        {
            "current_page": page,
            "page_title": title,
        },
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
