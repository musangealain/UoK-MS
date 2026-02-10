from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('lecturer', 'Lecturer'),
        ('admin', 'Admin'),
        ('staff', 'Staff'),
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


OFFICE_CHOICES = [
    ("ARG", "Office of the Registrar"),
    ("FIN", "Finance, Bursar & Procurement Office"),
    ("HRM", "Human Resources (HR)"),
    ("ACA", "Academic Affairs / Provost Office"),
    ("ADM", "Admissions and Student Services Office"),
    ("ELE", "E-Learning and Digital Education Office"),
    ("LIB", "University Library Services"),
]

OFFICE_PURPOSE = {
    "ARG": "Manages student registration, enrollment records, transcripts, course allocation, and academic records management.",
    "FIN": "Manages tuition and fee payments, budgeting, payroll, expenditure tracking, financial reporting, and procurement of goods, services, and equipment.",
    "HRM": "Manages staff records, recruitment processes, performance tracking, leave management, training programs, and payroll summaries.",
    "ACA": "Oversees curriculum development, course offerings, faculty workload, academic quality assurance, and accreditation compliance.",
    "ADM": "Handles student applications, admission decisions, enrollment statistics, student support services, and offer letter management.",
    "ELE": "Manages Learning Management Systems (LMS), online courses, virtual classrooms, digital content development, and e-learning support services.",
    "LIB": "Manages physical and digital library resources, book lending, e-resources access, research support, and library user services.",
}


class StaffProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staffprofile",
    )
    staff_id = models.CharField(max_length=20, unique=True)
    office_code = models.CharField(max_length=3, choices=OFFICE_CHOICES)
    issue_year = models.PositiveIntegerField()
    sequence = models.PositiveIntegerField()
    full_name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["office_code", "issue_year", "sequence"],
                name="uniq_staff_sequence_per_office_year",
            )
        ]
        indexes = [
            models.Index(fields=["office_code", "issue_year"]),
        ]

    def __str__(self):
        return f"{self.staff_id} - {self.full_name}"
