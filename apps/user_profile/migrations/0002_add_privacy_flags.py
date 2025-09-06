from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("user_profile", "0001_initial"),  # adjust if your latest differs
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="is_private",
            field=models.BooleanField(default=False, help_text="Hide entire profile from public."),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="show_email",
            field=models.BooleanField(default=False, help_text="Allow showing my email on public profile."),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="show_phone",
            field=models.BooleanField(default=False, help_text="Allow showing my phone on public profile."),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="show_socials",
            field=models.BooleanField(default=True, help_text="Allow showing my social links/IDs on public profile."),
        ),
    ]
