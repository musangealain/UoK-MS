import random
import string
import re

from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.urls import reverse

from dashboard.models import Application, UserProfile
from .forms import ApplicantInfoForm, ProgramChoiceForm



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


def portal_staff(request):
    logout(request)
    return redirect("staff_login")


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
        username = getattr(self.request.user, "username", "")
        if username.upper().startswith("REG"):
            return '/dashboard/applicant/'
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
        if not re.match(r"^OIT\d{2}-\d{3}$", user.username or ""):
            logout(self.request)
            form.add_error(None, "Admin ID must use the OIT format (e.g., OIT26-001).")
            return self.form_invalid(form)
        return super().form_valid(form)
    def get_success_url(self):
        return '/dashboard/admin/'


class StaffLoginView(LoginView):
    template_name = "registration/login_staff.html"

    def form_valid(self, form):
        user = form.get_user()
        if getattr(user, "userprofile", None) is None or user.userprofile.role != "staff":
            logout(self.request)
            form.add_error(None, "This account is not a staff account.")
            return self.form_invalid(form)
        staff_profile = getattr(user, "staffprofile", None)
        if staff_profile is None:
            logout(self.request)
            form.add_error(None, "Staff profile is missing. Contact admin.")
            return self.form_invalid(form)
        if not getattr(staff_profile, "is_active", True) or not getattr(user, "is_active", True):
            logout(self.request)
            form.add_error(None, "This staff account is inactive. Contact admin.")
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        staff_profile = getattr(self.request.user, "staffprofile", None)
        office_code = getattr(staff_profile, "office_code", "") or ""
        return f"/dashboard/staff/{office_code.upper()}/"


def _handle_signup(request, role, template_name, redirect_url):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        if username and password:
            if role == 'admin' and not re.match(r"^OIT\d{2}-\d{3}$", username):
                return render(
                    request,
                    template_name,
                    {'error': 'Admin ID must use the OIT format (e.g., OIT26-001).'},
                )
            if User.objects.filter(username=username).exists():
                return render(request, template_name, {'error': 'Username already exists.'})
            user = User.objects.create_user(username=username, email=email, password=password)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            if role == 'student':
                profile.student_status = 'applicant'
            profile.save()
            login(request, user)
            return redirect(redirect_url)
        return render(request, template_name, {'error': 'Username and password are required.'})
    return render(request, template_name)


def student_signup(request):
    return _handle_signup(request, 'student', 'registration/signup_student.html', '/dashboard/student/')


def _generate_reg_number():
    while True:
        reg = f"REG{random.randint(1000, 9999)}"
        if not User.objects.filter(username=reg).exists():
            return reg


def _generate_password(length=8):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def apply_step1(request):
    if request.method == 'POST':
        form = ApplicantInfoForm(request.POST)
        if form.is_valid():
            request.session['apply_data'] = form.cleaned_data
            return redirect('apply_step2')
    else:
        form = ApplicantInfoForm()
    return render(request, 'website/apply_step1.html', {'form': form})


def apply_step2(request):
    data = request.session.get('apply_data')
    if not data:
        return redirect('apply_step1')
    if request.method == 'POST':
        form = ProgramChoiceForm(request.POST)
        if form.is_valid():
            reg_number = _generate_reg_number()
            password = _generate_password()
            user = User.objects.create_user(
                username=reg_number,
                email=data['email'],
                password=password,
            )
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = 'student'
            profile.student_status = 'applicant'
            profile.save()
            Application.objects.create(
                applicant=user,
                reg_number=reg_number,
                reg_password=password,
                full_name=data['full_name'],
                email=data['email'],
                phone=data['phone'],
                program=form.cleaned_data['program'],
            )
            subject = "Your UoK Applicant Portal Credentials"
            message = (
                "Thank you for applying to the University of Kigali.\n\n"
                f"Your applicant portal credentials:\nUsername: {reg_number}\nPassword: {password}\n\n"
                "Use these to log in via the Student Portal."
            )
            try:
                send_mail(subject, message, None, [data['email']], fail_silently=False)
                email_sent = True
            except Exception:
                email_sent = False
            request.session.pop('apply_data', None)
            response = render(
                request,
                'website/apply_done.html',
                {
                    'reg_number': reg_number,
                    'password': password,
                    'email': data['email'],
                    'email_sent': email_sent,
                },
            )
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response
    else:
        form = ProgramChoiceForm()
    return render(request, 'website/apply_step2.html', {'form': form})


def lecturer_signup(request):
    return _handle_signup(request, 'lecturer', 'registration/signup_lecturer.html', '/dashboard/lecturer/')


def admin_signup(request):
    return _handle_signup(request, 'admin', 'registration/signup_admin.html', '/dashboard/admin/')
