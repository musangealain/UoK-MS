from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from dashboard.models import Application
@login_required
def student_dashboard(request):
    if request.user.userprofile.role != 'student':
        return redirect('home')
    if request.user.username.upper().startswith('REG') or request.user.userprofile.student_status == 'applicant':
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
    if not request.user.username.upper().startswith('REG') and request.user.userprofile.student_status != 'applicant':
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
            application.doc_id_uploaded = bool(request.POST.get('doc_id_uploaded'))
            application.doc_transcript_uploaded = bool(request.POST.get('doc_transcript_uploaded'))
            application.doc_recommendation_uploaded = bool(request.POST.get('doc_recommendation_uploaded'))
            if action == 'submit':
                if (
                    application.doc_id_uploaded
                    and application.doc_transcript_uploaded
                    and application.doc_recommendation_uploaded
                ):
                    application.status = 'under_review'
                    application.submitted_at = timezone.now()
            application.save()
        return redirect('applicant_dashboard')

    all_docs_uploaded = (
        application.doc_id_uploaded
        and application.doc_transcript_uploaded
        and application.doc_recommendation_uploaded
    )
    return render(
        request,
        'dashboard/student/applicant.html',
        {'application': application, 'all_docs_uploaded': all_docs_uploaded},
    )
