"""
Phase 6 — Soft-delete standardization for Group and PaymentVerification.

Group: already had is_deleted (BooleanField), now inherits from SoftDeleteModel
which adds deleted_at / deleted_by and alters is_deleted with db_index.

PaymentVerification: new SoftDeleteModel fields (is_deleted, deleted_at, deleted_by).
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0048_move_bracket_to_brackets_app"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- Group: add deleted_at, deleted_by, alter is_deleted ---
        migrations.AddField(
            model_name="group",
            name="deleted_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp when this record was deleted",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="group",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                help_text="User who deleted this record",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_deletions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="group",
            name="is_deleted",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Flag indicating if this record has been soft-deleted",
            ),
        ),
        # --- PaymentVerification: add is_deleted, deleted_at, deleted_by ---
        migrations.AddField(
            model_name="paymentverification",
            name="is_deleted",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Flag indicating if this record has been soft-deleted",
            ),
        ),
        migrations.AddField(
            model_name="paymentverification",
            name="deleted_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp when this record was deleted",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="paymentverification",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                help_text="User who deleted this record",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_deletions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
