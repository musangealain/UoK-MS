from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


def _require_lecturer(request):
    if request.user.userprofile.role != 'lecturer':
        return False
    return True
@login_required
def lecturer_dashboard(request):
    if not _require_lecturer(request):
        return redirect('home')
    return render(request, 'dashboard/lecturer/index.html')


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
