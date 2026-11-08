"""Inventory (default) or re-sign stored editor-image URLs from a fallback signing key to the current one.

Run deliberately, never from migrations, deploys or startup. Output is counts only: no key, token, URL,
record id or content is printed. Only the exact shape ``/files/editor/<token>/`` is considered, every token
must verify before it is touched, and only the token characters are replaced; surrounding content is kept
byte for byte. Tokens that fail verification or whose image is missing are never modified.

Statuses per URL: current (signed with the current key), legacy (verifies only via SECRET_KEY_FALLBACKS),
invalid (verifies with no configured key, or not an editor image name), missing (valid but the object is gone).
"""
import re
from collections import Counter

from django.apps import apps
from django.conf import settings
from django.core import signing
from django.core.exceptions import FieldDoesNotExist
from django.core.files.storage import storages
from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction
from django.urls import reverse

SALT = "published-editor-image"
# Fields wired to the rich-text widget in the admin; --field adds others explicitly.
DEFAULT_TARGETS = ("tournaments.Tournament.description", "tournaments.Tournament.rules_text")
TEXT_TYPES = (models.TextField, models.CharField)
TOKEN_CHARS = r"[A-Za-z0-9_\-:=]+"


def _prefix():
    return reverse("published_editor_media", args=["x"])[: -len("x/")]  # "/files/editor/"


def url_pattern():
    # Root-relative only, preceded by a delimiter: never a path inside an absolute/external URL.
    return re.compile(r"(?<=[\"'(=\s])" + re.escape(_prefix()) + "(?P<token>" + TOKEN_CHARS + ")/")


def classify_token(token, exists):
    """Return (status, name_or_None). ``exists`` is a callable name -> bool."""
    key = settings.SECRET_KEY
    try:
        name = signing.loads(token, salt=SALT, key=key, fallback_keys=[])
        status = "current"
    except signing.BadSignature:
        try:
            name = signing.loads(token, salt=SALT, key=key, fallback_keys=list(settings.SECRET_KEY_FALLBACKS))
            status = "legacy"
        except signing.BadSignature:
            return "invalid", None
    if not isinstance(name, str) or not name.startswith("editor/") or ".." in name or "\\" in name:
        return "invalid", None
    if not exists(name):
        return "missing", name
    return status, name


def resign(text, pattern, exists, counts=None, write=True):
    """Return text with legacy tokens re-signed (``write=False``: classify only, nothing is signed).

    Unverifiable, missing and current URLs are left as they are."""
    counts = counts if counts is not None else Counter()

    def swap(match):
        status, name = classify_token(match.group("token"), exists)
        counts[status] += 1
        if status != "legacy" or not write:
            return match.group(0)
        new = signing.dumps(name, salt=SALT, key=settings.SECRET_KEY)
        # Must verify under the current key alone (no fallback) and decode to the same image before use.
        if signing.loads(new, salt=SALT, key=settings.SECRET_KEY, fallback_keys=[]) != name:
            raise ValueError("re-signed token did not verify")
        return _prefix() + new + "/"

    return pattern.sub(swap, text), counts


def _field(label):
    try:
        app_label, model_name, field_name = label.split(".")
        field = apps.get_model(app_label, model_name)._meta.get_field(field_name)
    except (ValueError, LookupError, FieldDoesNotExist):
        raise CommandError(f"Unknown field (use app_label.Model.field): {label}") from None
    if not isinstance(field, TEXT_TYPES) or field.choices:
        raise CommandError(f"Only text fields can be targeted: {label}")
    return field


class Command(BaseCommand):
    help = "Count stored editor-image URLs by signing status; with --apply re-sign legacy ones to the current key."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Re-sign legacy URLs (default is a read-only dry run).")
        parser.add_argument("--field", action="append", default=[], metavar="app.Model.field",
                            help="Additional text field to include (repeatable).")
        parser.add_argument("--discover", action="store_true",
                            help="Read-only: count records per text field that contain an editor-image URL, across all models.")

    def handle(self, *args, **options):
        if options["discover"] and options["apply"]:
            raise CommandError("--discover is read-only and cannot be combined with --apply.")
        marker = _prefix()
        if options["discover"]:
            return self._discover(marker)
        fields = [_field(label) for label in (*DEFAULT_TARGETS, *options["field"])]
        pattern = url_pattern()
        cache = {}

        def exists(name):
            if name not in cache:
                cache[name] = storages["public_media"].exists(name)
            return cache[name]

        total, records, updated, failed = Counter(), 0, 0, 0
        for field in fields:
            model, attr = field.model, field.name
            candidates = model._default_manager.filter(**{attr + "__contains": marker}).values_list("pk", attr)
            for pk, value in candidates.iterator():
                records += 1
                _, counts = resign(value or "", pattern, exists, write=False)
                total.update(counts)
                if not options["apply"] or not counts["legacy"]:
                    continue
                try:
                    with transaction.atomic():
                        row = model._default_manager.select_for_update().filter(pk=pk).values_list(attr, flat=True).first()
                        # Recomputed from the locked value so a concurrent edit is never overwritten.
                        new, _ = resign(row or "", pattern, exists)
                        if new != row:
                            # update() writes only this column: no save() side effects, signals or other fields.
                            model._default_manager.filter(pk=pk).update(**{attr: new})
                            updated += 1
                except Exception:
                    failed += 1  # transaction rolled back: the original content is unchanged
        for status in ("current", "legacy", "invalid", "missing"):
            self.stdout.write(f"{status}: {total[status]}")
        self.stdout.write(f"records with editor-image URLs: {records}")
        if options["apply"]:
            self.stdout.write(f"records re-signed: {updated}, failed (unchanged): {failed}")
        else:
            self.stdout.write("dry run: nothing was changed (use --apply)")
        if not settings.SECRET_KEY_FALLBACKS and total["invalid"]:
            self.stdout.write("note: no SECRET_KEY_FALLBACKS configured, so URLs signed with a previous key count as invalid")
        if failed:
            raise CommandError(f"{failed} record(s) failed and were left unchanged")

    def _discover(self, marker):
        found = 0
        for model in apps.get_models():
            for field in model._meta.get_fields():
                if not isinstance(field, TEXT_TYPES) or field.choices or not getattr(field, "column", None):
                    continue
                try:
                    with transaction.atomic():  # savepoint: a failing table cannot poison the connection
                        n = model._default_manager.filter(**{field.name + "__contains": marker}).count()
                except Exception:
                    continue  # unmanaged/unavailable table: skipped, reported nowhere (counts only)
                if n:
                    found += n
                    self.stdout.write(f"{model._meta.label}.{field.name}: {n}")
        self.stdout.write(f"discover: {found} record(s) contain editor-image URLs (read-only)")
