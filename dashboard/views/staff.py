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


ADM_NAV_SECTIONS = [
    {
        "label": "Dashboard",
        "icon": "\U0001F6AA",
        "items": [
            {
                "title": "Admissions Dashboard",
                "kind": "overview",
                "description": "Real-time application metrics and pipeline status.",
            },
            {
                "slug": "application-overview",
                "title": "Application Overview",
                "description": "Snapshot of applications, stage mix, and cycle health.",
            },
            {
                "slug": "enrollment-pipeline",
                "title": "Enrollment Pipeline",
                "description": "Track conversion flow from application to enrollment.",
            },
            {
                "slug": "student-services-status",
                "title": "Student Services Status",
                "description": "Monitor service queues, pending cases, and completion status.",
            },
        ],
    },
    {
        "label": "Application Management",
        "icon": "\U0001F4DD",
        "items": [
            {
                "slug": "new-applications",
                "title": "New Applications",
                "description": "Review newly submitted applications and intake batches.",
            },
            {
                "slug": "application-review",
                "title": "Application Review",
                "description": "Process application decisions through the review workflow.",
            },
            {
                "slug": "document-verification",
                "title": "Document Verification",
                "description": "Verify mandatory applicant documents and completion status.",
            },
            {
                "slug": "application-status",
                "title": "Application Status",
                "description": "Track status progression and pending actions by applicant.",
            },
            {
                "slug": "waitlist-management",
                "title": "Waitlist Management",
                "description": "Maintain waitlists and prioritize eligible candidates.",
            },
        ],
    },
    {
        "label": "Admission Decisions",
        "icon": "\u2705",
        "items": [
            {
                "slug": "offer-letters",
                "title": "Offer Letters",
                "description": "Generate and manage admission offer communication.",
            },
            {
                "slug": "rejection-letters",
                "title": "Rejection Letters",
                "description": "Manage rejection notices and applicant communication logs.",
            },
            {
                "slug": "conditional-offers",
                "title": "Conditional Offers",
                "description": "Issue and track offers with pending requirements.",
            },
            {
                "slug": "scholarship-awards",
                "title": "Scholarship Awards",
                "description": "Coordinate scholarship recommendations and awards.",
            },
            {
                "slug": "acceptance-tracking",
                "title": "Acceptance Tracking",
                "description": "Track accepted candidates and enrollment completion.",
            },
        ],
    },
    {
        "label": "Enrollment Statistics",
        "icon": "\U0001F4CA",
        "items": [
            {
                "slug": "application-trends",
                "title": "Application Trends",
                "description": "Analyze trend lines across cycles and programs.",
            },
            {
                "slug": "acceptance-rates",
                "title": "Acceptance Rates",
                "description": "Review offer, acceptance, and rejection rate changes.",
            },
            {
                "slug": "enrollment-forecast",
                "title": "Enrollment Forecast",
                "description": "Forecast projected intake by faculty and program.",
            },
            {
                "slug": "demographics-analysis",
                "title": "Demographics Analysis",
                "description": "Measure demographic distribution across applicants.",
            },
            {
                "slug": "yield-rates",
                "title": "Yield Rates",
                "description": "Track yield from offers to enrolled students.",
            },
        ],
    },
    {
        "label": "Student Services",
        "icon": "\U0001F91D",
        "items": [
            {
                "slug": "orientation-programs",
                "title": "Orientation Programs",
                "description": "Plan and track orientation sessions for new students.",
            },
            {
                "slug": "student-support",
                "title": "Student Support",
                "description": "Manage student support requests and follow-ups.",
            },
            {
                "slug": "counseling-services",
                "title": "Counseling Services",
                "description": "Coordinate referrals and student counseling support.",
            },
            {
                "slug": "student-id-cards",
                "title": "Student ID Cards",
                "description": "Track card issuance and pending ID requests.",
            },
            {
                "slug": "housing-assistance",
                "title": "Housing Assistance",
                "description": "Handle student housing requests and placement support.",
            },
        ],
    },
    {
        "label": "Communication",
        "icon": "\U0001F4E2",
        "items": [
            {
                "slug": "prospective-students",
                "title": "Prospective Students",
                "description": "Manage outreach lists and lead engagement activity.",
            },
            {
                "slug": "applicant-communication",
                "title": "Applicant Communication",
                "description": "Track inbound and outbound applicant communication.",
            },
            {
                "slug": "open-day-events",
                "title": "Open Day Events",
                "description": "Coordinate open day schedules and attendance.",
            },
            {
                "slug": "campus-tours",
                "title": "Campus Tours",
                "description": "Schedule and monitor campus tour bookings.",
            },
            {
                "slug": "email-templates",
                "title": "Email Templates",
                "description": "Maintain reusable message templates for admissions.",
            },
        ],
    },
    {
        "label": "Admission Reports",
        "icon": "\U0001F4C8",
        "items": [
            {
                "slug": "application-reports",
                "title": "Application Reports",
                "description": "Generate operational reports across application stages.",
            },
            {
                "slug": "conversion-rates",
                "title": "Conversion Rates",
                "description": "Measure conversion between each admission stage.",
            },
            {
                "slug": "enrollment-reports",
                "title": "Enrollment Reports",
                "description": "Produce enrollment summaries and completion reports.",
            },
            {
                "slug": "recruitment-analytics",
                "title": "Recruitment Analytics",
                "description": "Analyze campaign performance and recruitment impact.",
            },
        ],
    },
    {
        "label": "Settings",
        "icon": "\u2699",
        "items": [
            {
                "slug": "admission-criteria",
                "title": "Admission Criteria",
                "description": "Configure policy, requirements, and evaluation criteria.",
            },
            {
                "slug": "application-forms",
                "title": "Application Forms",
                "description": "Manage form fields, validation, and required documents.",
            },
            {
                "slug": "offer-templates",
                "title": "Offer Templates",
                "description": "Configure offer and decision communication templates.",
            },
            {
                "title": "Profile & Password",
                "kind": "password_change",
                "description": "Manage profile preferences and account credentials.",
            },
        ],
    },
]


