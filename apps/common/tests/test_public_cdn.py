"""OL-08: strict public-CDN eligibility, verified publication and safe fallback. Synthetic images, mocked provider."""
import itertools
from io import StringIO
from unittest import mock

import cloudinary
import cloudinary.exceptions
import pytest
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.template import Context, Template
from django.test import override_settings

from apps.common.media import cdn, derivatives
from apps.common.media.policy import KNOWN_FIELDS, PUBLIC_FIELDS
from apps.common.models import PublishedMedia
from apps.common.tests.test_public_image_derivatives import png, stored  # noqa: F401
from apps.games.models.game import Game

ON = override_settings(OWNLOBBY_PUBLIC_CDN=True)
SECRET = "synthetic-api-secret-value"


@pytest.fixture(autouse=True)
def provider(monkeypatch):
    cache.clear()
    cfg = cloudinary.config()
    saved = (cfg.cloud_name, cfg.api_key, cfg.api_secret)  # global SDK state: restore it for other tests
    cloudinary.config(cloud_name="synth", api_key="synthetic-key", api_secret=SECRET)
    monkeypatch.setattr(cdn, "_sleep", lambda s: None)
    yield
    cloudinary.config(cloud_name=saved[0], api_key=saved[1], api_secret=saved[2])
    cache.clear()


_seq = itertools.count(1)


def make_game(stored, slug="cdn-game", **extra):
    g = Game.objects.create(name=slug, slug=slug, short_code=f"C{next(_seq)}", default_team_size=1, profile_id_field="x",
                            default_result_type="map_score", is_active=True, **extra)
    g.icon.save("i.png", ContentFile(png(1400, 1000)))
    stored.append(("x", g.icon.name))
    g.refresh_from_db()
    return g


def reply(pid, **over):
    base = {"public_id": pid, "type": "upload", "access_mode": "public", "version": 4711, "width": 1280, "height": 914,
            "bytes": 5000}
    return {**base, **over}


def fake_upload(**over):
    def upload(file, **kw):
        return reply(kw["public_id"], **over)
    return mock.Mock(side_effect=upload)


def test_cdn_eligibility_is_a_small_reviewed_subset_that_excludes_dynamic_visibility_media():
    assert cdn.PUBLISHABLE <= derivatives.ALLOWED <= PUBLIC_FIELDS
    assert cdn.PUBLISHABLE < derivatives.ALLOWED  # strictly smaller: derivative-eligible is not CDN-eligible
    for excluded in [("ecommerce.product", "featured_image"), ("ecommerce.productimage", "image"),
                     ("organizations.team", "logo"), ("user_profile.userprofile", "avatar"),
                     ("tournaments.tournament", "banner_image"), ("tournaments.tournamentsponsor", "logo"),
                     ("siteui.communitypostmedia", "file"), ("tournaments.kycsubmission", "document_front"),
                     ("tournaments.payment", "payment_proof")]:
        assert excluded not in cdn.PUBLISHABLE
    assert not (KNOWN_FIELDS - PUBLIC_FIELDS) & cdn.PUBLISHABLE
    assert cdn.NAMESPACE.startswith("ownlobby-public/")


def test_url_is_versioned_immutable_and_every_other_state_falls_back(db, stored):
    g = make_game(stored)
    ver = derivatives.version(g.icon.name)
    assert cdn.url(g.icon, "card") is None  # flag off by default
    PublishedMedia.objects.create(label="games.game", field_name="icon", object_pk=str(g.pk), source_version=ver,
                                  public_id=cdn.public_id("games.game", "icon", g.pk, ver), cdn_version=4711,
                                  width=1280, height=914, size_bytes=5000)
    with ON:
        got = cdn.url(g.icon, "card")
        assert got == (f"https://res.cloudinary.com/synth/image/upload/c_limit,f_auto,q_auto,w_640/v4711/"
                       f"ownlobby-public/v1/games.game/icon/{g.pk}/{ver}")
        assert cdn.url(g.icon, "nonsense") is None
        Game.objects.filter(pk=g.pk).update(is_active=False)  # deactivated: the CDN copy is no longer advertised
        g.refresh_from_db()
        assert cdn.url(g.icon, "card") is None
        Game.objects.filter(pk=g.pk).update(is_active=True)
        g.icon.save("replaced.png", ContentFile(png(800, 600)))  # replaced original: new version, no stale CDN URL
        stored.append(("x", g.icon.name))
        assert cdn.url(g.icon, "card") is None
    with ON, override_settings(OWNLOBBY_MEDIA_MODE="legacy"):
        assert cdn.url(g.icon, "card") is None


