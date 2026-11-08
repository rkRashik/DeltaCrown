"""OL-02C: re-signing stored editor-image URLs from a fallback signing key to the current one.

Synthetic keys (generated per run), synthetic images and disposable rows only. Needs the governed-media QA
settings (local public_media storage) and PostgreSQL, like the other media tests in the smoke job.
"""
import io
import logging
import secrets
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.core.management import call_command
from django.core.signals import request_finished
from django.core.management.base import CommandError
from django.db import close_old_connections
from django.test import Client, override_settings
from django.utils import timezone
from PIL import Image

from apps.common.management.commands import resign_editor_image_urls as cmd
from apps.common.media.editor import EditorStorage
from apps.games.models.game import Game
from apps.tournaments.models import Tournament

OLD = "synthetic-old-" + secrets.token_hex(32)
NEW = "synthetic-new-" + secrets.token_hex(32)
OTHER = "synthetic-other-" + secrets.token_hex(32)
SALT = "published-editor-image"
ROUTE = "/files/editor/"
User = get_user_model()


def _png():
    out = io.BytesIO()
    Image.new("RGB", (2, 2), (10, 120, 200)).save(out, "PNG")
    return ContentFile(out.getvalue(), name="synthetic.png")


def _token(url):
    return url[len(ROUTE):-1]


@pytest.fixture
def image(db):
    """A real stored editor image; its URL is signed under the OLD key."""
    with override_settings(SECRET_KEY=OLD, SECRET_KEY_FALLBACKS=[]):
        storage = EditorStorage()
        name = storage.save("synthetic.png", _png())
        url = storage.url(name)
    yield {"name": name, "old_url": url}
    storages["public_media"].delete(name)


@pytest.fixture
def make_tournament(db):
    game = Game.objects.create(name="Synthetic", slug="synthetic", default_team_size=1,
                               profile_id_field="ingame_id", default_result_type="map_score", is_active=True)
    organizer = User.objects.create_user(username="resign-org", email="resign-org@example.test")
    now = timezone.now()
    counter = iter(range(1000))

    def make(description="", rules_text=""):
        n = next(counter)
        return Tournament.objects.create(
            name=f"Resign Cup {n}", slug=f"resign-cup-{n}", organizer=organizer, game=game,
            format=Tournament.SINGLE_ELIM, participation_type=Tournament.SOLO, max_participants=4, min_participants=2,
            registration_start=now - timedelta(days=2), registration_end=now - timedelta(days=1),
            tournament_start=now + timedelta(days=1), tournament_end=now + timedelta(days=2),
            status=Tournament.DRAFT, description=description, rules_text=rules_text,
        )

    return make


def run(*args):
    out = StringIO()
    call_command("resign_editor_image_urls", *args, stdout=out, stderr=StringIO())
    return out.getvalue()


def fetch(url):
    response = Client().get(url)
    # Closing a streamed response fires request_finished, whose close_old_connections would drop the
    # test's open transaction (and its rows); the real request cycle is not under test here.
    request_finished.disconnect(close_old_connections)
    try:
        response.close()
    finally:
        request_finished.connect(close_old_connections)
    return response


def html(url):
    return f'<p>Intro</p><img class="x" src="{url}" alt="a"><p>Outro &amp; more</p>'


KEYS = dict(SECRET_KEY=NEW, SECRET_KEY_FALLBACKS=[OLD])


def test_old_url_works_with_fallback_resigned_url_works_with_new_key_only(image, make_tournament):
    t = make_tournament(description=html(image["old_url"]))
    with override_settings(**KEYS):
        assert fetch(image["old_url"]).status_code == 200  # 1. fallback keeps old URLs alive
        run("--apply")
    t.refresh_from_db()
    new_url = t.description.split('src="')[1].split('"')[0]
    assert new_url != image["old_url"] and new_url.startswith(ROUTE)
    with override_settings(SECRET_KEY=NEW, SECRET_KEY_FALLBACKS=[]):
        response = fetch(new_url)
        assert response.status_code == 200  # 2. re-signed URL needs only the new key
        assert fetch(image["old_url"]).status_code == 404  # 3. old signature fails once the fallback is gone
        assert response["Cache-Control"] == "private, no-store"  # 8. serving behavior unchanged
        assert response["X-Content-Type-Options"] == "nosniff"
    assert t.description == html(new_url)  # structure preserved byte for byte, only the token differs


def test_dry_run_is_read_only_and_apply_is_idempotent(image, make_tournament):
    original = html(image["old_url"])
    t = make_tournament(description=original, rules_text="no urls here")
    with override_settings(**KEYS):
        dry = run()
        assert "legacy: 1" in dry and "dry run" in dry
        t.refresh_from_db()
        assert t.description == original
        first = run("--apply")
        assert "records re-signed: 1, failed (unchanged): 0" in first
        t.refresh_from_db()
        after_first = t.description
        second = run("--apply")  # 4. nothing left to do: no change, no new tokens
        assert "legacy: 0" in second and "current: 1" in second and "records re-signed: 0" in second
        t.refresh_from_db()
        assert t.description == after_first
        assert t.rules_text == "no urls here"


