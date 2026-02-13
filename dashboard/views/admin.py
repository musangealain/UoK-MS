from django.contrib.auth.decorators import login_required
import random
import string
import time

from django.contrib.auth.models import User
from django.db import IntegrityError, OperationalError
from django.db import transaction
from django.db.models import Max
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from dashboard.models import (
    AcademicModule,
    AcademicSession,
    Application,
    Department,
    Enrollment,
    Faculty,
    OFFICE_CHOICES,
    OFFICE_PURPOSE,
    Program,
    ProgramModule,
    StaffProfile,
    TeachingAssignment,
    UserProfile,
)

ADMIN_GROUPS = {
    "people.office_performance": {
        "title": "Office Performance",
        "items": [
            {"key": "people.office_performance.registrar_office", "title": "Registrar Office"},
            {"key": "people.office_performance.finance_office", "title": "Finance Office"},
            {"key": "people.office_performance.hr_office", "title": "HR Office"},
            {"key": "people.office_performance.academic_affairs", "title": "Academic Affairs"},
            {"key": "people.office_performance.admissions_office", "title": "Admissions Office"},
            {"key": "people.office_performance.e_learning_office", "title": "E-Learning Office"},
            {"key": "people.office_performance.library_services", "title": "Library Office"},
        ],
    },
    "people.student_performance": {
        "title": "Student Performance",
        "items": [
            {"key": "people.student_performance.enrollment_demographics", "title": "Enrollment & Demographics"},
            {"key": "people.student_performance.academic_results", "title": "Academic Results"},
            {"key": "people.student_performance.retention_progression", "title": "Retention & Progression"},
            {"key": "people.student_performance.satisfaction_outcomes", "title": "Satisfaction & Outcomes"},
        ],
    },
    "people.faculty_performance": {
        "title": "Faculty Performance",
        "items": [
            {"key": "people.faculty_performance.teaching_effectiveness", "title": "Teaching Effectiveness"},
            {"key": "people.faculty_performance.research_output", "title": "Research Output"},
            {"key": "people.faculty_performance.engagement_development", "title": "Engagement & Development"},
        ],
    },
    "academic.program_performance": {
        "title": "Program Performance",
        "items": [
            {"key": "academic.program_performance.business_school", "title": "Business School"},
            {"key": "academic.program_performance.computing_it", "title": "Computing & IT"},
            {"key": "academic.program_performance.law_school", "title": "Law School"},
            {"key": "academic.program_performance.short_courses", "title": "Short Courses"},
        ],
    },
    "academic.course_analytics": {
        "title": "Course Analytics",
        "items": [
            {"key": "academic.course_analytics.popularity_demand", "title": "Popularity & Demand"},
            {"key": "academic.course_analytics.pass_fail_rates", "title": "Pass/Fail Rates"},
            {"key": "academic.course_analytics.student_feedback", "title": "Student Feedback"},
        ],
    },
    "academic.learning_outcomes": {
        "title": "Learning Outcomes",
        "items": [
            {"key": "academic.learning_outcomes.graduate_competencies", "title": "Graduate Competencies"},
            {"key": "academic.learning_outcomes.employer_feedback", "title": "Employer Feedback"},
        ],
    },
    "financial.revenue_analysis": {
        "title": "Revenue Analysis",
        "items": [
            {"key": "financial.revenue_analysis.program_profitability", "title": "Program Profitability"},
            {"key": "financial.revenue_analysis.revenue_streams", "title": "Revenue Streams"},
            {"key": "financial.revenue_analysis.fee_collection_rates", "title": "Fee Collection Rates"},
        ],
    },
    "financial.cost_analysis": {
        "title": "Cost Analysis",
        "items": [
            {"key": "financial.cost_analysis.department_expenditure", "title": "Department Expenditure"},
            {"key": "financial.cost_analysis.cost_per_student", "title": "Cost per Student"},
            {"key": "financial.cost_analysis.resource_utilization", "title": "Resource Utilization"},
        ],
    },
    "financial.budget_forecasting": {
        "title": "Budget & Forecasting",
        "items": [
            {"key": "financial.budget_forecasting.budget_vs_actual", "title": "Budget vs. Actual"},
            {"key": "financial.budget_forecasting.three_year_projections", "title": "3-Year Projections"},
            {"key": "financial.budget_forecasting.roi_analysis", "title": "ROI Analysis"},
        ],
    },
}


