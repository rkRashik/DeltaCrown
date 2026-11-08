"""OL-07B: platform-wide image policy, privacy boundaries and shared template helpers. Synthetic data only."""
import io
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.template import Context, Template
from django.template.loader import get_template
from django.test import Client, override_settings
from PIL import Image

from apps.common.media import derivatives
from apps.common.media.fields import MediaImageField
from apps.common.media.policy import CLOUDINARY_PUBLIC_FIELDS, KNOWN_FIELDS, PUBLIC_FIELDS
from apps.common.tests.test_public_image_derivatives import _close, keys, png, stored  # noqa: F401

User = get_user_model()
ON = override_settings(OWNLOBBY_PUBLIC_DERIVATIVES=True)

EDITED_TEMPLATES = [
    "organizations/teams/team_directory.html", "organizations/teams/partials/find_team_v2.html",
    "teams/partials/_card.html", "organizations/org/org_directory.html", "tournaments/components/_tournament_card.html",
    "tournaments/detailPages/_detail_mobile.html", "tournaments/detailPages/detail.html", "tournaments/list.html",
    "tournaments/mobile/feed.html", "tournaments/public/player/my_tournaments.html", "tournaments/hub/hub.html",
    "ecommerce/product_list.html", "ecommerce/category_detail.html", "ecommerce/product_detail.html",
    "ecommerce/cart.html", "user_profile/profile/public_profile.html", "user_profile/profile/public_profile_mobile.html",
    "siteui/_arena_mobile.html", "Arena.html", "players/detail.html",
]


def test_eligibility_is_a_reviewed_subset_of_public_fields_with_a_cache_class_for_each():
    assert derivatives.ALLOWED == frozenset(derivatives.POLICY) and derivatives.ALLOWED <= PUBLIC_FIELDS
    for label, name in derivatives.ALLOWED:
        assert isinstance(apps.get_model(label)._meta.get_field(name), MediaImageField)
    private = KNOWN_FIELDS - PUBLIC_FIELDS  # KYC, evidence, payments, community media, ... never eligible
    assert not (private & derivatives.ALLOWED)
    assert ("siteui.communitypostmedia", "thumbnail") not in derivatives.ALLOWED
    assert "public" not in " ".join(derivatives.CACHE_CONTROL.values())
    # visibility/privacy-dependent artwork must revalidate (authorization runs on every request)
    for field in (("user_profile.userprofile", "avatar"), ("user_profile.userprofile", "banner"),
                  ("organizations.team", "logo"), ("tournaments.tournament", "banner_image"),
                  ("tournaments.tournamentsponsor", "logo")):
        assert derivatives.POLICY[field] == derivatives.REVALIDATE
    assert derivatives.CACHE_CONTROL[derivatives.REVALIDATE] == "private, no-cache"
    assert derivatives.POLICY[("games.game", "icon")] == derivatives.STABLE


def test_every_edited_template_still_compiles():
    for name in EDITED_TEMPLATES:
        get_template(name)


def test_derivative_authorization_matches_the_original_route_for_profile_avatars(db, stored):
    owner = User.objects.create_user(username="avatar-owner", email="avatar-owner@example.test")
    profile = owner.profile
    profile.avatar.save("me.png", ContentFile(png(1200, 1200)))
    stored.append(("x", profile.avatar.name))
    profile.refresh_from_db()
    assert derivatives.generate(profile.avatar) == "generated"
    original = f"/files/user_profile.userprofile/avatar/{profile.pk}/"
    url = derivatives.url(profile.avatar, "icon")
    stranger = Client()
    # whatever the original route says to a stranger, the derivative route says the same
    assert (stranger.get(url).status_code in (302, 404)) == (stranger.get(original).status_code == 404)
    mine = Client()
    mine.force_login(owner)
    response = mine.get(url)
    assert response.status_code == 200 and response["Cache-Control"] == "private, no-cache"
    etag = response["ETag"]
    _close(response)
    assert mine.get(url, HTTP_IF_NONE_MATCH=etag).status_code == 304
    from apps.user_profile.models_main import PrivacySettings
    PrivacySettings.objects.update_or_create(user_profile=profile, defaults={"is_private_account": True})
    assert stranger.get(original).status_code == 404  # private account: the original refuses a stranger ...
    assert stranger.get(url).status_code == 404 and stranger.get(url, HTTP_IF_NONE_MATCH=etag).status_code == 404
    assert mine.get(url, HTTP_IF_NONE_MATCH=etag).status_code == 304  # ... and so does the derivative, validator or not


