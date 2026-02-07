from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.urls import reverse

from dashboard.models import UserProfile

# Create your views here.
def home(request):
    if request.user.is_authenticated:
        logout(request)
    return render(request, 'website/home.html')


def portal_student(request):
    logout(request)
    return redirect('student_login')


def portal_lecturer(request):
    logout(request)
    return redirect('lecturer_login')


def portal_admin(request):
    logout(request)
    return redirect('admin_login')


class StudentLoginView(LoginView):
    template_name = 'registration/login_student.html'
    def form_valid(self, form):
        user = form.get_user()
        if getattr(user, "userprofile", None) is None or user.userprofile.role != "student":
            logout(self.request)
            form.add_error(None, "This account is not a student account.")
            return self.form_invalid(form)
        return super().form_valid(form)
    def get_success_url(self):
        return '/dashboard/student/'


class LecturerLoginView(LoginView):
    template_name = 'registration/login_lecturer.html'
    def form_valid(self, form):
        user = form.get_user()
        if getattr(user, "userprofile", None) is None or user.userprofile.role != "lecturer":
            logout(self.request)
            form.add_error(None, "This account is not a lecturer account.")
            return self.form_invalid(form)
        return super().form_valid(form)
    def get_success_url(self):
        return '/dashboard/lecturer/'


class AdminLoginView(LoginView):
    template_name = 'registration/login_admin.html'
    def form_valid(self, form):
        user = form.get_user()
        if getattr(user, "userprofile", None) is None or user.userprofile.role != "admin":
            logout(self.request)
            form.add_error(None, "This account is not an admin account.")
            return self.form_invalid(form)
        return super().form_valid(form)
    def get_success_url(self):
        return '/dashboard/admin/'


def _handle_signup(request, role, template_name, redirect_url):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        if username and password:
            if User.objects.filter(username=username).exists():
                return render(request, template_name, {'error': 'Username already exists.'})
            user = User.objects.create_user(username=username, email=email, password=password)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.save()
            login(request, user)
            return redirect(redirect_url)
        return render(request, template_name, {'error': 'Username and password are required.'})
    return render(request, template_name)


def student_signup(request):
    return _handle_signup(request, 'student', 'registration/signup_student.html', '/dashboard/student/')


def lecturer_signup(request):
    return _handle_signup(request, 'lecturer', 'registration/signup_lecturer.html', '/dashboard/lecturer/')


def admin_signup(request):
    return _handle_signup(request, 'admin', 'registration/signup_admin.html', '/dashboard/admin/')
