from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from dashboard.models import (
    AttendanceRecord,
    AttendanceSession,
    Enrollment,
    TeachingAssignment,
)


def _require_lecturer(request):
    if request.user.userprofile.role != 'lecturer':
        return False
    return True
@login_required
def lecturer_dashboard(request):
    if not _require_lecturer(request):
        return redirect('home')
    return render(request, 'dashboard/lecturer/index.html', {'current_page': 'overview'})


@login_required
def lecturer_courses(request):
    if not _require_lecturer(request):
        return redirect('home')
    return render(request, 'dashboard/lecturer/courses.html', {'current_page': 'courses'})


@login_required
def lecturer_course_assignments(request):
    if not _require_lecturer(request):
        return redirect('home')
    return render(request, 'dashboard/lecturer/course_assignments.html', {'current_page': 'course_assignments'})


@login_required
def lecturer_timetable(request):
    if not _require_lecturer(request):
        return redirect('home')
    return render(request, 'dashboard/lecturer/timetable.html', {'current_page': 'timetable'})


@login_required
def lecturer_materials(request):
    if not _require_lecturer(request):
        return redirect('home')
    return render(request, 'dashboard/lecturer/materials.html', {'current_page': 'materials'})


@login_required
def lecturer_student_lists(request):
    if not _require_lecturer(request):
        return redirect('home')
    return render(request, 'dashboard/lecturer/student_lists.html', {'current_page': 'student_lists'})


@login_required
def lecturer_course_enrollments(request):
    if not _require_lecturer(request):
        return redirect('home')
    return render(request, 'dashboard/lecturer/course_enrollments.html', {'current_page': 'course_enrollments'})


@login_required
def lecturer_attendance_sessions(request):
    if not _require_lecturer(request):
        return redirect('home')
    return render(request, 'dashboard/lecturer/attendance_sessions.html', {'current_page': 'attendance_sessions'})


@login_required
def lecturer_attendance_records(request):
    if not _require_lecturer(request):
        return redirect('home')
    return render(request, 'dashboard/lecturer/attendance_records.html', {'current_page': 'attendance_records'})


@login_required
def lecturer_academic_workspace(request):
    if not _require_lecturer(request):
        return redirect("home")

    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        try:
            if action == "create_attendance_session":
                assignment_id = int(request.POST.get("assignment_id") or 0)
                topic = (request.POST.get("topic") or "").strip()
                held_on = (request.POST.get("held_on") or "").strip()
                if not assignment_id or not topic:
                    raise ValueError("Teaching assignment and topic are required.")
                assignment = (
                    TeachingAssignment.objects.filter(
                        pk=assignment_id,
                        instructor=request.user,
                        is_active=True,
                    )
                    .only("id")
                    .first()
                )
                if not assignment:
                    raise ValueError("Teaching assignment not found.")
                attendance_kwargs = {
                    "teaching_assignment_id": assignment.id,
                    "topic": topic,
                }
                if held_on:
                    attendance_kwargs["held_on"] = held_on
                AttendanceSession.objects.create(**attendance_kwargs)
                request.session["lecturer_academic_flash"] = "Attendance session created."

            elif action == "mark_attendance":
                attendance_session_id = int(request.POST.get("attendance_session_id") or 0)
                student_id = int(request.POST.get("student_id") or 0)
                status = (request.POST.get("status") or "present").strip().lower()
                if status not in {"present", "absent", "late", "excused"}:
                    raise ValueError("Invalid attendance status.")
                attendance_session = (
                    AttendanceSession.objects.select_related("teaching_assignment")
                    .filter(
                        pk=attendance_session_id,
                        teaching_assignment__instructor=request.user,
                    )
                    .first()
                )
                if not attendance_session:
                    raise ValueError("Attendance session not found.")
                is_enrolled = Enrollment.objects.filter(
                    student_id=student_id,
                    module=attendance_session.teaching_assignment.module,
                    session=attendance_session.teaching_assignment.session,
                    status__in=["enrolled", "completed"],
                ).exists()
                if not is_enrolled:
                    raise ValueError("Student is not enrolled in this module/session.")
                AttendanceRecord.objects.update_or_create(
                    attendance_session=attendance_session,
                    student_id=student_id,
                    defaults={"status": status},
                )
                request.session["lecturer_academic_flash"] = "Attendance record saved."

        except ValueError as exc:
            request.session["lecturer_academic_error"] = str(exc)
        return redirect("lecturer_academic_workspace")

    assignments = (
        TeachingAssignment.objects.select_related("module", "session")
        .filter(instructor=request.user, is_active=True)
        .order_by("-created_at")
    )
    assignment_pairs = {(a.module_id, a.session_id) for a in assignments}

    enrollments = []
    for module_id, session_id in assignment_pairs:
        enrollments.extend(
            Enrollment.objects.select_related("student", "module", "session")
            .filter(
                module_id=module_id,
                session_id=session_id,
                status__in=["enrolled", "completed"],
            )
            .order_by("student__username")
        )

    for assignment in assignments:
        assignment.student_count = Enrollment.objects.filter(
            module_id=assignment.module_id,
            session_id=assignment.session_id,
            status__in=["enrolled", "completed"],
        ).count()

    attendance_sessions = (
        AttendanceSession.objects.select_related("teaching_assignment", "teaching_assignment__module", "teaching_assignment__session")
        .filter(teaching_assignment__instructor=request.user)
        .order_by("-held_on", "-id")
    )
    attendance_records = (
        AttendanceRecord.objects.select_related(
            "student",
            "attendance_session",
            "attendance_session__teaching_assignment__module",
        )
        .filter(attendance_session__teaching_assignment__instructor=request.user)
        .order_by("-marked_at")[:180]
    )

    return render(
        request,
        "dashboard/lecturer/academic_workspace.html",
        {
            "current_page": "academic_workspace",
            "assignments": assignments,
            "enrollments": enrollments,
            "attendance_sessions": attendance_sessions,
            "attendance_records": attendance_records,
            "flash": request.session.pop("lecturer_academic_flash", None),
            "flash_error": request.session.pop("lecturer_academic_error", None),
        },
    )