def test_publication_uploads_once_verifies_and_is_idempotent_without_overwrite(db, stored):
    g = make_game(stored)
    upload = fake_upload()
    with mock.patch.object(cloudinary.uploader, "upload", upload):
        assert cdn.publish(g.icon) == "uploaded"
        assert cdn.publish(g.icon) == "already_present"
    assert upload.call_count == 1
    kw = upload.call_args.kwargs
    ver = derivatives.version(g.icon.name)
    assert kw["public_id"] == f"ownlobby-public/v1/games.game/icon/{g.pk}/{ver}"
    assert kw["overwrite"] is False and kw["type"] == "upload" and kw["unique_filename"] is False and kw["use_filename"] is False
    row = PublishedMedia.objects.get()
    assert (row.cdn_version, row.status, row.source_version) == (4711, "ready", ver)
    Game.objects.filter(pk=g.pk).update(is_active=False)
    g2 = make_game(stored, "cdn-inactive")
    Game.objects.filter(pk=g2.pk).update(is_active=False)
    g2.refresh_from_db()
    with mock.patch.object(cloudinary.uploader, "upload", upload):
        assert cdn.publish(g2.icon) == "skipped" and upload.call_count == 1  # inactive records are never published


def test_unsupported_source_and_non_eligible_field_are_not_uploaded(db, stored):
    g = make_game(stored)
    from apps.tournaments.models import Tournament
    upload = fake_upload()
    with mock.patch.object(cloudinary.uploader, "upload", upload):
        assert cdn.publish(Tournament(pk=1).banner_image) == "skipped"
        g.icon.storage.delete(g.icon.name)
        g.icon.storage.save(g.icon.name, ContentFile(b"not an image at all"))
        assert cdn.publish(g.icon) == "unsupported"
    assert upload.call_count == 0 and not PublishedMedia.objects.exists()


@pytest.mark.parametrize("response,stops", [
    ({"type": "authenticated"}, True), ({"access_mode": "authenticated"}, True), ({"public_id": "legacy/other"}, True),
    ({"version": "x"}, True)])
def test_unexpected_provider_visibility_or_identity_stops_without_a_mapping(db, stored, response, stops):
    g = make_game(stored)
    with mock.patch.object(cloudinary.uploader, "upload", fake_upload(**response)):
        with pytest.raises(cdn.Stop):
            cdn.publish(g.icon)
    assert not PublishedMedia.objects.exists()


def test_rate_limit_and_source_change_stop_and_transient_errors_retry_then_fail(db, stored):
    g = make_game(stored)
    with mock.patch.object(cloudinary.uploader, "upload", mock.Mock(side_effect=cloudinary.exceptions.RateLimited("x"))):
        with pytest.raises(cdn.Stop):
            cdn.publish(g.icon)
    flaky = mock.Mock(side_effect=OSError("boom"))
    with mock.patch.object(cloudinary.uploader, "upload", flaky):
        assert cdn.publish(g.icon) == "failed" and flaky.call_count == cdn.ATTEMPTS
    def swap(file, **kw):
        Game.objects.filter(pk=g.pk).update(icon="other/name.png")
        return reply(kw["public_id"])
    with mock.patch.object(cloudinary.uploader, "upload", mock.Mock(side_effect=swap)):
        with pytest.raises(cdn.Stop):
            cdn.publish(g.icon)
    assert not PublishedMedia.objects.exists()


def test_command_dry_run_contacts_nothing_validates_scope_and_prints_counts_only(db, stored):
    g = make_game(stored)
    upload = fake_upload()
    out = StringIO()
    with mock.patch.object(cloudinary.uploader, "upload", upload):
        call_command("publish_public_media", stdout=out)
        assert upload.call_count == 0 and "dry run" in out.getvalue()
        for bad in (["--apply"], ["--model", "tournaments.kycsubmission"], ["--model", "ecommerce.product", "--apply"],
                    ["--model", "games.game", "--apply", "--limit", "0"]):
            with pytest.raises(CommandError):
                call_command("publish_public_media", *bad)
        out = StringIO()
        call_command("publish_public_media", "--apply", "--model", "games.game", stdout=out)
    text = out.getvalue()
    assert "games.Game uploaded: 1" in text and "complete" in text
    for secret in (SECRET, "synthetic-key", g.icon.name, "ownlobby-public"):
        assert secret not in text
    out = StringIO()
    with mock.patch.object(cloudinary.uploader, "upload", upload):
        call_command("publish_public_media", "--apply", "--model", "games.game", stdout=out)
    assert "already_present: 1" in out.getvalue() and upload.call_count == 1


def test_command_stops_on_repeated_provider_errors_and_reports_the_resume_cursor(db, stored):
    for i in range(4):
        make_game(stored, f"cdn-err-{i}")
    flaky = mock.Mock(side_effect=OSError("boom"))
    with mock.patch.object(cloudinary.uploader, "upload", flaky), pytest.raises(CommandError, match="STOPPED"):
        call_command("publish_public_media", "--apply", "--model", "games.game", stdout=StringIO())
    assert flaky.call_count == cdn.ATTEMPTS * cdn.STOP_AFTER_ERRORS  # no fourth record was attempted


