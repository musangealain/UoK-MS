from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render

from dashboard.models import OFFICE_CHOICES, OFFICE_PURPOSE


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
        "Applications and admissions decisions",
        "Enrollment statistics",
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
            "slug": "applications",
            "title": "Applications",
            "description": "View new applications, verify documents, and track review status.",
        },
        {
            "slug": "admission-decisions",
            "title": "Admission Decisions",
            "description": "Approve/reject applicants and publish admission outcomes.",
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
}


def _get_office_modules(office_code: str):
    office_code = (office_code or "").strip().upper()
    return OFFICE_MODULES.get(office_code, [])


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
