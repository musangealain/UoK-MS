from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
@login_required
def student_dashboard(request):
    if request.user.userprofile.role != 'student':
        return redirect('home')
    return render(request, 'dashboard/student/index.html')