def test_templates_use_the_cdn_across_modules_and_keep_a_fallback(db, stored):
    from apps.ecommerce.models import Brand, Category
    g = make_game(stored)
    cat = Category.objects.create(name="Gear", slug="gear", is_active=True)
    cat.image.save("c.png", ContentFile(png(900, 600)))
    stored.append(("x", cat.image.name))
    brand = Brand.objects.create(name="Acme", slug="acme", is_active=True) if hasattr(Brand, "slug") else Brand.objects.create(name="Acme")
    brand.logo.save("b.png", ContentFile(png(500, 300)))
    stored.append(("x", brand.logo.name))
    with mock.patch.object(cloudinary.uploader, "upload", fake_upload()):
        assert [cdn.publish(f) for f in (g.icon, cat.image, brand.logo)] == ["uploaded"] * 3
    tpl = Template('{% load media_derivatives %}<img {% image_attrs g.icon "icon,card,hero" "50vw" %}>'
                   '<img {% image_attrs c.image "thumb,card" "50vw" %}><img {% image_attrs b.logo "icon" %}>{% image_url g.icon "card" %}')
    ctx = Context({"g": g, "c": cat, "b": brand})
    off = tpl.render(ctx)
    assert "res.cloudinary.com" not in off and "onerror" not in off  # default: everything exactly as before
    with ON:
        on = tpl.render(ctx)
    assert on.count("res.cloudinary.com/synth/image/upload/c_limit,f_auto,q_auto,w_") >= 6
    assert "w_128/" in on and "w_640/" in on and "w_1280/" in on and "640w" in on and 'sizes="50vw"' in on
    assert f'data-fallback-src="/files/games.game/icon/{g.pk}/"' in on and "onerror=" in on
    # a record without a mapping keeps its authorized route even with the flag on
    other = make_game(stored, "cdn-unmapped")
    with ON:
        assert "res.cloudinary.com" not in Template('{% load media_derivatives %}{% image_url g.icon "card" %}').render(
            Context({"g": other}))


def test_real_pages_emit_cdn_urls_only_for_published_art_and_python_helpers_agree(db, stored):
    from datetime import timedelta
    from django.contrib.auth import get_user_model
    from django.test import Client
    from django.utils import timezone
    from apps.siteui.homepage_extras import _img_url
    from apps.tournaments.models import Tournament
    g = make_game(stored)
    organizer = get_user_model().objects.create_user(username="cdn-org", email="cdn-org@example.test")
    now = timezone.now()
    Tournament.objects.create(
        name="Cdn Cup", slug="cdn-cup", organizer=organizer, game=g, format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.SOLO, max_participants=4, min_participants=2,
        registration_start=now - timedelta(days=1), registration_end=now + timedelta(days=1),
        tournament_start=now + timedelta(days=2), tournament_end=now + timedelta(days=3),
        status=Tournament.REGISTRATION_OPEN)
    with ON:
        before = Client().get("/tournaments/").content.decode()
        assert "res.cloudinary.com" not in before and _img_url(g.icon, "icon") == derivatives.variant_url(g.icon, "icon")
    with mock.patch.object(cloudinary.uploader, "upload", fake_upload()):
        assert cdn.publish(g.icon) == "uploaded"
    with ON:
        page = Client().get("/tournaments/").content.decode()
        assert f"res.cloudinary.com/synth/image/upload/c_limit,f_auto,q_auto,w_128/v4711/ownlobby-public/v1/games.game/icon/{g.pk}/" in page
        assert _img_url(g.icon, "icon").startswith("https://res.cloudinary.com/synth/") and _img_url(g.icon).startswith("/files/")
    assert "res.cloudinary.com" not in Client().get("/tournaments/").content.decode()  # flag off: rollback is instant


def test_max_images_is_a_hard_cap_across_fields_and_resumes_without_duplicates(db, stored):
    games = [make_game(stored, f"cdn-cap-{i}") for i in range(3)]
    for g in games:  # two eligible fields each: six images, three records
        g.logo.save("l.png", ContentFile(png(600, 400)))
        stored.append(("x", g.logo.name))
    upload = fake_upload()
    out = StringIO()
    with mock.patch.object(cloudinary.uploader, "upload", upload):
        dry = StringIO()
        call_command("publish_public_media", stdout=dry)
        assert "6 image(s) with a file" in dry.getvalue()
        call_command("publish_public_media", "--apply", "--model", "games.game", "--max-images", "5", stdout=out)
        assert upload.call_count == 5 and "uploaded: 5" in out.getvalue()
        cursor = games[2].pk - 1
        assert f"--after-pk {cursor}" in out.getvalue()
        out = StringIO()
        call_command("publish_public_media", "--apply", "--model", "games.game", "--max-images", "5",
                     "--after-pk", str(cursor), stdout=out)
    assert upload.call_count == 6 and "already_present: 1" in out.getvalue() and "uploaded: 1" in out.getvalue()
    assert PublishedMedia.objects.count() == 6


def test_max_pixels_lowers_the_decode_cap_and_skips_larger_sources(db, stored):
    make_game(stored, "cdn-pixels")  # 1400 x 1000 = 1.4 MP
    upload = fake_upload()
    out = StringIO()
    with mock.patch.object(cloudinary.uploader, "upload", upload):
        call_command("publish_public_media", "--apply", "--model", "games.game", "--max-pixels", "1000000", stdout=out)
    assert upload.call_count == 0 and "skipped: 1" in out.getvalue() and not PublishedMedia.objects.exists()
