import random
import string
import time

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError, OperationalError
from django.db import transaction
from django.db.models import Max
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

from dashboard.models import (
    AcademicModule,
    AcademicSession,
    Application,
    Enrollment,
    LecturerProfile,
    MODULE_CHOICES,
    OFFICE_CHOICES,
    OFFICE_PURPOSE,
    Program,
    ProgramModule,
    UserProfile,
)


def _is_staff(user):
    profile = getattr(user, "userprofile", None)
    return bool(profile and profile.role == "staff")


OFFICE_FEATURES = {
    "ARG": [
        "Student registration & enrollment records",
        "Transcripts and academic record management",
        "Course allocation and academic records",
    ],
    "FIN": [
        "Tuition & fee payments tracking",
        "Budgeting and expenditure tracking",
        "Payroll summaries and procurement",
    ],
    "HRM": [
        "Staff records management",
        "Recruitment and performance tracking",
        "Leave management and training programs",
    ],
    "ACA": [
        "Curriculum and course offerings oversight",
        "Faculty workload monitoring",
        "Quality assurance & accreditation compliance",
    ],
    "ADM": [
        "Admission decisions and offer letter management",
        "Enrollment statistics and intake monitoring",
        "Student support services management",
    ],
    "ELE": [
        "LMS / online course management",
        "Virtual classrooms support",
        "Digital content development workflows",
    ],
    "LIB": [
        "Library resource management",
        "Book lending & e-resources access",
        "Research support and user services",
    ],
}


OFFICE_MODULES = {
    "ARG": [
        {
            "slug": "student-registration",
            "title": "Student Registration",
            "description": "Register students, update enrollment details, and manage registration status.",
        },
        {
            "slug": "enrollment-records",
            "title": "Enrollment Records",
            "description": "View and maintain enrollment records and student academic history.",
        },
        {
            "slug": "transcripts",
            "title": "Transcripts",
            "description": "Generate and manage transcripts and academic statements.",
        },
        {
            "slug": "course-allocation",
            "title": "Course Allocation",
            "description": "Allocate courses and manage course offerings per term.",
        },
        {
            "slug": "academic-records",
            "title": "Academic Records",
            "description": "Maintain academic records and support record audits.",
        },
    ],
    "ADM": [
        {
            "slug": "enrolled-students",
            "title": "Enrolled Students",
            "description": "Review enrolled student records and enrollment details.",
        },
        {
            "slug": "admission-decisions",
            "title": "Admission Decisions",
            "description": "Review applicant records, verify documents, and publish admission decisions.",
        },
        {
            "slug": "offer-letters",
            "title": "Offer Letters",
            "description": "Generate and manage admission offer letters and communications.",
        },
        {
            "slug": "enrollment-statistics",
            "title": "Enrollment Statistics",
            "description": "Monitor intake, conversion, and enrollment numbers by program.",
        },
        {
            "slug": "student-support",
            "title": "Student Support Services",
            "description": "Manage student support requests and service follow-ups.",
        },
    ],
    "FIN": [
        {
            "slug": "tuition-payments",
            "title": "Tuition & Payments",
            "description": "Track fee payments, post receipts, and monitor payment compliance.",
        },
        {
            "slug": "budgeting",
            "title": "Budgeting",
            "description": "Create and review budgets, allocations, and department requests.",
        },
        {
            "slug": "payroll",
            "title": "Payroll",
            "description": "Review payroll summaries and payment runs for staff.",
        },
        {
            "slug": "expenditures",
            "title": "Expenditure Tracking",
            "description": "Track spending, approvals, and expense categorization.",
        },
        {
            "slug": "procurement",
            "title": "Procurement",
            "description": "Manage procurement requests, quotes, purchase orders, and deliveries.",
        },
        {
            "slug": "financial-reports",
            "title": "Financial Reports",
            "description": "Generate financial statements and management reports.",
        },
    ],
    "HRM": [
        {
            "slug": "academic-staff",
            "title": "Academic Staff (Lecturers)",
            "description": "Manage lecturer accounts, access status, and academic staff records.",
        },
    ],
}


def _get_office_modules(office_code: str):
    office_code = (office_code or "").strip().upper()
    return OFFICE_MODULES.get(office_code, [])


def _generate_password(length=10):
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def _normalize_name_part(value: str) -> str:
    return (value or "").strip()


def _build_full_name(first_name: str, surname: str, last_name: str) -> str:
    parts = [first_name]
    if surname:
        parts.append(surname)
    parts.append(last_name)
    return " ".join([p for p in parts if p])