ADM_SUBDASHBOARD_FUNCTIONALITIES = [
    {
        "title": "Admissions Dashboard",
        "description": "Real-time application metrics and pipeline status.",
    },
    {
        "title": "Application Management",
        "description": "Process and track applications through review cycle.",
    },
    {
        "title": "Admission Decisions",
        "description": "Generate offer/rejection letters and manage acceptances.",
    },
    {
        "title": "Enrollment Statistics",
        "description": "Analyze application trends and enrollment patterns.",
    },
    {
        "title": "Student Services",
        "description": "Support enrolled students with services and resources.",
    },
    {
        "title": "Communication",
        "description": "Manage outreach to prospective and accepted students.",
    },
]


ADM_MODULE_ALIASES = {
    "admission-decisions": "application-review",
    "enrolled-students": "acceptance-tracking",
}


def _build_adm_modules():
    modules = []
    for section in ADM_NAV_SECTIONS:
        for item in section.get("items", []):
            slug = item.get("slug")
            if not slug:
                continue
            modules.append(
                {
                    "slug": slug,
                    "title": item.get("title", slug.replace("-", " ").title()),
                    "description": item.get("description", ""),
                    "section": section.get("label", ""),
                }
            )
    return modules


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
    "ADM": _build_adm_modules(),
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


def _get_office_nav_sections(office_code: str):
    office_code = (office_code or "").strip().upper()
    if office_code == "ADM":
        return ADM_NAV_SECTIONS
    return []


def _get_adm_subdashboard_functionalities(office_code: str):
    office_code = (office_code or "").strip().upper()
    if office_code == "ADM":
        return ADM_SUBDASHBOARD_FUNCTIONALITIES
    return []


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
        .order_by("username")
    )
    user_ids = [u.id for u in students]
    student_usernames = [u.username for u in students]
    applications = list(
        Application.objects.filter(applicant_id__in=user_ids)
        | Application.objects.filter(student_number__in=student_usernames)
    )
    by_applicant_id = {a.applicant_id: a for a in applications if a.applicant_id}
    by_student_number = {a.student_number: a for a in applications if a.student_number}
    for u in students:
        u.application_record = by_applicant_id.get(u.id) or by_student_number.get(u.username)
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
                    if application.status != "under_review":
                        raise ValueError("Only under-review applications can be approved.")
                    docs_complete = bool(
                        application.doc_id_uploaded
                        and application.doc_transcript_uploaded
                        and application.doc_recommendation_uploaded
                    )
                    if not docs_complete:
                        raise ValueError("All required documents must be verified before approval.")
                    application.status = "approved"
                    if not application.student_number:
                        application.student_number = _unique_student_number()
                    application.save(update_fields=["status", "student_number"])
                else:
                    if application.status not in {"submitted", "under_review"}:
                        raise ValueError("Only active review cases can be rejected.")
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
    Application.objects.filter(applicant_id=user.id).delete()
    Application.objects.filter(student_number=user.username).delete()
    user.delete()


