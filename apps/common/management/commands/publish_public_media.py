"""Publish strictly approved public artwork to the Cloudinary CDN, in explicit bounded batches (OL-08).

Never run by deploys, migrations or startup. Default is a read-only dry run (counts only, no provider contact).
`--apply` needs one `--model`; it uploads a re-encoded 1280 px WebP master under a new namespaced, version-keyed
public id (`overwrite=False`, so legacy Cloudinary assets can never be overwritten) and records a `PublishedMedia`
row only after the provider's response was verified. Originals and the references stored in the database are never
changed. Output is counts and a resume cursor only: no names, ids, URLs, credentials or image content.

Safe to repeat (published records report `already_present`). Also the way future uploads become CDN-ready:
run it periodically (it only touches records that have no ready mapping for their current original).
It stops (non-zero exit) on rate limiting, refused credentials, unexpected asset visibility/identity, a source that
changed during publication, or repeated provider errors.

  publish_public_media --apply --model games.game --max-images 5 --max-pixels 8000000 [--after-pk N]

`--max-images` is a hard cap on images handled (a record can hold several eligible fields); `--limit` counts records.
`--max-pixels` lowers the decode cap (default 24 MP, ~100 MB decoded): use it on a small shared instance.
"""
import time
from collections import Counter

import cloudinary
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from apps.common.media import cdn
from apps.common.media.fields import enabled

MODELS = sorted({label for label, _ in cdn.PUBLISHABLE})


class Command(BaseCommand):
    help = "Publish approved public artwork to the Cloudinary CDN (dry run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Upload (default: dry run, no provider contact).")
        parser.add_argument("--model", choices=MODELS, help="Required with --apply.")
        parser.add_argument("--limit", type=int, default=20, help="Max records per run (default 20).")
        parser.add_argument("--max-images", type=int, default=0, help="Hard cap on images handled this run (default: none).")
        parser.add_argument("--max-pixels", type=int, default=0, help="Decode cap in pixels (default: 24 MP).")
        parser.add_argument("--after-pk", type=int, default=0, help="Resume after this primary key.")
        parser.add_argument("--max-seconds", type=int, default=120, help="Stop starting new records after this long.")

    def handle(self, *args, **options):
        if not enabled():
            raise CommandError("Governed media is not enabled (OWNLOBBY_MEDIA_MODE legacy): nothing to do.")
        if (options["limit"] < 1 or options["max_seconds"] < 1 or options["after_pk"] < 0
                or options["max_images"] < 0 or options["max_pixels"] < 0):
            raise CommandError("--limit and --max-seconds must be positive; other numeric options non-negative.")
        if options["apply"] and not options["model"]:
            raise CommandError("--apply requires --model (one model per run keeps the cursor unambiguous).")
        if options["after_pk"] and not options["model"]:
            raise CommandError("--after-pk requires --model.")
        if options["apply"]:
            config = cloudinary.config()
            if not (config.cloud_name and config.api_key and config.api_secret):
                raise CommandError("Cloudinary is not configured on this host (nothing was contacted).")
        for label in [options["model"]] if options["model"] else MODELS:
            self._run(apps.get_model(label), options)

    def _run(self, model, options):
        from apps.common.models import PublishedMedia
        label = model._meta.label_lower
        names = sorted(name for lab, name in cdn.PUBLISHABLE if lab == label)
        rows = model._base_manager.filter(pk__gt=options["after_pk"]).order_by("pk")
        if not options["apply"]:
            ready = PublishedMedia.objects.filter(label=label, status=PublishedMedia.READY).count()
            with_file = sum(rows.exclude(**{name: ""}).exclude(**{name + "__isnull": True}).count() for name in names)
            self.stdout.write(f"{model._meta.label}: {rows.count()} record(s) after cursor, {with_file} image(s) with a file "
                              f"(fields: {', '.join(names)}), {ready} ready mapping(s) "
                              "(dry run: nothing was uploaded; use --apply --model)")
            return
        deadline = time.monotonic() + options["max_seconds"]
        counts, done, cursor, more, errors, stopped, images = Counter(), 0, options["after_pk"], False, 0, None, 0
        cap = options["max_images"]
        for obj in rows.iterator(chunk_size=50):
            if done >= options["limit"] or time.monotonic() > deadline:
                more = True
                break
            done += 1
            cursor = obj.pk
            try:
                for name in names:
                    blob = getattr(obj, name)
                    if blob:
                        if cap and images >= cap:  # re-run from just before this record: finished fields report already_present
                            more, cursor, done = True, obj.pk - 1, done - 1
                            break
                        images += 1
                        status = cdn.publish(blob, max_pixels=options["max_pixels"] or None)
                        counts[status] += 1
                        errors = errors + 1 if status == "failed" else 0
                        if errors >= cdn.STOP_AFTER_ERRORS:
                            raise cdn.Stop("repeated provider errors")
            except cdn.Stop as exc:
                stopped = str(exc)
                break
            if more:
                break
        for status, n in sorted(counts.items()):
            self.stdout.write(f"{model._meta.label} {status}: {n}")
        self.stdout.write(f"{model._meta.label}: processed {done} record(s); "
                          + (f"more remain, resume with --model {model._meta.label} --after-pk {cursor}" if more else "complete"))
        if stopped:
            raise CommandError(f"STOPPED: {stopped}. Nothing further was attempted; investigate before resuming "
                               f"(--after-pk {cursor - 1}).")
