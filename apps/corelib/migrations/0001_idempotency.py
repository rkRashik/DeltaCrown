# apps/corelib/migrations/0001_initial.py
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="IdempotencyKey",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
                ("scope", models.CharField(max_length=100, db_index=True)),
                ("token", models.CharField(max_length=64, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="idempotency_keys", to=settings.AUTH_USER_MODEL)),
            ],
            options={},
        ),
        migrations.AddConstraint(
            model_name="idempotencykey",
            constraint=models.UniqueConstraint(fields=("user", "scope", "token"), name="uq_idem_user_scope_token"),
        ),
        migrations.AddIndex(
            model_name="idempotencykey",
            index=models.Index(fields=("user", "scope", "token"), name="corelib_idem_user_scope_token_idx"),
        ),
    ]