def _adm_issue_portal_access(application_id: int, *, reset_password: bool = False):
    success = False
    issued_password = None
    for _ in range(3):
        try:
            with transaction.atomic():
                application = Application.objects.select_for_update().filter(pk=application_id).first()
                if not application:
                    raise ValueError("Admission case not found.")
                if application.status != "approved":
                    raise ValueError("Portal access can only be issued for approved applications.")

                applicant_user = application.applicant or User.objects.filter(username=application.reg_number).first()
                if not applicant_user:
                    raise ValueError("Applicant user account is missing.")
                if applicant_user.username != application.reg_number:
                    raise ValueError("Applicant account no longer matches the REG reference.")

                if not application.student_number:
                    application.student_number = _unique_student_number()
                if not application.applicant_id:
                    application.applicant = applicant_user

                if (
                    reset_password
                    or not application.issued_password
                    or len(application.issued_password) != 10
                ):
                    application.issued_password = _generate_password(10)
                issued_password = application.issued_password
                application.reg_password = application.issued_password
                update_fields = ["student_number", "issued_password", "reg_password"]
                if application.applicant_id:
                    update_fields.append("applicant")
                application.save(update_fields=update_fields)

                applicant_user.email = application.email
                applicant_user.is_active = True
                applicant_user.set_password(application.issued_password)
                applicant_user.save(update_fields=["email", "is_active", "password"])

                profile, _ = UserProfile.objects.get_or_create(user=applicant_user)
                profile.role = "student"
                profile.student_status = "enrolled"
                profile.save(update_fields=["role", "student_status"])

            success = True
            break
        except OperationalError:
            time.sleep(0.1)
            continue

    if not success:
        raise OperationalError("Portal access issuance failed. Please retry.")
    return issued_password


def _adm_set_application_status(application_id: int, status: str):
    allowed = {"submitted", "under_review", "rejected"}
    if status not in allowed:
        raise ValueError("Invalid application status.")

    application = Application.objects.filter(pk=application_id).first()
    if not application:
        raise ValueError("Admission case not found.")

    application.status = status
    application.save(update_fields=["status"])
    return application


def _adm_update_document_flags(
    application_id: int,
    *,
    doc_id_uploaded: bool,
    doc_transcript_uploaded: bool,
    doc_recommendation_uploaded: bool,
):
    application = Application.objects.filter(pk=application_id).first()
    if not application:
        raise ValueError("Admission case not found.")
    if application.status != "submitted":
        raise ValueError("Document verification can only be edited while application is submitted.")

    application.doc_id_uploaded = bool(doc_id_uploaded)
    application.doc_transcript_uploaded = bool(doc_transcript_uploaded)
    application.doc_recommendation_uploaded = bool(doc_recommendation_uploaded)
    application.save(
        update_fields=[
            "doc_id_uploaded",
            "doc_transcript_uploaded",
            "doc_recommendation_uploaded",
        ]
    )
    return application