def _next_student_number():
    last_number = Application.objects.exclude(student_number__isnull=True).aggregate(
        Max("student_number")
    )["student_number__max"]
    if last_number:
        next_number = int(last_number) + 1
    else:
        next_number = 26000001
    return f"{next_number:08d}"


def _unique_student_number():
    candidate = int(_next_student_number())
    while User.objects.filter(username=f"{candidate:08d}").exists():
        candidate += 1
    return f"{candidate:08d}"


def _get_students_with_records():
    students = list(
        User.objects.select_related("userprofile")
        .filter(userprofile__role="student", userprofile__student_status="enrolled")
        .exclude(username__startswith="REG")
        .order_by("username")
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
        User.objects.select_related("userprofile")
        .filter(userprofile__role="lecturer")
        .order_by("username")
    )


def _adm_application_decision(application_id: int, decision: str):
    if decision not in {"approve", "reject"}:
        raise ValueError("Invalid decision.")

    success = False
    for _ in range(3):
        try:
            with transaction.atomic():
                try:
                    application = Application.objects.get(pk=application_id)
                except Application.DoesNotExist:
                    raise ValueError("Admission case not found.")

                if decision == "approve":
                    application.status = "approved"
                    if not application.student_number:
                        application.student_number = _unique_student_number()
                    if not application.issued_password:
                        application.issued_password = _generate_password()
                    application.save(update_fields=["status", "student_number", "issued_password"])

                    applicant_user = User.objects.filter(username=application.reg_number).first()
                    if applicant_user and applicant_user.is_active:
                        applicant_user.is_active = False
                        applicant_user.set_unusable_password()
                        applicant_user.save()
                        UserProfile.objects.filter(user=applicant_user).update(student_status="applicant")

                    if not User.objects.filter(username=application.student_number).exists():
                        new_user = User.objects.create_user(
                            username=application.student_number,
                            email=application.email,
                            password=application.issued_password,
                        )
                        profile, _ = UserProfile.objects.get_or_create(user=new_user)
                        profile.role = "student"
                        profile.student_status = "enrolled"
                        profile.save()
                else:
                    application.status = "rejected"
                    application.save(update_fields=["status"])
            success = True
            break
        except OperationalError:
            time.sleep(0.1)
            continue

    if not success:
        raise OperationalError("Decision failed. Please retry.")


def _adm_application_delete(application_id: int):
    Application.objects.filter(pk=application_id).delete()


def _adm_delete_enrolled_student(user_id: int):
    user = (
        User.objects.select_related("userprofile")
        .filter(pk=user_id, userprofile__role="student")
        .first()
    )
    if not user:
        raise ValueError("Student account not found.")
    Application.objects.filter(student_number=user.username).delete()
    user.delete()


def _get_active_lecturer(module_code: str):
    return (
        LecturerProfile.objects.select_related("user")
        .filter(module_code=module_code, is_active=True)
        .order_by("-created_at")
        .first()
    )


def _hire_lecturer(*, module_code: str, first_name: str, last_name: str, surname: str = "", allow_replace: bool = False):
    module_code = (module_code or "").strip().upper()
    first_name = _normalize_name_part(first_name)
    surname = _normalize_name_part(surname)
    last_name = _normalize_name_part(last_name)
    valid_codes = {code for code, _label in MODULE_CHOICES}
    if module_code not in valid_codes:
        raise ValueError("Invalid module code.")
    if not first_name:
        raise ValueError("First name is required.")
    if not last_name:
        raise ValueError("Last name is required.")

    if not allow_replace and _get_active_lecturer(module_code):
        raise ValueError("This module already has an active lecturer. Use replace or stop access first.")

    now = timezone.now()
    issue_year = int(now.year)
    yy = issue_year % 100
    full_name = _build_full_name(first_name, surname, last_name)
    module_name = dict(MODULE_CHOICES).get(module_code, "")

    for _ in range(3):
        try:
            with transaction.atomic():
                last_seq = (
                    LecturerProfile.objects.filter(module_code=module_code, issue_year=issue_year)
                    .aggregate(Max("sequence"))
                    .get("sequence__max")
                    or 0
                )
                next_seq = int(last_seq) + 1
                lecturer_id = f"LEC{yy:02d}-{next_seq:03d}"
                password = _generate_password(10)

                user = User.objects.create_user(username=lecturer_id, password=password)
                user.first_name = first_name[:150]
                user.last_name = _build_full_name(surname, "", last_name)[:150]
                user.save(update_fields=["first_name", "last_name"])

                profile, _created = UserProfile.objects.get_or_create(user=user)
                profile.role = "lecturer"
                profile.save(update_fields=["role"])

                LecturerProfile.objects.create(
                    user=user,
                    lecturer_id=lecturer_id,
                    module_code=module_code,
                    module_name=module_name,
                    issue_year=issue_year,
                    sequence=next_seq,
                    first_name=first_name,
                    surname=surname,
                    last_name=last_name,
                    full_name=full_name,
                    assigned_password=password,
                )

            return {
                "module_code": module_code,
                "module_name": module_name,
                "full_name": full_name,
                "lecturer_id": lecturer_id,
                "password": password,
            }
        except (OperationalError, IntegrityError):
            time.sleep(0.1)
            continue

    raise OperationalError("Could not allocate a unique lecturer id. Please retry.")


