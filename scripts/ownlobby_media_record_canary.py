"""Read-only production-record canary for OwnLobby's hybrid private-media route.

Uses local release code + production Supabase DB/object store, but does not
modify records, media, cache, keys or access settings. No real identifiers,
URLs, usernames, filenames, media contents or credentials are printed.

This does NOT replace a deployed Render HTTP canary or independent restore.
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Direct invocation (python scripts/...) starts with scripts/ on sys.path,
# not the repository root. Match manage.py's import path on Windows and Linux.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["OWNLOBBY_MEDIA_MODE"] = "hybrid"
os.environ["DJANGO_SETTINGS_MODULE"] = "deltacrown.settings"

import django
django.setup()

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.db import connection, transaction
from django.test import RequestFactory
from rest_framework.test import force_authenticate

from apps.common.media.views import download
from apps.common.media.throttles import MediaReadThrottle
from apps.tournaments.models.registration import Payment
from django.contrib.auth import get_user_model


def read_only_canary():
    target = connection.settings_dict
    host = (target.get("HOST") or "").lower()
    name = target.get("NAME") or ""
    if not (host.endswith(".supabase.co") or host.endswith(".pooler.supabase.com")) or name != "postgres":
        raise RuntimeError("Expected production Supabase PostgreSQL; no queries issued")
    if getattr(settings, "OWNLOBBY_MEDIA_MODE", "") != "hybrid":
        raise RuntimeError("Governed hybrid mode not active")
    if settings.STORAGES.get("private_media", {}).get("BACKEND") != "apps.common.media.storage.ProtectedS3Storage":
        raise RuntimeError("Private S3 backend not selected")

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
        qs = (Payment.objects.filter(is_deleted=False, registration__is_deleted=False,
                                      registration__user__is_active=True)
              .select_related("registration__user")
              .order_by("pk"))
        candidate = None
        for payment in qs[:12]:
            if payment.registration.user_id is None:
                continue
            for field in ("payment_proof", "proof_image"):
                if getattr(payment, field):
                    candidate = (payment, field)
                    break
            if candidate:
                break
        if not candidate:
            raise RuntimeError("No eligible payment-proof owner record available")

        payment, field_name = candidate
        owner = payment.registration.user
        other = (get_user_model().objects.filter(is_active=True, is_staff=False,
                 is_superuser=False).exclude(pk=owner.pk).first())
        if other is None:
            raise RuntimeError("No independent non-owner account available")

        factory = RequestFactory()
        def invoke(method, actor=None):
            request = getattr(factory, method)(
                "/files/privacy-canary/", REMOTE_ADDR="127.0.0.1")
            if actor is not None:
                force_authenticate(request, user=actor)
            return download(request, "tournaments.payment", field_name, str(payment.pk))

        # No provider call is permitted for denied requests.
        with patch.object(MediaReadThrottle, "allow_request", return_value=True):
            with patch("apps.common.media.views.serve_blob") as origin:
                for who in (AnonymousUser(), other):
                    for method in ("get", "head"):
                        response = invoke(method, who)
                        try:
                            if response.status_code != 404:
                                raise RuntimeError("Unauthorized media route was not denied")
                        finally:
                            response.close()
                origin.assert_not_called()

            response = invoke("get", owner)
            try:
                if response.status_code != 200 or not response.streaming:
                    raise RuntimeError("Owner media route did not return a streamed file")
                part = next(iter(response.streaming_content), b"")
                if not isinstance(part, (bytes, bytearray)) or not part:
                    raise RuntimeError("Authorized S3-backed media returned no content")
                if response.get("Cache-Control") != "private, no-store":
                    raise RuntimeError("Private media cache header missing")
            finally:
                response.close()

    return True


if __name__ == "__main__":
    try:
        read_only_canary()
    except Exception as err:
        print("DJANGO_RECORD_MEDIA_FAIL:", type(err).__name__)
        raise SystemExit(2) from None
    print("DJANGO_RECORD_MEDIA_PASS")
    print("ANONYMOUS_DENIALS: 2")
    print("NONOWNER_DENIALS: 2")
    print("OWNER_STREAMED_READS: 1")
    print("NO_DATABASE_OR_STORAGE_WRITES")
    print("NOT VERIFIED: public Render session handling, backup restoration, Cloudinary CDN invalidation")