def _adm_build_offer_letter_preview(application: Application, office_label: str):
    issued_on = timezone.localdate().strftime("%Y-%m-%d")
    student_number = application.student_number or "Pending Student Number"
    credential_note = (
        f"Student Portal Username (REG): {application.reg_number}\n"
        f"Student Portal Password: {application.issued_password}\n"
        f"Student Number: {application.student_number}"
        if application.student_number and application.issued_password
        else "Your portal access will be issued by Admissions from the Offer Letters dashboard."
    )
    lines = [
        f"Date: {issued_on}",
        "",
        f"To: {application.full_name}",
        f"Program: {application.program}",
        "",
        "Subject: Admission Offer",
        "",
        f"Dear {application.full_name},",
        "",
        f"Congratulations. You are offered admission to {application.program} at the University.",
        f"Reference Number: {application.reg_number}",
        f"Student Number: {student_number}",
        credential_note,
        "",
        "Please confirm your acceptance and complete enrollment requirements.",
        "",
        f"Admissions and Student Services Office ({office_label})",
    ]
    return "\n".join(lines)


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
            "office_nav_sections": _get_office_nav_sections(office_code),
            "adm_subdashboard_functionalities": _get_adm_subdashboard_functionalities(office_code),
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
            "office_nav_sections": _get_office_nav_sections(office_code),
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
    if office_code == "ADM":
        canonical_slug = ADM_MODULE_ALIASES.get(module_slug, module_slug)
        if canonical_slug != module_slug:
            return redirect("staff_office_module", office_code=office_code, module_slug=canonical_slug)
        module_slug = canonical_slug

    modules = _get_office_modules(office_code)
    office_nav_sections = _get_office_nav_sections(office_code)
    module = next((m for m in modules if m["slug"] == module_slug), None)
    if module is None:
        raise Http404("Unknown module")

    if office_code == "ADM" and module_slug == "new-applications":
        if request.method == "POST":
            action = (request.POST.get("action") or "").strip()
            try:
                application_id = int(request.POST.get("application_id") or 0)
            except ValueError:
                application_id = 0
            try:
                if action == "start_review":
                    app = Application.objects.filter(pk=application_id).first()
                    if not app:
                        raise ValueError("Admission case not found.")
                    if not app.submitted_at:
                        raise ValueError("Applicant has not completed final submission yet.")
                    docs_complete = bool(
                        app.doc_id_uploaded
                        and app.doc_transcript_uploaded
                        and app.doc_recommendation_uploaded
                    )
                    if not docs_complete:
                        raise ValueError("This case is missing documents. Complete verification first.")
                    if app.status != "submitted":
                        raise ValueError("Only newly submitted applications can move to review.")
                    _adm_set_application_status(application_id, "under_review")
                    request.session["adm_flash"] = "Application moved to review queue."
            except (ValueError, OperationalError) as exc:
                request.session["adm_flash_error"] = str(exc)
            return redirect("staff_office_module", office_code=office_code, module_slug=module_slug)

        applications = Application.objects.order_by("-created_at")
        queue_applications = applications.filter(status="submitted", submitted_at__isnull=False)[:120]
        for app in queue_applications:
            docs_complete = int(app.doc_id_uploaded) + int(app.doc_transcript_uploaded) + int(
                app.doc_recommendation_uploaded
            )
            app.docs_complete = docs_complete
            app.docs_percent = int((docs_complete / 3) * 100)
        return render(
            request,
            "dashboard/staff/adm_new_applications.html",
            {
                "current_page": f"staff.module.{module_slug}",
                "office_code": office_code,
                "office_label": office_map[office_code],
                "office_purpose": OFFICE_PURPOSE.get(office_code, ""),
                "office_modules": modules,
                "office_nav_sections": office_nav_sections,
                "module": module,
                "queue_applications": queue_applications,
                "submitted_count": applications.filter(status="submitted", submitted_at__isnull=False).count(),
                "under_review_count": applications.filter(status="under_review").count(),
                "approved_count": applications.filter(status="approved").count(),
                "rejected_count": applications.filter(status="rejected").count(),
                "flash": request.session.pop("adm_flash", None),
                "flash_error": request.session.pop("adm_flash_error", None),
                "staff_id": staff_profile.staff_id,
                "staff_name": staff_profile.full_name or request.user.first_name or request.user.username,
            },
        )

    if office_code == "ADM" and module_slug == "document-verification":
        if request.method == "POST":
            action = (request.POST.get("action") or "").strip()
            try:
                application_id = int(request.POST.get("application_id") or 0)
            except ValueError:
                application_id = 0
            try:
                app = _adm_update_document_flags(
                    application_id,
                    doc_id_uploaded=bool(request.POST.get("doc_id_uploaded")),
                    doc_transcript_uploaded=bool(request.POST.get("doc_transcript_uploaded")),
                    doc_recommendation_uploaded=bool(request.POST.get("doc_recommendation_uploaded")),
                )
                if action == "mark_review_ready":
                    all_docs = bool(
                        app.doc_id_uploaded and app.doc_transcript_uploaded and app.doc_recommendation_uploaded
                    )
                    if not all_docs:
                        raise ValueError("All required documents must be verified before review-ready status.")
                    _adm_set_application_status(application_id, "under_review")
                    request.session["adm_flash"] = "Documents verified. Application moved to review queue."
                else:
                    request.session["adm_flash"] = "Document verification updated."
            except (ValueError, OperationalError) as exc:
                request.session["adm_flash_error"] = str(exc)
            return redirect("staff_office_module", office_code=office_code, module_slug=module_slug)

        applications = Application.objects.filter(
            status__in=["submitted", "under_review"],
        ).exclude(status="submitted", submitted_at__isnull=True).order_by("-created_at")[:160]
        for app in applications:
            docs_complete = int(app.doc_id_uploaded) + int(app.doc_transcript_uploaded) + int(
                app.doc_recommendation_uploaded
            )
            app.docs_complete = docs_complete
            app.docs_percent = int((docs_complete / 3) * 100)

        return render(
            request,
            "dashboard/staff/adm_document_verification.html",
            {
                "current_page": f"staff.module.{module_slug}",
                "office_code": office_code,
                "office_label": office_map[office_code],
                "office_purpose": OFFICE_PURPOSE.get(office_code, ""),
                "office_modules": modules,
                "office_nav_sections": office_nav_sections,
                "module": module,
                "applications": applications,
                "flash": request.session.pop("adm_flash", None),
                "flash_error": request.session.pop("adm_flash_error", None),
                "staff_id": staff_profile.staff_id,
                "staff_name": staff_profile.full_name or request.user.first_name or request.user.username,
            },
        )

    if office_code == "ADM" and module_slug == "offer-letters":
        if request.method == "POST":
            action = (request.POST.get("action") or "").strip()
            try:
                if action == "clear_offer_preview":
                    request.session.pop("adm_offer_preview", None)
                elif action in {"issue_portal_access", "reset_portal_access"}:
                    application_id = int(request.POST.get("application_id") or 0)
                    issued_password = _adm_issue_portal_access(
                        application_id,
                        reset_password=(action == "reset_portal_access"),
                    )
                    if action == "reset_portal_access":
                        request.session["adm_flash"] = (
                            f"Portal access reset successfully. New REG password: {issued_password}"
                        )
                    else:
                        request.session["adm_flash"] = (
                            f"Portal access issued successfully. REG password: {issued_password}"
                        )
                elif action == "generate_offer_preview":
                    application_id = int(request.POST.get("application_id") or 0)
                    application = Application.objects.filter(pk=application_id).first()
                    if not application:
                        raise ValueError("Admission case not found.")
                    if application.status != "approved":
                        raise ValueError("Only approved applications can generate offer letters.")
                    request.session["adm_offer_preview"] = _adm_build_offer_letter_preview(
                        application,
                        office_map[office_code],
                    )
                    request.session["adm_flash"] = f"Offer preview generated for {application.full_name}."
                else:
                    raise ValueError("Invalid offer action.")
            except (ValueError, OperationalError) as exc:
                request.session["adm_flash_error"] = str(exc)
            return redirect("staff_office_module", office_code=office_code, module_slug=module_slug)

        approved_applications = Application.objects.filter(status="approved").order_by("-created_at")[:120]
        return render(
            request,
            "dashboard/staff/adm_offer_letters.html",
            {
                "current_page": f"staff.module.{module_slug}",
                "office_code": office_code,
                "office_label": office_map[office_code],
                "office_purpose": OFFICE_PURPOSE.get(office_code, ""),
                "office_modules": modules,
                "office_nav_sections": office_nav_sections,
                "module": module,
                "approved_applications": approved_applications,
                "offer_preview": request.session.pop("adm_offer_preview", None),
                "flash": request.session.pop("adm_flash", None),
                "flash_error": request.session.pop("adm_flash_error", None),
                "staff_id": staff_profile.staff_id,
                "staff_name": staff_profile.full_name or request.user.first_name or request.user.username,
            },
        )

    if office_code == "ADM" and module_slug == "application-review":
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
                        request.session["adm_flash"] = (
                            "Admission case approved. Issue portal credentials from Offer Letters."
                        )
                    else:
                        request.session["adm_flash"] = "Admission case rejected."
            except (ValueError, OperationalError) as exc:
                request.session["adm_flash_error"] = str(exc)
            return redirect("staff_office_module", office_code=office_code, module_slug=module_slug)

        applications = Application.objects.select_related("applicant").order_by("-created_at")
        pending_applications = applications.filter(status="under_review")[:100]
        for app in pending_applications:
            docs_complete = int(app.doc_id_uploaded) + int(app.doc_transcript_uploaded) + int(
                app.doc_recommendation_uploaded
            )
            app.docs_complete = docs_complete
            app.docs_percent = int((docs_complete / 3) * 100)
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
                "office_nav_sections": office_nav_sections,
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

    if office_code == "ADM" and module_slug == "acceptance-tracking":
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
                "office_nav_sections": office_nav_sections,
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
                "office_nav_sections": office_nav_sections,
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
            "office_nav_sections": office_nav_sections,
            "module": module,
            "staff_id": staff_profile.staff_id,
            "staff_name": staff_profile.full_name or request.user.first_name or request.user.username,
        },
    )