def _deactivate_lecturer(module_code: str):
    lecturer = _get_active_lecturer(module_code)
    if not lecturer:
        raise ValueError("No active lecturer to deactivate.")
    now = timezone.now()
    LecturerProfile.objects.filter(pk=lecturer.pk, is_active=True).update(
        is_active=False,
        deactivated_at=now,
    )
    lecturer.user.is_active = False
    lecturer.user.save(update_fields=["is_active"])
    return lecturer

def _require_staff_access(request, office_code: str):
    if not _is_staff(request.user):
        return None, redirect("home")

    staff_profile = getattr(request.user, "staffprofile", None)
    if staff_profile is None:
        return None, redirect("home")

    if not staff_profile.is_active or not request.user.is_active:
        return None, redirect("home")

    office_code = (office_code or "").strip().upper()
    office_map = dict(OFFICE_CHOICES)
    if office_code not in office_map:
        raise Http404("Unknown office")

    if staff_profile.office_code != office_code:
        return staff_profile, redirect("staff_office_dashboard", office_code=staff_profile.office_code)

    return staff_profile, None


@login_required
def staff_dashboard(request):
    if not _is_staff(request.user):
        return redirect("home")
    staff_profile = getattr(request.user, "staffprofile", None)
    if staff_profile is None:
        return redirect("home")
    if not staff_profile.is_active or not request.user.is_active:
        return redirect("home")
    return redirect("staff_office_dashboard", office_code=staff_profile.office_code)


@login_required
def staff_office_dashboard(request, office_code):
    staff_profile, response = _require_staff_access(request, office_code)
    if response is not None:
        return response

    office_code = (office_code or "").strip().upper()
    office_map = dict(OFFICE_CHOICES)

    return render(
        request,
        "dashboard/staff/office_dashboard.html",
        {
            "current_page": "staff.overview",
            "office_code": office_code,
            "office_label": office_map[office_code],
            "office_purpose": OFFICE_PURPOSE.get(office_code, ""),
            "office_features": OFFICE_FEATURES.get(office_code, []),
            "office_modules": _get_office_modules(office_code),
            "staff_id": staff_profile.staff_id,
            "staff_name": staff_profile.full_name or request.user.first_name or request.user.username,
        },
    )


