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
    reg_password = models.CharField(max_length=64, null=True, blank=True)
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

MODULE_CHOICES = [
    ("CSC121", "C++ Programming"),
    ("CSC212", "Data Structures And Algorithm"),
    ("CSC213", "Computer Architecture"),
    ("CSC221", "Object-Oriented Programming With Java"),
    ("CSC222", "Computer Maintenance And Repair"),
    ("CSC231", "Operations Research"),
    ("CSC232", "Programming With Python"),
    ("CSC233", "Network Security And Cryptography"),
    ("CSC311", "Visual Programming"),
    ("CSC312", "Wireless Network And Mobile Computing"),
    ("CSC313", "Multimedia And Computer Graphics"),
    ("CSC321", "Advanced Networking"),
    ("CSC322", "Artificial Intelligence"),
    ("CSC323", "Server And Systems Administration"),
    ("CSC332", "Internet-Of-Things And Embedded System Practice"),
    ("CSC333", "Advanced Java Programming"),
    ("CSC421", "Mobile Application Development"),
    ("CSC422", "Distributed And Cloud Computing"),
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
    first_name = models.CharField(max_length=100, blank=True, default="")
    surname = models.CharField(max_length=100, blank=True, default="")
    last_name = models.CharField(max_length=100, blank=True, default="")
    full_name = models.CharField(max_length=200)
    assigned_password = models.CharField(max_length=64, blank=True, default="")
    is_active = models.BooleanField(default=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
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


class LecturerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lecturerprofile",
    )
    lecturer_id = models.CharField(max_length=20, unique=True)
    module_code = models.CharField(max_length=10, choices=MODULE_CHOICES)
    module_name = models.CharField(max_length=200)
    issue_year = models.PositiveIntegerField()
    sequence = models.PositiveIntegerField()
    first_name = models.CharField(max_length=100, blank=True, default="")
    surname = models.CharField(max_length=100, blank=True, default="")
    last_name = models.CharField(max_length=100, blank=True, default="")
    full_name = models.CharField(max_length=200)
    assigned_password = models.CharField(max_length=64, blank=True, default="")
    is_active = models.BooleanField(default=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["module_code", "issue_year", "sequence"],
                name="uniq_lecturer_sequence_per_module_year",
            )
        ]
        indexes = [
            models.Index(fields=["module_code", "issue_year"]),
        ]

    def __str__(self):
        return f"{self.lecturer_id} - {self.full_name}"


class PortalRegistry(models.Model):
    PORTAL_CHOICES = [
        ("student", "Student Portal"),
        ("lecturer", "Lecturer Portal"),
        ("staff", "Staff Portal"),
        ("admin", "Admin Portal"),
    ]

    code = models.CharField(max_length=20, choices=PORTAL_CHOICES, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    dashboard_route_name = models.CharField(max_length=100, blank=True, default="")
    dashboard_path = models.CharField(max_length=200, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class PortalTable(models.Model):
    portal = models.ForeignKey(
        PortalRegistry,
        on_delete=models.CASCADE,
        related_name="tables",
    )
    table_key = models.CharField(max_length=80)
    table_name = models.CharField(max_length=120)
    dashboard_route_name = models.CharField(max_length=100, blank=True, default="")
    dashboard_path = models.CharField(max_length=200, blank=True, default="")
    sort_order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["portal__name", "sort_order", "table_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["portal", "table_key"],
                name="uniq_portal_table_key",
            )
        ]

    def __str__(self):
        return f"{self.portal.code}:{self.table_name}"
