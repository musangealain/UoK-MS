from django.db import migrations, models
import django.db.models.deletion


def seed_portal_registry(apps, schema_editor):
    PortalRegistry = apps.get_model("dashboard", "PortalRegistry")
    PortalTable = apps.get_model("dashboard", "PortalTable")

    portals = [
        {
            "code": "student",
            "name": "Student Portal",
            "description": "Student-facing portal for applicants and enrolled students.",
            "dashboard_route_name": "student_dashboard",
            "dashboard_path": "/dashboard/student/",
            "tables": [
                ("applicant_dashboard", "Applicant Dashboard", "applicant_dashboard", "/dashboard/applicant/", 1),
                ("student_dashboard", "Student Dashboard", "student_dashboard", "/dashboard/student/", 2),
            ],
        },
        {
            "code": "lecturer",
            "name": "Lecturer Portal",
            "description": "Lecturer workspace for teaching and course operations.",
            "dashboard_route_name": "lecturer_dashboard",
            "dashboard_path": "/dashboard/lecturer/",
            "tables": [
                ("dashboard", "Dashboard", "lecturer_dashboard", "/dashboard/lecturer/", 1),
                ("courses", "Courses", "lecturer_courses", "/dashboard/lecturer/courses/", 2),
                ("course_assignments", "Course Assignments", "lecturer_course_assignments", "/dashboard/lecturer/course-assignments/", 3),
                ("timetable", "Timetable", "lecturer_timetable", "/dashboard/lecturer/timetable/", 4),
                ("materials", "Materials", "lecturer_materials", "/dashboard/lecturer/materials/", 5),
                ("student_lists", "Student Lists", "lecturer_student_lists", "/dashboard/lecturer/student-lists/", 6),
                ("course_enrollments", "Course Enrollments", "lecturer_course_enrollments", "/dashboard/lecturer/course-enrollments/", 7),
                ("attendance_sessions", "Attendance Sessions", "lecturer_attendance_sessions", "/dashboard/lecturer/attendance-sessions/", 8),
                ("attendance_records", "Attendance Records", "lecturer_attendance_records", "/dashboard/lecturer/attendance-records/", 9),
            ],
        },
        {
            "code": "staff",
            "name": "Staff Portal",
            "description": "Office operations portal for institutional staff.",
            "dashboard_route_name": "staff_dashboard",
            "dashboard_path": "/dashboard/staff/",
            "tables": [
                ("staff_overview", "Office Overview", "staff_dashboard", "/dashboard/staff/", 1),
                ("adm_admission_decisions", "ADM Admission Decisions", "", "/dashboard/staff/ADM/admission-decisions/", 2),
                ("adm_enrolled_students", "ADM Enrolled Students", "", "/dashboard/staff/ADM/enrolled-students/", 3),
                ("hrm_academic_staff", "HRM Academic Staff", "", "/dashboard/staff/HRM/academic-staff/", 4),
            ],
        },
        {
            "code": "admin",
            "name": "Admin Portal",
            "description": "Executive and institutional analytics portal.",
            "dashboard_route_name": "admin_dashboard",
            "dashboard_path": "/dashboard/admin/",
            "tables": [
                ("institutional_dashboard", "Institutional Dashboard", "admin_dashboard", "/dashboard/admin/", 1),
                ("strategic_kpis", "Strategic KPIs", "admin_kpi_monitor", "/dashboard/admin/kpis/", 2),
                ("system_utilization", "System Utilization", "admin:index", "/admin/", 3),
            ],
        },
    ]

    for p in portals:
        portal, _ = PortalRegistry.objects.update_or_create(
            code=p["code"],
            defaults={
                "name": p["name"],
                "description": p["description"],
                "dashboard_route_name": p["dashboard_route_name"],
                "dashboard_path": p["dashboard_path"],
                "is_active": True,
            },
        )
        for key, name, route_name, path, order in p["tables"]:
            PortalTable.objects.update_or_create(
                portal=portal,
                table_key=key,
                defaults={
                    "table_name": name,
                    "dashboard_route_name": route_name,
                    "dashboard_path": path,
                    "sort_order": order,
                    "is_active": True,
                },
            )


def unseed_portal_registry(apps, schema_editor):
    PortalRegistry = apps.get_model("dashboard", "PortalRegistry")
    PortalRegistry.objects.filter(code__in=["student", "lecturer", "staff", "admin"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0009_lecturerprofile"),
    ]

    operations = [
        migrations.CreateModel(
            name="PortalRegistry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(choices=[("student", "Student Portal"), ("lecturer", "Lecturer Portal"), ("staff", "Staff Portal"), ("admin", "Admin Portal")], max_length=20, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True, default="")),
                ("dashboard_route_name", models.CharField(blank=True, default="", max_length=100)),
                ("dashboard_path", models.CharField(blank=True, default="", max_length=200)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="PortalTable",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("table_key", models.CharField(max_length=80)),
                ("table_name", models.CharField(max_length=120)),
                ("dashboard_route_name", models.CharField(blank=True, default="", max_length=100)),
                ("dashboard_path", models.CharField(blank=True, default="", max_length=200)),
                ("sort_order", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("portal", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tables", to="dashboard.portalregistry")),
            ],
            options={
                "ordering": ["portal__name", "sort_order", "table_name"],
            },
        ),
        migrations.AddConstraint(
            model_name="portaltable",
            constraint=models.UniqueConstraint(fields=("portal", "table_key"), name="uniq_portal_table_key"),
        ),
        migrations.RunPython(seed_portal_registry, unseed_portal_registry),
    ]