def test_unrelated_content_is_never_touched(image, make_tournament):
    legacy = image["old_url"]
    bad_sig = ROUTE + _token(legacy)[:-3] + "xyz/"  # tampered signature
    other_salt = ROUTE + signing.dumps(image["name"], salt="something-else", key=OLD) + "/"
    private_name = ROUTE + signing.dumps("kyc/private-doc.png", salt=SALT, key=OLD) + "/"  # valid but not an editor image
    gone = ROUTE + signing.dumps("editor/does-not-exist.png", salt=SALT, key=OLD) + "/"
    external = f"https://example.com{legacy}"  # same path on another host
    private_file = "/files/user_profile.verificationrecord/id_document_front/1/"
    body = (
        f'<a href="{external}">x</a> <img src="{bad_sig}"> <img src="{other_salt}"> <img src="{private_name}">'
        f' <img src="{gone}"> <a href="{private_file}">doc</a> <code>{legacy}</code>-text plain-text ' + html(legacy)
    )
    t = make_tournament(description=body)
    with override_settings(**KEYS):
        summary = run("--apply")
    t.refresh_from_db()
    assert "invalid: 3" in summary and "missing: 1" in summary
    # exactly one URL changed: the properly delimited <img>. The external-host copy and the text-node copy
    # (preceded by '>') keep the old token; every other byte is identical.
    assert t.description.count(legacy) == 2
    new_url = t.description.split('class="x" src="')[1].split('"')[0]
    assert new_url != legacy
    assert t.description == body.replace(f'class="x" src="{legacy}"', f'class="x" src="{new_url}"')


def test_failed_record_keeps_original_and_other_records_still_migrate(image, make_tournament):
    a = make_tournament(description=html(image["old_url"]))
    b = make_tournament(description=html(image["old_url"]))
    calls = {"n": 0}
    real = signing.dumps

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("synthetic failure")
        return real(*args, **kwargs)

    with override_settings(**KEYS), patch.object(cmd.signing, "dumps", side_effect=flaky):
        out = StringIO()
        with pytest.raises(CommandError):
            call_command("resign_editor_image_urls", "--apply", stdout=out, stderr=StringIO())
    assert "records re-signed: 1, failed (unchanged): 1" in out.getvalue()
    a.refresh_from_db(); b.refresh_from_db()
    changed = [r for r in (a, b) if r.description != html(image["old_url"])]
    unchanged = [r for r in (a, b) if r.description == html(image["old_url"])]
    assert len(changed) == 1 and len(unchanged) == 1  # the failed record still has its working original
    with override_settings(**KEYS):
        assert fetch(image["old_url"]).status_code == 200


def test_unverifiable_token_does_not_migrate_and_hint_is_shown_without_fallbacks(image, make_tournament):
    t = make_tournament(description=html(image["old_url"]))
    with override_settings(SECRET_KEY=NEW, SECRET_KEY_FALLBACKS=[]):
        out = run("--apply")
    t.refresh_from_db()
    assert t.description == html(image["old_url"])
    assert "invalid: 1" in out and "no SECRET_KEY_FALLBACKS configured" in out


def test_output_and_logs_contain_no_keys_tokens_names_or_content(image, make_tournament, caplog):
    t = make_tournament(description="SECRET-PROSE " + html(image["old_url"]))
    caplog.set_level(logging.DEBUG)
    with override_settings(**KEYS):
        text = run() + run("--apply") + run("--discover")
        with override_settings(SECRET_KEY_FALLBACKS=[]):
            text += run()
    t.refresh_from_db()
    logged = " ".join(r.getMessage() for r in caplog.records)
    forbidden = [OLD, NEW, _token(image["old_url"]), image["name"], "SECRET-PROSE", "synthetic.png"]
    for value in forbidden + [_token(t.description.split('src="')[1].split('"')[0])]:
        assert value not in text and value not in logged


def test_discover_is_read_only_and_cannot_be_combined_with_apply(image, make_tournament):
    t = make_tournament(description=html(image["old_url"]))
    with override_settings(**KEYS):
        out = run("--discover")
        assert "tournaments.Tournament.description: 1" in out and "read-only" in out
        with pytest.raises(CommandError):
            run("--discover", "--apply")
    t.refresh_from_db()
    assert t.description == html(image["old_url"])


def test_only_text_fields_can_be_targeted(db):
    for bad in ("tournaments.Tournament.nope", "tournaments.Tournament.status", "tournaments.Tournament.organizer", "garbage"):
        with pytest.raises(CommandError):
            run("--field", bad)
    assert "dry run" in run("--field", "tournaments.Tournament.meta_description")