def _admin_subnav_for_page(page: str):
    page = (page or "").strip()
    if not page:
        return None
    for group_key, group in ADMIN_GROUPS.items():
        if page == group_key or page.startswith(group_key + "."):
            items = []
            for raw in group.get("items", []):
                key = raw["key"]
                url_name = raw.get("url_name")
                if url_name:
                    href = reverse(url_name)
                else:
                    href = reverse("admin_placeholder", kwargs={"page": key})
                items.append(
                    {
                        "key": key,
                        "title": raw.get("title", key),
                        "href": href,
                    }
                )
            is_group_page = page == group_key
            title = group.get("title", group_key)
            active = next((i for i in items if i["key"] == page), None)
            page_title = active["title"] if active else title
            return {
                "group_key": group_key,
                "title": title,
                "items": items,
                "is_group_page": is_group_page,
                "page_title": page_title,
            }
    return None


def _maybe_add_admin_subnav(context: dict, current_page: str):
    subnav = _admin_subnav_for_page(current_page)
    if not subnav:
        return context
    context.update(
        {
            "subnav_title": subnav["title"],
            "subnav_items": subnav["items"],
            "subnav_is_group_page": subnav["is_group_page"],
        }
    )
    return context


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


def _get_active_office_head(office_code: str):
    return (
        StaffProfile.objects.select_related("user")
        .filter(office_code=office_code, is_active=True)
        .order_by("-created_at")
        .first()
    )


def _normalize_name_part(value: str) -> str:
    return (value or "").strip()


def _build_full_name(first_name: str, surname: str, last_name: str) -> str:
    parts = [first_name]
    if surname:
        parts.append(surname)
    parts.append(last_name)
    return " ".join([p for p in parts if p])


def _hire_office_head(*, office_code: str, first_name: str, last_name: str, surname: str = "", allow_replace: bool = False):
    office_code = (office_code or "").strip().upper()
    first_name = _normalize_name_part(first_name)
    surname = _normalize_name_part(surname)
    last_name = _normalize_name_part(last_name)
    valid_codes = {code for code, _label in OFFICE_CHOICES}
    if office_code not in valid_codes:
        raise ValueError("Invalid office code.")
    if not first_name:
        raise ValueError("First name is required.")
    if not last_name:
        raise ValueError("Last name is required.")

    if not allow_replace and _get_active_office_head(office_code):
        raise ValueError("This office already has an active head. Use replace or stop access first.")

    now = timezone.now()
    issue_year = int(now.year)
    yy = issue_year % 100
    full_name = _build_full_name(first_name, surname, last_name)

    for _ in range(3):
        try:
            with transaction.atomic():
                last_seq = (
                    StaffProfile.objects.filter(office_code=office_code, issue_year=issue_year)
                    .aggregate(Max("sequence"))
                    .get("sequence__max")
                    or 0
                )
                next_seq = int(last_seq) + 1
                staff_id = f"{office_code}{yy:02d}-{next_seq:03d}"
                password = _generate_password(10)

                user = User.objects.create_user(username=staff_id, password=password)
                user.first_name = first_name[:150]
                user.last_name = _build_full_name(surname, "", last_name)[:150]
                user.save(update_fields=["first_name", "last_name"])

                profile, _created = UserProfile.objects.get_or_create(user=user)
                profile.role = "staff"
                profile.save(update_fields=["role"])

                StaffProfile.objects.create(
                    user=user,
                    staff_id=staff_id,
                    office_code=office_code,
                    issue_year=issue_year,
                    sequence=next_seq,
                    first_name=first_name,
                    surname=surname,
                    last_name=last_name,
                    full_name=full_name,
                    assigned_password=password,
                )

            return {
                "office_code": office_code,
                "full_name": full_name,
                "staff_id": staff_id,
                "password": password,
            }
        except (OperationalError, IntegrityError):
            time.sleep(0.1)
            continue

    raise OperationalError("Could not allocate a unique staff id. Please retry.")


def _deactivate_office_head(office_code: str):
    head = _get_active_office_head(office_code)
    if not head:
        raise ValueError("No active office head to deactivate.")
    now = timezone.now()
    StaffProfile.objects.filter(pk=head.pk, is_active=True).update(
        is_active=False,
        deactivated_at=now,
    )
    head.user.is_active = False
    head.user.save(update_fields=["is_active"])
    return head
