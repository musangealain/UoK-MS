from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0007_staffprofile_extra_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="reg_password",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
