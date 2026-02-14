from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from dashboard.models import (
    AcademicSession,
    Application,
    AttendanceRecord,
    Enrollment,
    ProgramModule,
)
@login_required
def student_dashboard(request):
    if request.user.userprofile.role != 'student':
        return redirect('home')
    if request.user.userprofile.student_status == 'applicant':
        return redirect('applicant_dashboard')
    application = (
        Application.objects.filter(applicant=request.user).first()
        or Application.objects.filter(reg_number=request.user.username).first()
        or Application.objects.filter(student_number=request.user.username).first()
    )
    context = {
        'current_page': 'overview',
        'application': application,
    }
    return render(request, 'dashboard/student/index.html', context)


@login_required
def applicant_dashboard(request):
    if request.user.userprofile.role != 'student':
        return redirect('home')
    if request.user.userprofile.student_status != 'applicant':
        return redirect('student_dashboard')
    application = (
        Application.objects.filter(applicant=request.user).first()
        or Application.objects.filter(reg_number=request.user.username).first()
        or Application.objects.filter(student_number=request.user.username).first()
    )
    if not application:
        return render(request, 'dashboard/student/applicant.html', {'missing_application': True})

    if request.method == 'POST':
        if application.status == 'submitted':
            action = request.POST.get('action')
            if not application.submitted_at:
                application.doc_id_uploaded = bool(request.POST.get('doc_id_uploaded'))
                application.doc_transcript_uploaded = bool(request.POST.get('doc_transcript_uploaded'))
                application.doc_recommendation_uploaded = bool(request.POST.get('doc_recommendation_uploaded'))
            if action == 'submit':
                if (
                    application.doc_id_uploaded
                    and application.doc_transcript_uploaded
                    and application.doc_recommendation_uploaded
                ):
                    if not application.submitted_at:
                        application.submitted_at = timezone.now()
            application.save()
        return redirect('applicant_dashboard')

    all_docs_uploaded = (
        application.doc_id_uploaded
        and application.doc_transcript_uploaded
        and application.doc_recommendation_uploaded
    )
    is_final_submitted = bool(application.submitted_at and application.status == 'submitted')
    return render(
        request,
        'dashboard/student/applicant.html',
        {
            'application': application,
            'all_docs_uploaded': all_docs_uploaded,
            'is_final_submitted': is_final_submitted,
        },
    )


@login_required
def student_academic_workspace(request):
    if request.user.userprofile.role != "student":
        return redirect("home")
    if request.user.userprofile.student_status == "applicant":
        return redirect("applicant_dashboard")

    profile = request.user.userprofile

    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        try:
            if action == "enroll_self":
                module_id = int(request.POST.get("module_id") or 0)
                session_id = int(request.POST.get("session_id") or 0)
                if not profile.program_id:
                    raise ValueError("Your program is not assigned yet. Contact office staff.")
                if not ProgramModule.objects.filter(
                    program_id=profile.program_id,
                    module_id=module_id,
                ).exists():
                    raise ValueError("Selected module is not mapped to your program.")
                if not AcademicSession.objects.filter(pk=session_id, is_active=True).exists():
                    raise ValueError("Selected session is invalid.")
                Enrollment.objects.update_or_create(
                    student=request.user,
                    module_id=module_id,
                    session_id=session_id,
                    defaults={
                        "program_id": profile.program_id,
                        "status": "enrolled",
                    },
                )
                request.session["student_academic_flash"] = "Module enrollment saved."

            elif action == "drop_self":
                enrollment_id = int(request.POST.get("enrollment_id") or 0)
                updated = Enrollment.objects.filter(
                    pk=enrollment_id,
                    student=request.user,
                ).update(status="dropped")
                if not updated:
                    raise ValueError("Enrollment record not found.")
                request.session["student_academic_flash"] = "Enrollment dropped."

        except ValueError as exc:
            request.session["student_academic_error"] = str(exc)
        return redirect("student_academic_workspace")

    program_modules = ProgramModule.objects.none()
    if profile.program_id:
        program_modules = (
            ProgramModule.objects.select_related("module", "program")
            .filter(program_id=profile.program_id)
            .order_by("semester", "module__code")
        )

    sessions = AcademicSession.objects.filter(is_active=True).order_by("-year_start", "-semester")
    enrollments = (
        Enrollment.objects.select_related("module", "session", "program")
        .filter(student=request.user)
        .order_by("-enrolled_at")
    )
    attendance_records = (
        AttendanceRecord.objects.select_related(
            "attendance_session",
            "attendance_session__teaching_assignment__module",
        )
        .filter(student=request.user)
        .order_by("-marked_at")[:150]
    )

    return render(
        request,
        "dashboard/student/academic_workspace.html",
        {
            "current_page": "academic_workspace",
            "program": profile.program,
            "program_modules": program_modules,
            "sessions": sessions,
            "enrollments": enrollments,
            "attendance_records": attendance_records,
            "flash": request.session.pop("student_academic_flash", None),
            "flash_error": request.session.pop("student_academic_error", None),
        },
    )