@login_required
def admin_dashboard(request):
    if not _is_admin(request.user):
        return redirect('home')
    students = _get_students_with_records()
    lecturers = _get_lecturers()
    active_office_heads = StaffProfile.objects.filter(is_active=True).count()
    total_staff = len(lecturers) + active_office_heads

    quick_stats = [
        {"label": "Total Students", "value": f"{len(students):,}", "delta": "8% YoY", "dir": "up"},
        {"label": "Total Staff", "value": f"{total_staff:,}", "delta": "5% YoY", "dir": "up"},
        {"label": "Retention Rate", "value": "88%", "delta": "2% YoY", "dir": "down"},
        {"label": "Graduation Rate", "value": "82%", "delta": "3% YoY", "dir": "up"},
        {"label": "Employment Rate", "value": "91%", "delta": "2% YoY", "dir": "up"},
    ]

    office_performance_top5 = [
        {"name": "Registrar", "code": "ARG", "score": "85%", "delta": "2%", "dir": "up", "status": "green"},
        {"name": "Finance", "code": "FIN", "score": "92%", "delta": "1%", "dir": "up", "status": "green"},
        {"name": "HR", "code": "HRM", "score": "75%", "delta": "5%", "dir": "up", "status": "yellow"},
        {"name": "Academic", "code": "ACA", "score": "95%", "delta": "3%", "dir": "up", "status": "green"},
        {"name": "Admissions", "code": "ADM", "score": "70%", "delta": "8%", "dir": "down", "status": "red"},
    ]

    financial_health = [
        {"label": "Revenue YTD", "value": "$4.2M", "delta": "12%", "dir": "up"},
        {"label": "Expenses YTD", "value": "$3.1M", "delta": "8%", "dir": "up"},
        {"label": "Net Surplus", "value": "$1.1M", "delta": "18%", "dir": "up"},
        {"label": "Collection Rate", "value": "92%", "delta": "3%", "dir": "up"},
        {"label": "Budget Variance", "value": "-2.5%", "delta": "", "dir": "flat"},
    ]

    recent_activity = [
        {"time": "10:30 AM", "text": "Registrar Office issued 45 transcripts"},
        {"time": "09:15 AM", "text": f"Finance Office processed payroll ({total_staff} staff)"},
        {"time": "08:00 AM", "text": "Admissions Office sent 23 offer letters"},
        {"time": "Yesterday", "text": "IT Department resolved 15 support tickets"},
    ]
    return render(
        request,
        'dashboard/admin/index.html',
        {
            'students': students,
            'lecturers': lecturers,
            'quick_stats': quick_stats,
            'office_performance_top5': office_performance_top5,
            'financial_health': financial_health,
            'recent_activity': recent_activity,
            'current_page': 'executive.institutional_dashboard',
        },
    )


@login_required
def admin_students(request):
    if not _is_admin(request.user):
        return redirect('home')
    students = _get_students_with_records()
    context = {
        "students": students,
        "current_page": "people.student_performance.enrollment_demographics",
    }
    _maybe_add_admin_subnav(context, context["current_page"])
    return render(
        request,
        'dashboard/admin/students.html',
        context,
    )


@login_required
def admin_lecturers(request):
    if not _is_admin(request.user):
        return redirect('home')
    lecturers = _get_lecturers()
    context = {
        "lecturers": lecturers,
        "current_page": "people.faculty_performance.teaching_load",
    }
    _maybe_add_admin_subnav(context, context["current_page"])
    return render(
        request,
        'dashboard/admin/lecturers.html',
        context,
    )


