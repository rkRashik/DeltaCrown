"""Export references only; no file reads, DB writes, deletes or network transfer."""

import json
import os
from pathlib import Path
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from apps.common.media.fields import MediaFileField, MediaImageField
from apps.common.media.policy import storage_alias


class Command(BaseCommand):
    help = "Export confidential media references to an owner-controlled manifest (read-only DB)."

    def add_arguments(self, parser):
        parser.add_argument("--output", required=True)

    def handle(self, *args, **options):
        output = Path(options["output"])
        rows = []
        for model in apps.get_models():
            if model._meta.proxy:
                continue
            fields = [
                f for f in model._meta.fields if isinstance(f, (MediaFileField, MediaImageField))
            ]
            if not fields:
                continue
            # Include soft-deleted references for retention, never silently orphan evidence.
            for record in model._base_manager.values_list("pk", *(f.name for f in fields)).iterator(
                chunk_size=500
            ):
                for field, key in zip(fields, record[1:]):
                    if key:
                        rows.append(
                            {
                                "model": model._meta.label_lower,
                                "pk": str(record[0]),
                                "field": field.name,
                                "key": key,
                                "alias": storage_alias(field),
                            }
                        )
        # Exclusive creation prevents accidental overwrite of prior custody evidence.
        with output.open("x", encoding="utf-8") as handle:
            os.chmod(output, 0o600)
            json.dump(
                {"references": rows, "non_field_uploads_require_separate_inventory": True},
                handle,
                indent=2,
            )
        self.stdout.write(
            f"Exported {len(rows)} references. Treat the manifest as confidential; never commit it."
        )
