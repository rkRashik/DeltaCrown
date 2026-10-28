"""Brand identity, authenticated hero isolation and compatibility regressions."""
from datetime import timedelta
from io import BytesIO
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import xml.etree.ElementTree as ET

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, TestCase, override_settings
from django.template.loader import render_to_string
from django.utils import timezone

from apps.siteui.homepage_hero import (
    _get_active_match, _get_pending_action, _get_registered_tournament,
    _get_organized_tournament, _hero_organizer, get_home_hero_context,
)
from apps.siteui.homepage_presentation import UNIVERSAL_HEADLINE, get_homepage_presentation
from apps.common.seo import build_seo, organization_schema


class BrandIdentityTests(SimpleTestCase):
    def test_official_master_wordmarks_and_symbols_keep_exact_colors(self):
        for theme, own, lobby in [("dark", "#F6F1E7", "#E2B761"), ("light", "#141517", "#B17D31")]:
            svg = ET.parse(finders.find(settings.BRAND["logo_" + theme]))
            for segment, color in [("own", own), ("lobby", lobby)]:
                paths = [p for p in svg.iter() if p.attrib.get("data-brand-segment") == segment]
                self.assertTrue(paths)
                self.assertTrue(all(p.attrib["fill"] == color for p in paths))
            signal = next(p for p in svg.iter() if p.attrib.get("data-part") == "signal")
            self.assertEqual(signal.attrib["fill"], "#D8804C")
            self.assertEqual(svg.getroot().attrib["viewBox"], "0 0 1000 220")

    def test_canonical_origin_changes_only_with_site_url(self):
        for origin in ("https://deltacrown.xyz", "https://ownlobby.com"):
            with override_settings(SITE_URL=origin):
                seo = build_seo(path="/tournaments/")
                self.assertEqual(seo["canonical"], origin + "/tournaments/")
                self.assertIn("/static/ownlobby/", seo["og_image"])
                self.assertEqual(organization_schema()["name"], "OwnLobby")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="noreply@deltacrown.xyz", SITE_URL="https://deltacrown.xyz")
    def test_otp_email_uses_official_png_and_keeps_verified_sender(self):
        from apps.accounts.emails import send_otp_email
        user = SimpleNamespace(username="Player [[brand]]", email="qa@example.com", id=10)
        send_otp_email(user, "123456")
        message = mail.outbox[-1]
        self.assertIn("OwnLobby", message.subject)
        self.assertIn("noreply@deltacrown.xyz", message.from_email)
        html = message.alternatives[0].content
        self.assertIn("ownlobby/logos/primary-horizontal-dark.png", html)
        self.assertIn("Player [[brand]]", html)
        self.assertIn("123456", message.body)

    def test_universal_message_is_visible_and_context_reserved_in_same_heading(self):
        hero = dict(mode="team_manager", subcopy="Manage your roster.",
                    primary_cta_url="/teams/qa/manage/", primary_cta_label="Manage roster",
                    secondary_cta_url="/tournaments/", secondary_cta_label="Find events")
        ui = get_homepage_presentation({}, hero)
        html = render_to_string("partials/home_headline.html", {"home_ui": ui, "user": SimpleNamespace(is_authenticated=True)})
        self.assertEqual(UNIVERSAL_HEADLINE, ("Find tournaments.", "Build your team.", "Compete your way."))
        self.assertIn('class="ol-hero-context" aria-hidden="true"', html)
        self.assertNotIn('is-personalized', html)
        self.assertEqual(html.count('<h1 '), 1)
        self.assertEqual(ui['primary_url'], '/teams/qa/manage/')

    def test_guest_does_not_receive_contextual_message(self):
        hero = dict(mode="guest", primary_cta_url="/account/signup/", primary_cta_label="Create account", secondary_cta_url="/tournaments/", secondary_cta_label="Find events")
        self.assertFalse(get_homepage_presentation({}, hero)["contextual_headline"])

    def test_future_certificates_embed_approved_artwork_without_saving_records(self):
        from PIL import Image
        from apps.tournaments.services.certificate_service import CertificateService
        service = CertificateService()
        args = dict(tournament=SimpleNamespace(name="QA Cup [[brand]]"), registration=SimpleNamespace(),
                    certificate_type="participant", placement=None, language="en",
                    verification_code=uuid.uuid4(), qr_image=Image.new("RGB", (200, 200), "white"))
        with patch.object(service, "_get_participant_display_name", return_value="QA Player [[brand]]"):
            pdf = service._render_pdf_certificate(**args)
            png = service._render_png_certificate(**args)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertIn(b"OwnLobby Tournament Platform", pdf)
        self.assertGreaterEqual(pdf.count(b"/Subtype /Image"), 2)
        with Image.open(BytesIO(png)) as image:
            self.assertEqual(image.size, (1920, 1080))
            self.assertGreater(sum(count for count, color in image.getcolors(1920 * 1080) if color == (177, 125, 49)), 0)

    @override_settings(SITE_URL="https://ownlobby.com")
    def test_discord_embed_uses_brand_origin_and_logo_without_network_dispatch(self):
        from apps.tournaments.services.discord_webhook import DiscordWebhookService
        embed = DiscordWebhookService.build_embed("QA title", "QA description")
        self.assertIn("OwnLobby", embed["footer"]["text"])
        self.assertTrue(embed["footer"]["icon_url"].startswith("https://ownlobby.com/static/ownlobby/"))


class HeroOwnershipTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from apps.games.models import Game
        from apps.tournaments.models import Tournament
        User = get_user_model()
        cls.user = User.objects.create_user(username="brand_qa_player", email="player@example.com", password="qa-pass")
        cls.other = User.objects.create_user(username="brand_qa_other", email="other@example.com", password="qa-pass")
        cls.game = Game.objects.create(name="OwnLobby QA Game", display_name="OwnLobby QA Game", slug="ownlobby-qa-game", short_code="OLQA", category="OTHER")
        now = timezone.now()
        cls.tournament = Tournament.objects.create(
            name="QA Tournament [[brand]]", slug="ownlobby-qa-cup", organizer=cls.other,
            game=cls.game, participation_type="solo", status="registration_open",
            max_participants=16, registration_start=now-timedelta(days=1),
            registration_end=now+timedelta(days=1), tournament_start=now+timedelta(days=2),
        )

    def registration(self, **kwargs):
        from apps.tournaments.models import Registration
        return Registration.objects.create(tournament=self.tournament, user=self.user, status="confirmed", **kwargs)

    def match(self, participant, state="scheduled"):
        from apps.tournaments.models import Match
        return Match.objects.create(tournament=self.tournament, participant1_id=participant,
            participant2_id=self.other.pk, round_number=1, match_number=1, state=state,
            scheduled_time=timezone.now()+timedelta(days=2))

    def test_registration_does_not_expose_another_players_match(self):
        self.registration()
        self.match(self.user.pk + 1000, "check_in")
        self.assertIsNone(_get_pending_action(self.user))
        self.assertIsNone(_get_active_match(self.user))

    def test_own_match_is_available_and_tournament_title_is_preserved(self):
        self.registration()
        self.match(self.user.pk)
        context = _get_active_match(self.user)
        self.assertEqual(context["name"], "QA Tournament [[brand]]")
        self.assertEqual(context["url"], "/tournaments/ownlobby-qa-cup/hub/")

    def test_team_match_cannot_match_a_solo_user_id_by_collision(self):
        self.tournament.participation_type = "team"
        self.tournament.save(update_fields=["participation_type"])
        self.registration()
        self.match(self.user.pk)
        with patch("apps.siteui.homepage_hero._get_team_ids_for_user", return_value=[]):
            self.assertIsNone(_get_active_match(self.user))

    def test_solo_registration_is_available_without_a_team(self):
        self.registration()
        self.assertEqual(_get_registered_tournament(self.user).tournament_id, self.tournament.pk)
        with patch("apps.siteui.homepage_hero._is_profile_incomplete", return_value=False):
            self.assertEqual(get_home_hero_context(self.user)["mode"], "registered")

    def test_organizer_is_verified_by_actual_ownership(self):
        self.assertIsNone(_get_organized_tournament(self.user))
        organized = _get_organized_tournament(self.other)
        self.assertEqual(organized.pk, self.tournament.pk)
        self.assertEqual(_hero_organizer(organized)["primary_cta_url"], "/toc/ownlobby-qa-cup/")

    def test_homepage_prevents_shared_personalized_response_caching(self):
        self.client.force_login(self.user)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("private", response["Cache-Control"])
        self.assertIn("no-store", response["Cache-Control"])

    def test_existing_profile_save_contract_accepts_valid_iso_country(self):
        from django.urls import reverse
        self.client.force_login(self.user)
        response = self.client.post(reverse("user_profile:update_basic_info"), {
            "display_name": "QA Player [[brand]]", "bio": "Local QA only", "country": "BD",
        }, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.display_name, "QA Player [[brand]]")
        self.assertEqual(str(self.user.profile.country), "BD")