def test_commerce_artwork_follows_the_record_active_state(db, stored):
    from apps.ecommerce.models import Category
    category = Category.objects.create(name="Gear", slug="gear", is_active=True)
    category.image.save("c.png", ContentFile(png(900, 600)))
    stored.append(("x", category.image.name))
    assert derivatives.generate(category.image) == "generated"
    url = derivatives.url(category.image, "card")
    client = Client()
    response = client.get(url)
    assert response.status_code == 200 and response["Cache-Control"] == "private, max-age=900, must-revalidate"
    _close(response)
    Category.objects.filter(pk=category.pk).update(is_active=False)
    assert client.get(url).status_code == 404  # same as the original route: revoked artwork is not served


def test_large_variant_sits_between_card_and_hero_and_is_generated(db, stored):
    from apps.games.models.game import Game
    game = Game.objects.create(name="Wide", slug="wide-game", default_team_size=1, profile_id_field="x",
                               default_result_type="map_score", is_active=True)
    game.banner.save("w.png", ContentFile(png(3840, 1240)))
    stored.append(("x", game.banner.name))
    assert list(derivatives.VARIANTS) == ["icon", "thumb", "card", "large", "hero"]
    assert derivatives.generate(game.banner) == "generated"
    with game.banner.storage.open(keys(game.banner)["large"], "rb") as handle:
        image = Image.open(io.BytesIO(handle.read()))
    assert image.size[0] == 960 and image.size[1] == round(960 * 1240 / 3840)  # aspect ratio kept, no padding


def test_template_helpers_pass_through_ungoverned_objects_and_urls_for_css(db, stored):
    plain = SimpleNamespace(url="/static/x.png")
    html = Template('{% load media_derivatives %}<img {% image_attrs b "thumb,card" "50vw" %}>{% image_url b "card" %}').render(
        Context({"b": plain}))
    assert html == '<img src="/static/x.png">/static/x.png'  # never raises, never invents derivative URLs
    from apps.games.models.game import Game
    game = Game.objects.create(name="Css", slug="css-game", default_team_size=1, profile_id_field="x",
                               default_result_type="map_score", is_active=True)
    game.banner.save("css.png", ContentFile(png(900, 300)))
    stored.append(("x", game.banner.name))
    tpl = Template('{% load media_derivatives %}{% image_url g.banner "card" %}')
    with override_settings(OWNLOBBY_PUBLIC_DERIVATIVES=False):
        assert tpl.render(Context({"g": game})) == f"/files/games.game/banner/{game.pk}/"
    with ON:
        assert tpl.render(Context({"g": game})).startswith(f"/files/derived/games.game/banner/{game.pk}/card/")


CDN = "https://res.cloudinary.com/synthetic/image/upload/v1/media/org/logo.png"


def _org_blob(url=CDN, label="organizations.organization", name="logo"):
    meta = SimpleNamespace(concrete_model=SimpleNamespace(_meta=SimpleNamespace(label_lower=label)))
    return SimpleNamespace(url=url, instance=SimpleNamespace(_meta=meta, pk=1), field=SimpleNamespace(name=name))


def test_cdn_brand_artwork_is_resized_by_cloudinary_only_in_hybrid_with_the_flag_and_never_touches_other_fields():
    assert ("organizations.organization", "logo") in CLOUDINARY_PUBLIC_FIELDS
    tpl = Template('{% load media_derivatives %}<img {% image_attrs b "thumb,card,hero" "50vw" %}>')
    blob = _org_blob()
    off = tpl.render(Context({"b": blob}))
    assert off == f'<img src="{CDN}">'  # default: unchanged
    with override_settings(OWNLOBBY_MEDIA_MODE="hybrid", OWNLOBBY_CLOUDINARY_TRANSFORMS=True):
        on = tpl.render(Context({"b": blob}))
        assert "c_limit,w_320,f_auto,q_auto" in on and "320w" in on and "1280w" in on and 'sizes="50vw"' in on
        assert tpl.render(Context({"b": _org_blob(url="https://example.com/a.png")})) == '<img src="https://example.com/a.png">'
        other = _org_blob(label="tournaments.tournament", name="banner_image")  # not CDN-published: untouched
        assert tpl.render(Context({"b": other})) == f'<img src="{CDN}">'
    with override_settings(OWNLOBBY_MEDIA_MODE="local", OWNLOBBY_CLOUDINARY_TRANSFORMS=True):
        assert tpl.render(Context({"b": blob})) == f'<img src="{CDN}">'  # only hybrid publishes on the CDN


def test_backfill_covers_new_models_and_reports_cdn_fields_as_unsupported_in_hybrid(db):
    from io import StringIO
    out = StringIO()
    call_command("generate_image_derivatives", stdout=out)
    for label in ("ecommerce.product", "organizations.team", "user_profile.userprofile", "tournaments.tournamentsponsor"):
        assert label.split(".")[1] in out.getvalue().lower()
    out = StringIO()
    with override_settings(OWNLOBBY_MEDIA_MODE="hybrid"):
        call_command("generate_image_derivatives", "--apply", "--model", "organizations.organization", stdout=out)
    assert "not supported" in out.getvalue()  # CDN-published brand artwork is never processed or copied
