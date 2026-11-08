"""Create WebP derivatives for existing allowlisted public artwork, in explicit bounded batches.

Never run by deploys, migrations or startup. Default is a read-only dry run (counts only). `--apply` needs one
`--model` and writes only new derivative files next to the originals (same storage); originals and database
rows are never touched. Output is counts and a resume cursor only: no names, ids, URLs or image content. Safe
to repeat: finished records report `exists` without reading the original.

Bounded, resumable:  generate_image_derivatives --apply --model games.game --limit 20 --max-seconds 120
then repeat with --after-pk <printed cursor> until it prints `complete`; then the next model.
"""
import time
from collections import Counter

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from apps.common.media import derivatives
from apps.common.media.fields import enabled

MODELS = sorted({label for label, _ in derivatives.ALLOWED})


class Command(BaseCommand):
    help = "Generate resized WebP derivatives for allowlisted public artwork (dry run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write derivatives (default: dry run).")
        parser.add_argument("--model", choices=MODELS, help="Required with --apply.")
        parser.add_argument("--limit", type=int, default=20, help="Max records per run (default 20).")
        parser.add_argument("--after-pk", type=int, default=0, help="Resume after this primary key.")
        parser.add_argument("--max-seconds", type=int, default=120, help="Stop starting new records after this long.")

    def handle(self, *args, **options):
        if not enabled():
            raise CommandError("Governed media is not enabled (OWNLOBBY_MEDIA_MODE legacy): nothing to do.")
        if options["limit"] < 1 or options["max_seconds"] < 1 or options["after_pk"] < 0:
            raise CommandError("--limit and --max-seconds must be positive and --after-pk non-negative.")
        if options["apply"] and not options["model"]:
            raise CommandError("--apply requires --model (one model per run keeps the cursor unambiguous).")
        if options["after_pk"] and not options["model"]:
            raise CommandError("--after-pk requires --model.")
        for label in [options["model"]] if options["model"] else MODELS:
            self._run(apps.get_model(label), options)

    def _run(self, model, options):
        label = model._meta.label_lower
        names = sorted(name for lab, name in derivatives.ALLOWED
                       if lab == label and derivatives.allowed(model._meta.get_field(name)))
        if not names:
            self.stdout.write(f"{model._meta.label}: not supported in the current media mode (published on the CDN)")
            return
        deadline = time.monotonic() + options["max_seconds"]
        rows = model._base_manager.filter(pk__gt=options["after_pk"]).order_by("pk")
        if not options["apply"]:
            self.stdout.write(f"{model._meta.label}: {rows.count()} record(s) after cursor, fields: {', '.join(names)} "
                              "(dry run: nothing was written; use --apply --model)")
            return
        counts, done, cursor, more = Counter(), 0, options["after_pk"], False
        for obj in rows.iterator(chunk_size=50):
            if done >= options["limit"] or time.monotonic() > deadline:
                more = True
                break
            done += 1
            cursor = obj.pk
            for name in names:
                blob = getattr(obj, name)
                if blob:
                    counts[derivatives.generate(blob)] += 1
        for status, n in sorted(counts.items()):
            self.stdout.write(f"{model._meta.label} {status}: {n}")
        self.stdout.write(f"{model._meta.label}: processed {done} record(s); "
                          + (f"more remain, resume with --model {model._meta.label} --after-pk {cursor}" if more else "complete"))
        if counts["error"]:
            raise CommandError(f"{counts['error']} image(s) failed; originals are untouched")