@login_required
def staff_academic_workspace(request, office_code):
    staff_profile, response = _require_staff_access(request, office_code)
    if response is not None:
        return response

    office_code = (office_code or "").strip().upper()
    office_map = dict(OFFICE_CHOICES)

    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        try:
            if action == "assign_student_program":
                student_id = int(request.POST.get("student_id") or 0)
                program_id = int(request.POST.get("program_id") or 0)
                profile = (
                    UserProfile.objects.select_related("user")
                    .filter(user_id=student_id, role="student")
                    .first()
                )
                if not profile:
                    raise ValueError("Student account not found.")
                if not Program.objects.filter(pk=program_id).exists():
                    raise ValueError("Program not found.")
                profile.program_id = program_id
                profile.save(update_fields=["program"])
                request.session["staff_academic_flash"] = "Student program assignment saved."

            elif action == "enroll_student":
                student_id = int(request.POST.get("student_id") or 0)
                module_id = int(request.POST.get("module_id") or 0)
                session_id = int(request.POST.get("session_id") or 0)
                profile = (
                    UserProfile.objects.select_related("user")
                    .filter(user_id=student_id, role="student")
                    .first()
                )
                if not profile:
                    raise ValueError("Student account not found.")
                if not AcademicModule.objects.filter(pk=module_id).exists():
                    raise ValueError("Module not found.")
                if not AcademicSession.objects.filter(pk=session_id).exists():
                    raise ValueError("Session not found.")
                Enrollment.objects.update_or_create(
                    student_id=student_id,
                    module_id=module_id,
                    session_id=session_id,
                    defaults={
                        "program_id": profile.program_id,
                        "status": "enrolled",
                    },
                )
                request.session["staff_academic_flash"] = "Student enrollment saved."

            elif action == "drop_enrollment":
                enrollment_id = int(request.POST.get("enrollment_id") or 0)
                updated = Enrollment.objects.filter(pk=enrollment_id).update(status="dropped")
                if not updated:
                    raise ValueError("Enrollment record not found.")
                request.session["staff_academic_flash"] = "Enrollment updated to dropped."

        except (ValueError, IntegrityError) as exc:
            request.session["staff_academic_error"] = str(exc)
        return redirect("staff_academic_workspace", office_code=office_code)

    students = (
        User.objects.select_related("userprofile")
        .filter(
            userprofile__role="student",
            userprofile__student_status="enrolled",
            is_active=True,
        )
        .exclude(username__startswith="REG")
        .order_by("username")
    )
    programs = Program.objects.select_related("department").order_by("code")
    modules = AcademicModule.objects.filter(is_active=True).order_by("code")
    sessions = AcademicSession.objects.filter(is_active=True).order_by("-year_start", "-semester")
    program_modules = (
        ProgramModule.objects.select_related("program", "module")
        .order_by("program__code", "semester", "module__code")
    )
    enrollments = (
        Enrollment.objects.select_related("student", "program", "module", "session")
        .order_by("-enrolled_at")[:150]
    )

    return render(
        request,
        "dashboard/staff/academic_workspace.html",
        {
            "current_page": "staff.academic_workspace",
            "office_code": office_code,
            "office_label": office_map[office_code],
            "office_purpose": OFFICE_PURPOSE.get(office_code, ""),
            "office_modules": _get_office_modules(office_code),
            "staff_id": staff_profile.staff_id,
            "staff_name": staff_profile.full_name or request.user.first_name or request.user.username,
            "students": students,
            "programs": programs,
            "modules": modules,
            "sessions": sessions,
            "program_modules": program_modules,
            "enrollments": enrollments,
            "flash": request.session.pop("staff_academic_flash", None),
            "flash_error": request.session.pop("staff_academic_error", None),
        },
    )


