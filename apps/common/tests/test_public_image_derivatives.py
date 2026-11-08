"""OL-07: public image derivatives. Synthetic images and disposable rows only (governed-media QA settings)."""
import io
from datetime import timedelta
from io import StringIO

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.template import Context, Template
from django.test import Client, override_settings
from django.utils import timezone
from PIL import Image

from apps.common.media import derivatives
from apps.common.media.policy import KNOWN_FIELDS, PUBLIC_FIELDS
from apps.games.models.game import Game
from apps.tournaments.models import Tournament

User = get_user_model()
ON = override_settings(OWNLOBBY_PUBLIC_DERIVATIVES=True)


def png(width, height, fmt="PNG"):
    """A smooth gradient: realistic dimensions, small enough to keep the test fast."""
    base = Image.linear_gradient("L").resize((width, height))
    out = io.BytesIO()
    Image.merge("RGB", (base, base.transpose(Image.FLIP_TOP_BOTTOM), base)).save(out, fmt)
    return out.getvalue()


@pytest.fixture
def stored():
    """Names to delete afterwards (originals) plus the whole derivatives tree, in both media storages."""
    names = []
    yield names
    import shutil
    from pathlib import Path
    from django.core.files.storage import storages
    for alias in ("public_media", "private_media"):
        storage = storages[alias]
        for _, name in names:
            try:
                storage.delete(name)
            except Exception:
                pass
        shutil.rmtree(Path(storage.location) / "derivatives", ignore_errors=True)


@pytest.fixture
def game(db, stored):
    g = Game.objects.create(name="Derivative Game", slug="derivative-game", default_team_size=1,
                            profile_id_field="ingame_id", default_result_type="map_score", is_active=True)
    g.icon.save("big.png", ContentFile(png(2048, 1526)))
    stored.append(("x", g.icon.name))
    g.refresh_from_db()
    return g


def _close(response):
    """Closing a streamed response fires request_finished -> close_old_connections, which would drop the
    test's open transaction; the real request cycle is not what is under test."""
    from django.core.signals import request_finished
    from django.db import close_old_connections
    request_finished.disconnect(close_old_connections)
    try:
        response.close()
    finally:
        request_finished.connect(close_old_connections)


def keys(blob):
    label, field, pk = derivatives._identity(blob)
    ver = derivatives.version(blob.name)
    return {v: derivatives.storage_key(label, field, pk, ver, v) for v in derivatives.VARIANTS}


def open_derivative(blob, variant):
    with blob.storage.open(keys(blob)[variant], "rb") as handle:
        return Image.open(io.BytesIO(handle.read()))


def test_generation_resizes_never_upscales_is_idempotent_and_keeps_the_original(game, stored):
    blob = game.icon
    original_name = blob.name
    assert derivatives.generate(blob) == "generated"
    for variant, edge in derivatives.VARIANTS.items():
        image = open_derivative(blob, variant)
        assert image.format == "WEBP"
        assert max(image.size) == edge  # source is larger than every variant
        assert abs(image.width / image.height - 2048 / 1526) < 0.02  # aspect ratio preserved
    assert derivatives.generate(blob) == "exists"  # repeat: nothing to do, original not even read
    game.refresh_from_db()
    assert game.icon.name == original_name and blob.storage.exists(original_name)  # reference and original intact

    small = Game.objects.create(name="Small", slug="small-game", default_team_size=1, profile_id_field="ingame_id",
                                default_result_type="map_score", is_active=True)
    small.icon.save("small.png", ContentFile(png(100, 80)))
    stored.append(("x", small.icon.name))
    assert derivatives.generate(small.icon) == "generated"
    assert {open_derivative(small.icon, v).size for v in derivatives.VARIANTS} == {(100, 80)}  # no upscaling


