from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
@login_required
def lecturer_dashboard(request):
    if request.user.userprofile.role != 'lecturer':
        return redirect('home')
    return render(request, 'dashboard/lecturer/index.html')
