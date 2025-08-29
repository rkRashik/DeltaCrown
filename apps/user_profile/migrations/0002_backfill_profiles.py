from django.db import migrations

def backfill(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("user_profile", "UserProfile")
    for u in User.objects.all():
        UserProfile.objects.get_or_create(user_id=u.id, defaults={"display_name": u.username})

class Migration(migrations.Migration):
    dependencies = [
        ("user_profile", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