def test_only_the_reviewed_public_fields_are_eligible_and_bad_input_is_handled(game, stored):
    assert derivatives.ALLOWED <= PUBLIC_FIELDS
    for label, name in KNOWN_FIELDS - PUBLIC_FIELDS:  # every private/evidence field is refused
        assert (label, name) not in derivatives.ALLOWED
    for label, name in (("user_profile.verificationrecord", "id_document_front"), ("organizations.organization", "logo")):
        assert not derivatives.allowed(apps.get_model(label)._meta.get_field(name))

    storage = game.icon.storage
    cases = {
        "unsupported": storage.save("games/icons/bad.png", ContentFile(b"not an image")),
        "unsupported_animated": storage.save("games/icons/anim.gif", ContentFile(_animated_gif())),
        "missing": "games/icons/never-existed.png",
    }
    for name in cases.values():
        stored.append(("private_media", name))
    for expected, name in cases.items():
        Game.objects.filter(pk=game.pk).update(icon=name)
        game.refresh_from_db()
        assert derivatives.generate(game.icon) == expected.split("_")[0]
        assert not any(storage.exists(k) for k in keys(game.icon).values())  # nothing was created
    Game.objects.filter(pk=game.pk).update(icon=_big_name(game, stored))
    game.refresh_from_db()
    assert derivatives.generate(game.icon, max_pixels=1000) == "too_large"


def _animated_gif():
    out = io.BytesIO()
    frames = [Image.new("RGB", (8, 8), (255, 0, 0)), Image.new("RGB", (8, 8), (0, 0, 255))]
    frames[0].save(out, "GIF", save_all=True, append_images=frames[1:])
    return out.getvalue()


def _big_name(game, stored):
    name = game.icon.storage.save("games/icons/pixels.png", ContentFile(png(200, 200)))
    stored.append(("private_media", name))
    return name


def test_route_serves_derivatives_with_the_original_authorization_and_safe_fallbacks(game):
    blob = game.icon
    url = derivatives.url(blob, "card")
    client = Client()
    assert client.get(url).status_code == 302  # not generated yet: falls back to the original route
    assert client.get(url)["Location"] == f"/files/games.game/icon/{game.pk}/"
    derivatives.generate(blob)
    response = client.get(url)
    assert response.status_code == 200 and response["Content-Type"] == "image/webp"
    assert response["Cache-Control"] == "public, max-age=86400" and response["X-Content-Type-Options"] == "nosniff"
    _close(response)
    stale = url.rsplit("/", 1)[0] + "/0123456789ab.webp"
    assert client.get(stale).status_code == 302  # wrong version
    assert client.get(url.replace("/card/", "/bogus/")).status_code == 302
    Game.objects.filter(pk=game.pk).update(is_active=False)
    assert client.get(url).status_code == 404  # same authorization as the original: inactive game is not public
    assert client.get(f"/files/derived/games.game/slug/{game.pk}/card/abc.webp").status_code == 404
    assert client.get("/files/derived/user_profile.verificationrecord/id_document_front/1/card/abc.webp").status_code == 404


def test_conditionally_visible_artwork_is_not_publicly_cacheable_and_follows_visibility(game, stored):
    organizer = User.objects.create_user(username="deriv-org", email="deriv-org@example.test")
    now = timezone.now()
    t = Tournament.objects.create(
        name="Deriv Cup", slug="deriv-cup", organizer=organizer, game=game, format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.SOLO, max_participants=4, min_participants=2,
        registration_start=now - timedelta(days=2), registration_end=now - timedelta(days=1),
        tournament_start=now + timedelta(days=1), tournament_end=now + timedelta(days=2), status=Tournament.DRAFT)
    t.banner_image.save("banner.png", ContentFile(png(1600, 900)))
    stored.append(("private_media", t.banner_image.name))
    t.refresh_from_db()
    assert derivatives.generate(t.banner_image) == "generated"
    url = derivatives.url(t.banner_image, "card")
    assert Client().get(url).status_code == 404  # draft: not visible to the public
    owner = Client()
    owner.force_login(organizer)
    response = owner.get(url)
    assert response.status_code == 200 and response["Cache-Control"] == "private, max-age=900, must-revalidate"
    _close(response)
    Tournament.objects.filter(pk=t.pk).update(status=Tournament.PUBLISHED)
    response = Client().get(url)
    assert response.status_code == 200 and response["Cache-Control"].startswith("private")  # never `public`
    _close(response)


def test_template_tag_emits_srcset_only_when_enabled_and_always_has_a_valid_src(game):
    tpl = Template('{% load media_derivatives %}<img {% image_attrs g.icon "thumb,card,hero" "100vw" %}>'
                   '<img {% image_attrs g.icon "icon" %}>')
    original = f"/files/games.game/icon/{game.pk}/"
    with override_settings(OWNLOBBY_PUBLIC_DERIVATIVES=False):
        html = tpl.render(Context({"g": game}))
        assert html.count(f'src="{original}"') == 2 and "srcset" not in html  # default behavior unchanged
    with ON:
        html = tpl.render(Context({"g": game}))
    assert "320w" in html and "640w" in html and "1280w" in html and 'sizes="100vw"' in html
    assert html.count("/files/derived/games.game/icon/") == 5  # 3 srcset entries + default src + single icon
    assert original not in html


