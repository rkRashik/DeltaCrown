from django.db import migrations, models


class Migration(migrations.Migration):
    """Additive: one new table, no change to existing tables or media references."""

    dependencies = [("common", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="PublishedMedia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=64)),
                ("field_name", models.CharField(max_length=64)),
                ("object_pk", models.CharField(max_length=64)),
                ("source_version", models.CharField(help_text="derivatives.version() of the original's storage name", max_length=12)),
                ("public_id", models.CharField(max_length=255, unique=True)),
                ("cdn_version", models.PositiveBigIntegerField(help_text="Cloudinary asset version stamp")),
                ("width", models.PositiveIntegerField()),
                ("height", models.PositiveIntegerField()),
                ("size_bytes", models.PositiveIntegerField()),
                ("status", models.CharField(choices=[("ready", "ready"), ("revoked", "revoked")], default="ready", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "indexes": [models.Index(fields=["label", "field_name", "object_pk"], name="pubmedia_lookup_idx")],
                "constraints": [models.UniqueConstraint(fields=("label", "field_name", "object_pk", "source_version"), name="uniq_published_media_source")],
            },
        ),
    ]
