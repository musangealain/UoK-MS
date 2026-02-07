from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from dashboard.models import UserProfile
@login_required
def admin_dashboard(request):
    if request.user.userprofile.role != 'admin':
        return redirect('home')
    users = (
        User.objects.select_related('userprofile')
        .all()
        .order_by('username')
    )
    return render(request, 'dashboard/admin/index.html', {'users': users})
