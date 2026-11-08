"""Report (default) or re-encrypt OAuth token rows under the primary field-encryption key.

Run deliberately; never executed by migrations or deploys. Output is counts only: no token, ciphertext
or key is ever printed. Rows that cannot be decrypted are reported and never modified.
"""
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.models import TextField
from django.db.models.functions import Cast

from apps.user_profile.fields import classify_stored_value
from apps.user_profile.models.oauth import GameOAuthConnection

FIELDS = ("access_token", "refresh_token")


class Command(BaseCommand):
    help = "Count OAuth token rows by encryption status; with --apply re-encrypt legacy/plaintext rows."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Re-encrypt legacy and plaintext values (default is a dry run).")

    def handle(self, *args, **options):
        counts = Counter()
        updated = 0
        # Cast to a plain TextField so the stored (still encrypted) column is returned: the model
        # field would otherwise decrypt it and hide which key was used.
        rows = GameOAuthConnection.objects.annotate(
            raw_access=Cast("access_token", TextField()), raw_refresh=Cast("refresh_token", TextField())
        ).values_list("pk", "raw_access", "raw_refresh")
        for pk, access, refresh in rows.iterator():
            needs_rewrite = False
            for value in (access, refresh):
                status = classify_stored_value(value)
                counts[status] += 1
                needs_rewrite = needs_rewrite or status in {"legacy", "plaintext"}
            if options["apply"] and needs_rewrite:
                conn = GameOAuthConnection.objects.get(pk=pk)
                # Reading decrypted (or kept plaintext); saving encrypts with the primary key. An
                # undecryptable sibling field is an UndecryptableToken and is written back unchanged.
                conn.save(update_fields=[*FIELDS])
                updated += 1
        for status in ("primary", "legacy", "plaintext", "undecryptable", "empty"):
            self.stdout.write(f"{status}: {counts[status]}")
        self.stdout.write(f"rows rewritten: {updated}" if options["apply"] else "dry run: nothing was changed (use --apply)")
