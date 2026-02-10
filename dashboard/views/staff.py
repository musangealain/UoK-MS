from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render

from dashboard.models import OFFICE_CHOICES, OFFICE_PURPOSE


def _is_staff(user):
    profile = getattr(user, "userprofile", None)
    return bool(profile and profile.role == "staff")


@login_required
def staff_office_dashboard(request, office_code):
    if not _is_staff(request.user):
        return redirect("home")

    staff_profile = getattr(request.user, "staffprofile", None)
    if staff_profile is None:
        return redirect("home")

    office_code = (office_code or "").strip().upper()
    office_map = dict(OFFICE_CHOICES)
    if office_code not in office_map:
        raise Http404("Unknown office")

    if staff_profile.office_code != office_code:
        return redirect("staff_office_dashboard", office_code=staff_profile.office_code)

    return render(
        request,
        "dashboard/staff/office.html",
        {
            "current_page": "staff.overview",
            "office_code": office_code,
            "office_label": office_map[office_code],
            "office_purpose": OFFICE_PURPOSE.get(office_code, ""),
            "staff_id": staff_profile.staff_id,
            "staff_name": staff_profile.full_name or request.user.first_name or request.user.username,
        },
    )

