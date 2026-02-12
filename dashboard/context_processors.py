from django.urls import NoReverseMatch, reverse

from dashboard.models import PortalRegistry


def _portal_code_from_path(path: str) -> str:
    path = (path or "").lower()
    if path.startswith("/dashboard/student/") or path.startswith("/dashboard/applicant/"):
        return "student"
    if path.startswith("/dashboard/lecturer/"):
        return "lecturer"
    if path.startswith("/dashboard/staff/"):
        return "staff"
    if path.startswith("/dashboard/admin/"):
        return "admin"
    return ""


def portal_navigation(request):
    portal_code = _portal_code_from_path(getattr(request, "path", ""))
    if not portal_code:
        return {}

    portal = (
        PortalRegistry.objects.prefetch_related("tables")
        .filter(code=portal_code, is_active=True)
        .first()
    )
    if not portal:
        return {"portal_code": portal_code, "portal_tables": []}

    table_links = []
    for table in portal.tables.filter(is_active=True).order_by("sort_order", "table_name"):
        href = table.dashboard_path or ""
        if not href and table.dashboard_route_name:
            try:
                href = reverse(table.dashboard_route_name)
            except NoReverseMatch:
                href = "#"
        table_links.append(
            {
                "key": table.table_key,
                "name": table.table_name,
                "href": href or "#",
                "is_active": (href and request.path == href),
            }
        )

    return {
        "portal_code": portal_code,
        "portal_name": portal.name,
        "portal_tables": table_links,
    }