@login_required
def staff_office_module(request, office_code, module_slug):
    staff_profile, response = _require_staff_access(request, office_code)
    if response is not None:
        return response

    office_code = (office_code or "").strip().upper()
    office_map = dict(OFFICE_CHOICES)
    modules = _get_office_modules(office_code)
    module = next((m for m in modules if m["slug"] == module_slug), None)
    if module is None:
        raise Http404("Unknown module")

    if office_code == "ADM" and module_slug == "admission-decisions":
        if request.method == "POST":
            action = request.POST.get("action")
            try:
                application_id = int(request.POST.get("application_id") or 0)
            except ValueError:
                application_id = 0
            try:
                if action == "decision":
                    decision = request.POST.get("decision")
                    _adm_application_decision(application_id, decision)
                    if decision == "approve":
                        request.session["adm_flash"] = "Admission case approved."
                    else:
                        request.session["adm_flash"] = "Admission case rejected."
            except (ValueError, OperationalError) as exc:
                request.session["adm_flash_error"] = str(exc)
            return redirect("staff_office_module", office_code=office_code, module_slug=module_slug)

        applications = Application.objects.select_related("applicant").order_by("-created_at")
        pending_applications = applications.filter(status__in=["submitted", "under_review"])[:100]
        approved_applications = applications.filter(status="approved")[:100]
        rejected_applications = applications.filter(status="rejected")[:100]
        return render(
            request,
            "dashboard/staff/adm_admission_decisions.html",
            {
                "current_page": f"staff.module.{module_slug}",
                "office_code": office_code,
                "office_label": office_map[office_code],
                "office_purpose": OFFICE_PURPOSE.get(office_code, ""),
                "office_modules": modules,
                "module": module,
                "pending_applications": pending_applications,
                "approved_applications": approved_applications,
                "rejected_applications": rejected_applications,
                "flash": request.session.pop("adm_flash", None),
                "flash_error": request.session.pop("adm_flash_error", None),
                "staff_id": staff_profile.staff_id,
                "staff_name": staff_profile.full_name or request.user.first_name or request.user.username,
            },
        )

    if office_code == "ADM" and module_slug == "enrolled-students":
        if request.method == "POST":
            try:
                user_id = int(request.POST.get("user_id") or 0)
            except ValueError:
                user_id = 0
            try:
                _adm_delete_enrolled_student(user_id)
                request.session["adm_flash"] = "Enrolled student removed."
            except (ValueError, OperationalError) as exc:
                request.session["adm_flash_error"] = str(exc)
            return redirect("staff_office_module", office_code=office_code, module_slug=module_slug)

        students = _get_students_with_records()
        return render(
            request,
            "dashboard/staff/adm_enrolled_students.html",
            {
                "current_page": f"staff.module.{module_slug}",
                "office_code": office_code,
                "office_label": office_map[office_code],
                "office_purpose": OFFICE_PURPOSE.get(office_code, ""),
                "office_modules": modules,
                "module": module,
                "students": students,
                "flash": request.session.pop("adm_flash", None),
                "flash_error": request.session.pop("adm_flash_error", None),
                "staff_id": staff_profile.staff_id,
                "staff_name": staff_profile.full_name or request.user.first_name or request.user.username,
            },
        )

    if office_code == "HRM" and module_slug == "academic-staff":
        if request.method == "POST":
            action = request.POST.get("action")
            try:
                if action == "hire_lecturer":
                    hire_result = _hire_lecturer(
                        module_code=request.POST.get("module_code"),
                        first_name=request.POST.get("first_name"),
                        surname=request.POST.get("surname"),
                        last_name=request.POST.get("last_name"),
                    )
                    request.session["lecturer_hire_result"] = hire_result
                    request.session["lecturer_action"] = "Hired"
                elif action == "replace_lecturer":
                    module_code = request.POST.get("module_code")
                    _deactivate_lecturer(module_code)
                    hire_result = _hire_lecturer(
                        module_code=module_code,
                        first_name=request.POST.get("first_name"),
                        surname=request.POST.get("surname"),
                        last_name=request.POST.get("last_name"),
                        allow_replace=True,
                    )
                    request.session["lecturer_hire_result"] = hire_result
                    request.session["lecturer_action"] = "Replaced"
                elif action == "deactivate_lecturer":
                    module_code = request.POST.get("module_code")
                    lecturer = _deactivate_lecturer(module_code)
                    request.session["lecturer_hire_result"] = {
                        "module_code": lecturer.module_code,
                        "module_name": lecturer.module_name,
                        "full_name": lecturer.full_name,
                        "lecturer_id": lecturer.lecturer_id,
                        "password": lecturer.assigned_password,
                    }
                    request.session["lecturer_action"] = "Access stopped"
            except ValueError as exc:
                request.session["lecturer_hire_error"] = str(exc)
            return redirect("staff_office_module", office_code=office_code, module_slug=module_slug)

        module_rows = []
        for code, label in MODULE_CHOICES:
            active_lecturer = _get_active_lecturer(code)
            module_rows.append(
                {
                    "code": code,
                    "name": label,
                    "lecturer": active_lecturer,
                }
            )
        return render(
            request,
            "dashboard/staff/hrm_academic_staff.html",
            {
                "current_page": f"staff.module.{module_slug}",
                "office_code": office_code,
                "office_label": office_map[office_code],
                "office_purpose": OFFICE_PURPOSE.get(office_code, ""),
                "office_modules": modules,
                "module": module,
                "module_rows": module_rows,
                "module_choices": MODULE_CHOICES,
                "lecturer_hire_result": request.session.pop("lecturer_hire_result", None),
                "lecturer_hire_error": request.session.pop("lecturer_hire_error", None),
                "lecturer_action": request.session.pop("lecturer_action", None),
                "staff_id": staff_profile.staff_id,
                "staff_name": staff_profile.full_name or request.user.first_name or request.user.username,
            },
        )

    return render(
        request,
        "dashboard/staff/module.html",
        {
            "current_page": f"staff.module.{module_slug}",
            "office_code": office_code,
            "office_label": office_map[office_code],
            "office_purpose": OFFICE_PURPOSE.get(office_code, ""),
            "office_modules": modules,
            "module": module,
            "staff_id": staff_profile.staff_id,
            "staff_name": staff_profile.full_name or request.user.first_name or request.user.username,
        },
    )
