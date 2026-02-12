from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0008_application_reg_password"),
    ]

    operations = [
        migrations.CreateModel(
            name="LecturerProfile",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("lecturer_id", models.CharField(max_length=20, unique=True)),
                ("module_code", models.CharField(choices=[("CSC121", "C++ Programming"), ("CSC212", "Data Structures And Algorithm"), ("CSC213", "Computer Architecture"), ("CSC221", "Object-Oriented Programming With Java"), ("CSC222", "Computer Maintenance And Repair"), ("CSC231", "Operations Research"), ("CSC232", "Programming With Python"), ("CSC233", "Network Security And Cryptography"), ("CSC311", "Visual Programming"), ("CSC312", "Wireless Network And Mobile Computing"), ("CSC313", "Multimedia And Computer Graphics"), ("CSC321", "Advanced Networking"), ("CSC322", "Artificial Intelligence"), ("CSC323", "Server And Systems Administration"), ("CSC332", "Internet-Of-Things And Embedded System Practice"), ("CSC333", "Advanced Java Programming"), ("CSC421", "Mobile Application Development"), ("CSC422", "Distributed And Cloud Computing")], max_length=10)),
                ("module_name", models.CharField(max_length=200)),
                ("issue_year", models.PositiveIntegerField()),
                ("sequence", models.PositiveIntegerField()),
                ("first_name", models.CharField(blank=True, default="", max_length=100)),
                ("surname", models.CharField(blank=True, default="", max_length=100)),
                ("last_name", models.CharField(blank=True, default="", max_length=100)),
                ("full_name", models.CharField(max_length=200)),
                ("assigned_password", models.CharField(blank=True, default="", max_length=64)),
                ("is_active", models.BooleanField(default=True)),
                ("deactivated_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="lecturerprofile", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "indexes": [models.Index(fields=["module_code", "issue_year"], name="dashboard_l_module__4c2b08_idx")],
            },
        ),
        migrations.AddConstraint(
            model_name="lecturerprofile",
            constraint=models.UniqueConstraint(fields=("module_code", "issue_year", "sequence"), name="uniq_lecturer_sequence_per_module_year"),
        ),
    ]