def test_list_page_uses_responsive_images_for_cards_and_logos(game, stored):
    organizer = User.objects.create_user(username="deriv-org2", email="deriv-org2@example.test")
    now = timezone.now()
    t = Tournament.objects.create(
        name="Listed Cup", slug="listed-cup", organizer=organizer, game=game, format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.SOLO, max_participants=4, min_participants=2,
        registration_start=now - timedelta(days=1), registration_end=now + timedelta(days=1),
        tournament_start=now + timedelta(days=2), tournament_end=now + timedelta(days=3),
        status=Tournament.REGISTRATION_OPEN)
    t.banner_image.save("banner.png", ContentFile(png(1600, 900)))
    stored.append(("private_media", t.banner_image.name))
    with ON:
        page = Client().get("/tournaments/").content.decode()
    card = f"/files/derived/tournaments.tournament/banner_image/{t.pk}/"
    assert f'srcset="{card}' in page and "1280w" in page and "(min-width: 768px) 50vw, 100vw" in page
    assert f"/files/derived/games.game/icon/{game.pk}/icon/" in page  # the 40px logo uses the 128px variant
    assert f'src="/files/tournaments.tournament/banner_image/{t.pk}/"' not in page
    with override_settings(OWNLOBBY_PUBLIC_DERIVATIVES=False):
        page = Client().get("/tournaments/").content.decode()
    assert f'src="/files/tournaments.tournament/banner_image/{t.pk}/"' in page  # original URL, as before


def test_new_uploads_are_derived_after_commit_only_when_enabled_and_never_fail_the_upload(
        db, stored, django_capture_on_commit_callbacks):
    g = Game.objects.create(name="Upload Game", slug="upload-game", default_team_size=1,
                            profile_id_field="ingame_id", default_result_type="map_score", is_active=True)
    with override_settings(OWNLOBBY_PUBLIC_DERIVATIVES=False), django_capture_on_commit_callbacks(execute=True):
        g.icon.save("off.png", ContentFile(png(400, 300)))
    stored.append(("private_media", g.icon.name))
    assert not any(g.icon.storage.exists(k) for k in keys(g.icon).values())
    with ON, django_capture_on_commit_callbacks(execute=True):
        g.icon.save("on.png", ContentFile(png(400, 300)))
    stored.append(("private_media", g.icon.name))
    assert all(g.icon.storage.exists(k) for k in keys(g.icon).values())
    from unittest.mock import patch
    with ON, patch.object(derivatives, "generate", side_effect=RuntimeError("synthetic")), \
            django_capture_on_commit_callbacks(execute=True):
        g.icon.save("boom.png", ContentFile(png(400, 300)))  # must not raise
    stored.append(("private_media", g.icon.name))
    g.refresh_from_db()
    assert g.icon.name.endswith(".png") and g.icon.storage.exists(g.icon.name)


def test_backfill_command_is_bounded_resumable_idempotent_and_status_only(game, stored):
    other = Game.objects.create(name="Second", slug="second-game", default_team_size=1, profile_id_field="ingame_id",
                                default_result_type="map_score", is_active=True)
    other.icon.save("second.png", ContentFile(png(900, 600)))
    stored.append(("private_media", other.icon.name))

    def run(*args):
        out = StringIO()
        call_command("generate_image_derivatives", *args, stdout=out)
        return out.getvalue()

    dry = run()
    assert "dry run" in dry and not any(game.icon.storage.exists(k) for k in keys(game.icon).values())
    with pytest.raises(CommandError):
        run("--apply")  # needs one explicit model
    first = run("--apply", "--model", "games.game", "--limit", "1")
    lower = min(game.pk, other.pk)
    assert "generated" in first and f"--after-pk {lower}" in first and "more remain" in first
    second = run("--apply", "--model", "games.game", "--limit", "5", "--after-pk", str(lower))
    assert "complete" in second
    again = run("--apply", "--model", "games.game", "--limit", "5")
    assert "exists" in again and "generated" not in again  # repeat run changes nothing
    for text in (dry, first, second, again):
        assert "big.png" not in text and "second.png" not in text and "Derivative Game" not in text
    assert game.icon.storage.exists(game.icon.name) and other.icon.storage.exists(other.icon.name)
