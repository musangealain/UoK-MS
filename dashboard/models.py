from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('lecturer', 'Lecturer'),
        ('admin', 'Admin'),
    ]
    STUDENT_STATUS_CHOICES = [
        ('applicant', 'Applicant'),
        ('enrolled', 'Enrolled'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='userprofile',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    student_status = models.CharField(
        max_length=20,
        choices=STUDENT_STATUS_CHOICES,
        default='applicant',
        blank=True,
    )

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Application(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    applicant = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='application',
        null=True,
        blank=True,
    )
    reg_number = models.CharField(max_length=20, unique=True)
    student_number = models.CharField(max_length=8, unique=True, null=True, blank=True)
    issued_password = models.CharField(max_length=64, null=True, blank=True)
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    program = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    doc_id_uploaded = models.BooleanField(default=False)
    doc_transcript_uploaded = models.BooleanField(default=False)
    doc_recommendation_uploaded = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reg_number} - {self.full_name}"