@login_required
def admin_applications(request):
    if not _is_admin(request.user):
        return redirect('home')
    applications = _get_applications()
    context = {
        "applications": applications,
        "current_page": "people.office_performance.admissions_office",
    }
    _maybe_add_admin_subnav(context, context["current_page"])
    return render(
        request,
        'dashboard/admin/applications.html',
        context,
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
def admin_academic_workspace(request):
    if not _is_admin(request.user):
        return redirect("home")

    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        try:
            if action == "create_faculty":
                code = (request.POST.get("code") or "").strip().upper()
                name = (request.POST.get("name") or "").strip()
                if not code or not name:
                    raise ValueError("Faculty code and name are required.")
                Faculty.objects.update_or_create(
                    code=code,
                    defaults={"name": name, "is_active": True},
                )
                request.session["academic_admin_flash"] = f"Faculty {code} saved."

            elif action == "create_department":
                faculty_id = int(request.POST.get("faculty_id") or 0)
                code = (request.POST.get("code") or "").strip().upper()
                name = (request.POST.get("name") or "").strip()
                if not faculty_id or not code or not name:
                    raise ValueError("Faculty, department code and name are required.")
                Department.objects.update_or_create(
                    faculty_id=faculty_id,
                    code=code,
                    defaults={"name": name, "is_active": True},
                )
                request.session["academic_admin_flash"] = f"Department {code} saved."

            elif action == "create_program":
                department_id = int(request.POST.get("department_id") or 0)
                code = (request.POST.get("code") or "").strip().upper()
                name = (request.POST.get("name") or "").strip()
                duration_years = int(request.POST.get("duration_years") or 4)
                if not department_id or not code or not name:
                    raise ValueError("Department, program code and name are required.")
                if duration_years < 1:
                    raise ValueError("Program duration must be at least 1 year.")
                Program.objects.update_or_create(
                    department_id=department_id,
                    code=code,
                    defaults={
                        "name": name,
                        "duration_years": duration_years,
                        "is_active": True,
                    },
                )
                request.session["academic_admin_flash"] = f"Program {code} saved."

            elif action == "create_module":
                code = (request.POST.get("code") or "").strip().upper()
                title = (request.POST.get("title") or "").strip()
                credit_hours = int(request.POST.get("credit_hours") or 3)
                if not code or not title:
                    raise ValueError("Module code and title are required.")
                if credit_hours < 1:
                    raise ValueError("Credit hours must be at least 1.")
                AcademicModule.objects.update_or_create(
                    code=code,
                    defaults={
                        "title": title,
                        "credit_hours": credit_hours,
                        "is_active": True,
                    },
                )
                request.session["academic_admin_flash"] = f"Module {code} saved."

            elif action == "create_session":
                year_start = int(request.POST.get("year_start") or 0)
                year_end = int(request.POST.get("year_end") or 0)
                semester = int(request.POST.get("semester") or 1)
                name = (request.POST.get("name") or "").strip()
                if not year_start or not year_end:
                    raise ValueError("Academic session years are required.")
                if year_end < year_start:
                    raise ValueError("End year cannot be before start year.")
                if semester not in {1, 2, 3}:
                    raise ValueError("Semester must be 1, 2, or 3.")
                if not name:
                    name = f"{year_start}/{year_end} - Semester {semester}"
                AcademicSession.objects.update_or_create(
                    year_start=year_start,
                    year_end=year_end,
                    semester=semester,
                    defaults={"name": name, "is_active": True},
                )
                request.session["academic_admin_flash"] = f"Session {name} saved."

            elif action == "map_program_module":
                program_id = int(request.POST.get("program_id") or 0)
                module_id = int(request.POST.get("module_id") or 0)
                semester = int(request.POST.get("semester") or 1)
                is_core = bool(request.POST.get("is_core"))
                if not program_id or not module_id:
                    raise ValueError("Program and module are required.")
                ProgramModule.objects.update_or_create(
                    program_id=program_id,
                    module_id=module_id,
                    defaults={"semester": semester, "is_core": is_core},
                )
                request.session["academic_admin_flash"] = "Program-module mapping saved."

            elif action == "create_teaching_assignment":
                instructor_id = int(request.POST.get("instructor_id") or 0)
                module_id = int(request.POST.get("module_id") or 0)
                session_id = int(request.POST.get("session_id") or 0)
                if not instructor_id or not module_id or not session_id:
                    raise ValueError("Lecturer, module and session are required.")
                instructor = (
                    User.objects.filter(pk=instructor_id, userprofile__role="lecturer")
                    .only("id")
                    .first()
                )
                if not instructor:
                    raise ValueError("Selected lecturer is invalid.")
                TeachingAssignment.objects.update_or_create(
                    instructor_id=instructor.id,
                    module_id=module_id,
                    session_id=session_id,
                    defaults={
                        "assigned_by": request.user,
                        "is_active": True,
                    },
                )
                request.session["academic_admin_flash"] = "Teaching assignment saved."

        except (ValueError, IntegrityError) as exc:
            request.session["academic_admin_error"] = str(exc)
        return redirect("admin_academic_workspace")

    faculties = Faculty.objects.filter(is_active=True).order_by("code")
    departments = Department.objects.select_related("faculty").order_by("faculty__code", "code")
    programs = Program.objects.select_related("department", "department__faculty").order_by("code")
    modules = AcademicModule.objects.filter(is_active=True).order_by("code")
    sessions = AcademicSession.objects.filter(is_active=True).order_by("-year_start", "-semester")
    program_modules = (
        ProgramModule.objects.select_related("program", "module")
        .order_by("program__code", "semester", "module__code")
    )
    lecturers = (
        User.objects.filter(userprofile__role="lecturer", is_active=True)
        .order_by("username")
    )
    assignments = (
        TeachingAssignment.objects.select_related("instructor", "module", "session")
        .order_by("-created_at")[:100]
    )
    enrollments = (
        Enrollment.objects.select_related("student", "module", "session", "program")
        .order_by("-enrolled_at")[:120]
    )

    return render(
        request,
        "dashboard/admin/academic_workspace.html",
        {
            "current_page": "academic.operations.workspace",
            "faculties": faculties,
            "departments": departments,
            "programs": programs,
            "modules": modules,
            "sessions": sessions,
            "program_modules": program_modules,
            "lecturers": lecturers,
            "assignments": assignments,
            "enrollments": enrollments,
            "flash": request.session.pop("academic_admin_flash", None),
            "flash_error": request.session.pop("academic_admin_error", None),
        },
    )


@login_required
def admin_placeholder(request, page):
    if not _is_admin(request.user):
        return redirect("home")
    title = page.replace("-", " ").replace(".", " / ").replace("/", " / ").title()
    subnav = _admin_subnav_for_page(page)
    if subnav and subnav.get("page_title"):
        title = subnav["page_title"]
    context = {
        "current_page": page,
        "page_title": title,
        "subnav_title": subnav["title"] if subnav else None,
        "subnav_items": subnav["items"] if subnav else None,
        "subnav_is_group_page": subnav["is_group_page"] if subnav else False,
    }

    if page == "executive.leadership":
        if request.method == "POST":
            action = request.POST.get("action")
            try:
                if action == "hire_office_head":
                    hire_result = _hire_office_head(
                        office_code=request.POST.get("office_code"),
                        first_name=request.POST.get("first_name"),
                        surname=request.POST.get("surname"),
                        last_name=request.POST.get("last_name"),
                    )
                    request.session["office_head_hire_result"] = hire_result
                    request.session["office_head_action"] = "Hired"
                elif action == "replace_office_head":
                    office_code = request.POST.get("office_code")
                    _deactivate_office_head(office_code)
                    hire_result = _hire_office_head(
                        office_code=office_code,
                        first_name=request.POST.get("first_name"),
                        surname=request.POST.get("surname"),
                        last_name=request.POST.get("last_name"),
                        allow_replace=True,
                    )
                    request.session["office_head_hire_result"] = hire_result
                    request.session["office_head_action"] = "Replaced"
                elif action == "deactivate_office_head":
                    office_code = request.POST.get("office_code")
                    head = _deactivate_office_head(office_code)
                    request.session["office_head_hire_result"] = {
                        "office_code": office_code,
                        "full_name": head.full_name,
                        "staff_id": head.staff_id,
                        "password": head.assigned_password,
                    }
                    request.session["office_head_action"] = "Access stopped"
            except ValueError as exc:
                request.session["office_head_hire_error"] = str(exc)
            return redirect("admin_placeholder", page=page)

        office_rows = []
        for code, label in OFFICE_CHOICES:
            head = _get_active_office_head(code)
            office_rows.append(
                {
                    "code": code,
                    "label": label,
                    "purpose": OFFICE_PURPOSE.get(code, ""),
                    "head": head,
                }
            )
        vacant_offices = [row for row in office_rows if not row["head"]]
        occupied_offices = [row for row in office_rows if row["head"]]

        context.update(
            {
                "office_rows": office_rows,
                "vacant_offices": vacant_offices,
                "occupied_offices": occupied_offices,
                "office_head_hire_result": request.session.pop("office_head_hire_result", None),
                "office_head_hire_error": request.session.pop("office_head_hire_error", None),
                "office_head_action": request.session.pop("office_head_action", None),
            }
        )
    return render(
        request,
        "dashboard/admin/placeholder.html",
        context,
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
