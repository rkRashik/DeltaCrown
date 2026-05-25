"""
Production-polish tests for the tournament create flow.

Covers:
  - TournamentHostingFeePayment model creation (waived / paid / failed)
  - charge_hosting_fee() audit record + PLATFORM_FEE reason
  - View uses get_hosting_fee_for_user() — staff_bypass_enabled=False charges staff
  - API uses get_hosting_fee_for_user() — fee=0 creates successfully
  - Slug IntegrityError retry — collision resolves, exhausted collision returns clean error
  - Template: wallet top-up CTA present, optional banner/logo file inputs supported
  - Admin view registered for TournamentHostingFeePayment
  - Fee=0 (fee disabled) → creation free + waived record
  - staff_bypass_enabled=False → staff charged same as regular user
"""
from __future__ import annotations

import base64
import json
import re
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.games.models.game import Game
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.hosting_fee_payment import TournamentHostingFeePayment
from apps.tournaments.models.hosting_config import TournamentHostingConfig
from apps.tournaments.services.hosting_fee import (
    charge_hosting_fee,
    get_hosting_fee_for_user,
    get_hosting_fee,
)

User = get_user_model()


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _fresh_name():
    return f"Test Tournament {uuid.uuid4().hex[:8]}"


def _test_email(label):
    return f"{label}-{uuid.uuid4().hex[:8]}@test.com"


def _test_game():
    game, _created = Game.objects.get_or_create(
        slug="create-flow-test-game",
        defaults={
            "name": "Create Flow Test Game",
            "display_name": "Create Flow Test Game",
            "short_code": "CFTG",
            "category": "FPS",
            "game_type": "TEAM_VS_TEAM",
            "platforms": ["PC"],
            "is_active": True,
        },
    )
    if not game.is_active:
        game.is_active = True
        game.save(update_fields=["is_active"])
    return game


def _api_payload(name=None, **overrides):
    now = timezone.now()
    p = {
        "name": name or _fresh_name(),
        "game_id": _test_game().id,
        "format": "single_elimination",
        "max_participants": 16,
        "min_participants": 2,
        "registration_start": (now + timedelta(hours=1)).isoformat(),
        "registration_end": (now + timedelta(days=4)).isoformat(),
        "tournament_start": (now + timedelta(days=7)).isoformat(),
        "description": "Test description.",
        "participation_type": "team",
        "has_entry_fee": False,
        "entry_fee_amount": "0.00",
        "entry_fee_currency": "BDT",
        "entry_fee_deltacoin": 0,
        "payment_methods": [],
        "prize_pool": "0.00",
        "prize_currency": "BDT",
        "prize_deltacoin": 0,
        "prize_distribution": {},
        "rules_text": "",
        "enable_check_in": True,
        "check_in_minutes_before": 15,
        "enable_dynamic_seeding": False,
        "enable_live_updates": True,
        "enable_certificates": True,
        "enable_challenges": False,
        "enable_fan_voting": False,
        "is_official": False,
        "meta_description": "",
    }
    p.update(overrides)
    return p


def _png_upload(name):
    return SimpleUploadedFile(
        name,
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        ),
        content_type="image/png",
    )


def _get_config():
    return TournamentHostingConfig.get_solo()


def _reset_config(**fields):
    """Reset config to known state and apply overrides."""
    cfg = _get_config()
    cfg.hosting_fee_enabled = True
    cfg.hosting_fee_dc = 500
    cfg.staff_bypass_enabled = True
    cfg.active_promo = "none"
    for k, v in fields.items():
        setattr(cfg, k, v)
    cfg.save()
    return cfg


# ──────────────────────────────────────────────────────────────
# 1.  TournamentHostingFeePayment model
# ──────────────────────────────────────────────────────────────

class HostingFeePaymentModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="feeuser", email="feeuser@test.com", password="x")
        self.game = _test_game()

    def _make_tour(self, name=None):
        now = timezone.now()
        slug = f"fee-tour-{uuid.uuid4().hex[:6]}"
        return Tournament.objects.create(
            name=name or _fresh_name(),
            slug=slug,
            game=self.game,
            organizer=self.user,
            format="single_elimination",
            max_participants=16,
            min_participants=2,
            registration_start=now + timedelta(hours=1),
            registration_end=now + timedelta(days=4),
            tournament_start=now + timedelta(days=7),
            status="draft",
            prize_pool=Decimal("0.00"),
            entry_fee_amount=Decimal("0.00"),
        )

    def test_waived_record_created(self):
        tour = self._make_tour()
        rec = TournamentHostingFeePayment.objects.create(
            user=self.user,
            tournament=tour,
            amount_dc=0,
            status=TournamentHostingFeePayment.Status.WAIVED,
            idempotency_key=f"test-waived-{uuid.uuid4().hex}",
        )
        self.assertEqual(rec.status, "waived")
        self.assertEqual(rec.amount_dc, 0)
        self.assertIsNone(rec.wallet_transaction_id)

    def test_mark_verified(self):
        admin = User.objects.create_user(username="adminv", email="adminv@test.com", is_staff=True, password="x")
        tour = self._make_tour()
        rec = TournamentHostingFeePayment.objects.create(
            user=self.user,
            tournament=tour,
            amount_dc=500,
            status=TournamentHostingFeePayment.Status.PAID,
            idempotency_key=f"test-paid-{uuid.uuid4().hex}",
        )
        rec.mark_verified(by_user=admin)
        rec.refresh_from_db()
        self.assertIsNotNone(rec.verified_at)
        self.assertEqual(rec.verified_by, admin)

    def test_mark_disputed(self):
        tour = self._make_tour()
        rec = TournamentHostingFeePayment.objects.create(
            user=self.user,
            tournament=tour,
            amount_dc=500,
            status=TournamentHostingFeePayment.Status.PAID,
            idempotency_key=f"test-disp-{uuid.uuid4().hex}",
        )
        rec.mark_disputed(notes="Suspicious txn")
        rec.refresh_from_db()
        self.assertEqual(rec.status, "disputed")
        self.assertIn("Suspicious", rec.notes)

    def test_str_representation(self):
        tour = self._make_tour("My Cup")
        rec = TournamentHostingFeePayment.objects.create(
            user=self.user,
            tournament=tour,
            amount_dc=0,
            status=TournamentHostingFeePayment.Status.WAIVED,
            idempotency_key=f"test-str-{uuid.uuid4().hex}",
        )
        self.assertIn("My Cup", str(rec))
        self.assertIn("feeuser", str(rec))


# ──────────────────────────────────────────────────────────────
# 2.  charge_hosting_fee() — waived path writes audit record
# ──────────────────────────────────────────────────────────────

class ChargeHostingFeeWaivedTest(TestCase):

    def setUp(self):
        _reset_config(hosting_fee_dc=500, staff_bypass_enabled=True)
        self.staff = User.objects.create_superuser(username="chstaff", email="chstaff@test.com", password="x")
        self.game = _test_game()
        now = timezone.now()
        self.tour = Tournament.objects.create(
            name=_fresh_name(),
            slug=f"ch-waive-{uuid.uuid4().hex[:6]}",
            game=self.game,
            organizer=self.staff,
            format="single_elimination",
            max_participants=16,
            min_participants=2,
            registration_start=now + timedelta(hours=1),
            registration_end=now + timedelta(days=4),
            tournament_start=now + timedelta(days=7),
            status="draft",
            prize_pool=Decimal("0.00"),
            entry_fee_amount=Decimal("0.00"),
        )

    def test_waived_record_written_for_exempt_staff(self):
        before = TournamentHostingFeePayment.objects.count()
        result = charge_hosting_fee(self.staff, self.tour)
        self.assertIsNone(result)
        after = TournamentHostingFeePayment.objects.count()
        self.assertEqual(after, before + 1)
        rec = TournamentHostingFeePayment.objects.get(tournament=self.tour)
        self.assertEqual(rec.status, "waived")
        self.assertEqual(rec.amount_dc, 0)

    def test_idempotent_waived_record(self):
        """Calling charge_hosting_fee twice does not create duplicate records."""
        charge_hosting_fee(self.staff, self.tour)
        charge_hosting_fee(self.staff, self.tour)
        count = TournamentHostingFeePayment.objects.filter(tournament=self.tour).count()
        self.assertEqual(count, 1)

    def test_fee_zero_config_writes_waived(self):
        _reset_config(hosting_fee_dc=0)
        regular = User.objects.create_user(username="regzero", email="regzero@test.com", password="x")
        now = timezone.now()
        tour2 = Tournament.objects.create(
            name=_fresh_name(),
            slug=f"ch-zero-{uuid.uuid4().hex[:6]}",
            game=self.game,
            organizer=regular,
            format="single_elimination",
            max_participants=16,
            min_participants=2,
            registration_start=now + timedelta(hours=1),
            registration_end=now + timedelta(days=4),
            tournament_start=now + timedelta(days=7),
            status="draft",
            prize_pool=Decimal("0.00"),
            entry_fee_amount=Decimal("0.00"),
        )
        result = charge_hosting_fee(regular, tour2)
        self.assertIsNone(result)
        rec = TournamentHostingFeePayment.objects.get(tournament=tour2)
        self.assertEqual(rec.status, "waived")

    def test_fee_disabled_writes_waived(self):
        _reset_config(hosting_fee_enabled=False)
        regular = User.objects.create_user(username="regoff", email="regoff@test.com", password="x")
        now = timezone.now()
        tour3 = Tournament.objects.create(
            name=_fresh_name(),
            slug=f"ch-off-{uuid.uuid4().hex[:6]}",
            game=self.game,
            organizer=regular,
            format="single_elimination",
            max_participants=16,
            min_participants=2,
            registration_start=now + timedelta(hours=1),
            registration_end=now + timedelta(days=4),
            tournament_start=now + timedelta(days=7),
            status="draft",
            prize_pool=Decimal("0.00"),
            entry_fee_amount=Decimal("0.00"),
        )
        result = charge_hosting_fee(regular, tour3)
        self.assertIsNone(result)
        rec = TournamentHostingFeePayment.objects.get(tournament=tour3)
        self.assertEqual(rec.status, "waived")


# ──────────────────────────────────────────────────────────────
# 3.  get_hosting_fee_for_user() — staff_bypass_enabled=False
# ──────────────────────────────────────────────────────────────

class HostingFeeStaffBypassTest(TestCase):

    def setUp(self):
        self.staff = User.objects.create_superuser(username="bypassstaff", email="bypassstaff@test.com", password="x")
        self.regular = User.objects.create_user(username="bypassreg", email="bypassreg@test.com", password="x")

    def test_staff_exempt_when_bypass_on(self):
        _reset_config(hosting_fee_dc=500, staff_bypass_enabled=True)
        self.assertEqual(get_hosting_fee_for_user(self.staff), 0)

    def test_staff_charged_when_bypass_off(self):
        _reset_config(hosting_fee_dc=500, staff_bypass_enabled=False)
        self.assertEqual(get_hosting_fee_for_user(self.staff), 500)

    def test_regular_always_charged(self):
        _reset_config(hosting_fee_dc=300)
        self.assertEqual(get_hosting_fee_for_user(self.regular), 300)

    def test_fee_disabled_returns_zero_for_all(self):
        _reset_config(hosting_fee_enabled=False)
        self.assertEqual(get_hosting_fee_for_user(self.staff), 0)
        self.assertEqual(get_hosting_fee_for_user(self.regular), 0)


# ──────────────────────────────────────────────────────────────
# 4.  API create — fee=0 succeeds; fee>0 with low balance → 402
# ──────────────────────────────────────────────────────────────

class CreateAPIFeeIntegrationTest(TestCase):

    def setUp(self):
        _reset_config(hosting_fee_dc=500, staff_bypass_enabled=True)
        self.staff = User.objects.create_superuser(username="apistaff", email="apistaff@test.com", password="x")
        self.regular = User.objects.create_user(username="apireg", email="apireg@test.com", password="x")
        self.url = reverse("tournaments_api:tournament-list")

    def _post(self, user, **kw):
        c = Client()
        c.force_login(user)
        return c.post(self.url, json.dumps(_api_payload(**kw)), content_type="application/json")

    def _post_multipart(self, user, **kw):
        payload = _api_payload(**kw)
        for key in ("prize_distribution", "payment_methods", "meta_keywords"):
            if key in payload:
                payload[key] = json.dumps(payload[key])
        payload["banner_image"] = _png_upload("banner.png")
        payload["thumbnail_image"] = _png_upload("thumb.png")
        c = Client()
        c.force_login(user)
        return c.post(self.url, payload)

    def _post_multipart_payload(self, user, payload):
        c = Client()
        c.force_login(user)
        return c.post(self.url, payload)

    def test_staff_creates_successfully(self):
        resp = self._post(self.staff, name=_fresh_name())
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["hosting_fee_charged"], 0)

    def test_staff_creates_successfully_with_optional_media(self):
        resp = self._post_multipart(self.staff, name=_fresh_name())
        self.assertEqual(resp.status_code, 201, resp.content)
        slug = resp.json()["tournament"]["slug"]
        tournament = Tournament.objects.get(slug=slug)
        self.assertTrue(tournament.banner_image)
        self.assertTrue(tournament.thumbnail_image)

    def test_staff_multipart_empty_optional_json_fields_uses_defaults(self):
        payload = _api_payload(name=_fresh_name())
        payload["prize_distribution"] = ""
        payload["payment_methods"] = ""
        payload["meta_keywords"] = ""
        payload["banner_image"] = _png_upload("banner.png")
        payload["thumbnail_image"] = _png_upload("thumb.png")

        resp = self._post_multipart_payload(self.staff, payload)
        self.assertEqual(resp.status_code, 201, resp.content)
        tournament = Tournament.objects.get(slug=resp.json()["tournament"]["slug"])
        self.assertEqual(tournament.prize_distribution, {})
        self.assertEqual(tournament.payment_methods, [])
        self.assertEqual(tournament.meta_keywords, [])

    def test_staff_multipart_invalid_json_returns_clean_400(self):
        payload = _api_payload(name=_fresh_name())
        payload["payment_methods"] = "{not-json"
        payload["banner_image"] = _png_upload("banner.png")
        payload["thumbnail_image"] = _png_upload("thumb.png")

        resp = self._post_multipart_payload(self.staff, payload)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "VALIDATION_ERROR")

    def test_regular_user_no_balance_gets_402(self):
        resp = self._post(self.regular, name=_fresh_name())
        self.assertEqual(resp.status_code, 402)
        data = resp.json()
        self.assertEqual(data["error"], "INSUFFICIENT_DELTACOIN")
        self.assertEqual(data["hosting_fee"], 500)

    def test_fee_disabled_regular_user_creates_free(self):
        _reset_config(hosting_fee_enabled=False)
        resp = self._post(self.regular, name=_fresh_name())
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["hosting_fee_charged"], 0)

    def test_fee_zero_regular_user_creates_free(self):
        _reset_config(hosting_fee_dc=0)
        resp = self._post(self.regular, name=_fresh_name())
        self.assertEqual(resp.status_code, 201)

    def test_waived_fee_creates_audit_record(self):
        _reset_config(hosting_fee_enabled=False)
        name = _fresh_name()
        resp = self._post(self.staff, name=name)
        self.assertEqual(resp.status_code, 201)
        slug = resp.json()["tournament"]["slug"]
        tour = Tournament.objects.get(slug=slug)
        self.assertTrue(
            TournamentHostingFeePayment.objects.filter(
                tournament=tour, status="waived"
            ).exists()
        )

    def test_402_creates_no_tournament(self):
        before = Tournament.objects.count()
        self._post(self.regular, name=_fresh_name())
        self.assertEqual(Tournament.objects.count(), before)

    def test_redirect_url_in_response(self):
        resp = self._post(self.staff, name=_fresh_name())
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        slug = data["tournament"]["slug"]
        self.assertEqual(data["redirect_url"], f"/toc/{slug}/?onboarding=true")


# ──────────────────────────────────────────────────────────────
# 5.  Create page GET — fee reflects config
# ──────────────────────────────────────────────────────────────

class CreatePageContextTest(TestCase):

    def setUp(self):
        self.staff = User.objects.create_superuser(username="ctxstaff", email="ctxstaff@test.com", password="x")
        self.regular = User.objects.create_user(username="ctxreg", email="ctxreg@test.com", password="x")

    def _get(self, user):
        c = Client()
        c.force_login(user)
        return c.get("/tournaments/create/")

    def test_staff_page_loads(self):
        _reset_config(hosting_fee_dc=500, staff_bypass_enabled=True)
        resp = self._get(self.staff)
        self.assertEqual(resp.status_code, 200)

    def test_csrf_token_in_page(self):
        resp = self._get(self.staff)
        html = resp.content.decode()
        m = re.search(r'data-csrf-token="([^"]{10,})"', html)
        self.assertIsNotNone(m, "CSRF token missing from page")

    def test_regular_user_sees_balance_warning_when_broke(self):
        _reset_config(hosting_fee_dc=500)
        resp = self._get(self.regular)
        html = resp.content.decode()
        self.assertIn("required to host", html)
        self.assertIn("Top up wallet", html)
        self.assertIn("/wallet/hub/", html)

    def test_no_warning_when_fee_is_zero(self):
        _reset_config(hosting_fee_dc=0)
        resp = self._get(self.regular)
        html = resp.content.decode()
        # can_afford should be true when fee=0
        self.assertIn('data-can-afford="true"', html)
        self.assertNotIn("required to host", html)

    def test_file_upload_inputs_present(self):
        """Create flow intentionally supports banner/logo uploads before launch."""
        resp = self._get(self.staff)
        html = resp.content.decode()
        self.assertIn('id="bannerInput"', html)
        self.assertIn('id="logoInput"', html)

    def test_post_create_upload_hint_present(self):
        resp = self._get(self.staff)
        html = resp.content.decode()
        self.assertIn("after creation", html.lower())

    def test_no_inline_onclick_in_template(self):
        resp = self._get(self.staff)
        html = resp.content.decode()
        self.assertNotIn("onclick=", html)

    def test_proceed_launch_button_uses_data_attr(self):
        resp = self._get(self.staff)
        html = resp.content.decode()
        self.assertIn("data-proceed-launch", html)


# ──────────────────────────────────────────────────────────────
# 6.  Slug collision handling
# ──────────────────────────────────────────────────────────────

class SlugCollisionTest(TestCase):

    def setUp(self):
        _reset_config(hosting_fee_enabled=False)
        self.staff = User.objects.create_superuser(username="slugstaff", email="slugstaff@test.com", password="x")
        self.url = reverse("tournaments_api:tournament-list")
        self.c = Client()
        self.c.force_login(self.staff)

    def _post(self, name):
        return self.c.post(
            self.url,
            json.dumps(_api_payload(name=name)),
            content_type="application/json",
        )

    def test_duplicate_name_gets_different_slug(self):
        name = _fresh_name()
        r1 = self._post(name)
        r2 = self._post(name)
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)
        slug1 = r1.json()["tournament"]["slug"]
        slug2 = r2.json()["tournament"]["slug"]
        self.assertNotEqual(slug1, slug2)

    def test_three_collisions_all_succeed(self):
        name = _fresh_name()
        slugs = set()
        for _ in range(3):
            resp = self._post(name)
            self.assertEqual(resp.status_code, 201)
            slugs.add(resp.json()["tournament"]["slug"])
        self.assertEqual(len(slugs), 3)

    def test_service_raises_clean_validation_error_on_exhausted_retries(self):
        """Verify clean ValidationError is raised (not IntegrityError) when retries exhausted."""
        from apps.tournaments.services.tournament_service import TournamentService

        game = _test_game()
        now = timezone.now()
        data = {
            "name": "Collision Cup",
            "game_id": game.id,
            "format": "single_elimination",
            "max_participants": 16,
            "min_participants": 2,
            "registration_start": now + timedelta(hours=1),
            "registration_end": now + timedelta(days=4),
            "tournament_start": now + timedelta(days=7),
            "description": "Test",
        }

        # Patch Tournament.save to always raise IntegrityError with "slug" in message
        from django.db import IntegrityError as IE

        call_count = [0]

        def always_collide(*args, **kwargs):
            call_count[0] += 1
            raise IE("duplicate key value violates unique constraint (slug)")

        with patch.object(Tournament, "save", side_effect=always_collide):
            with self.assertRaises(ValidationError) as ctx:
                TournamentService.create_tournament(self.staff, data)
        self.assertIn("similar URL", str(ctx.exception))
        self.assertEqual(call_count[0], 5)  # 5 attempts


# ──────────────────────────────────────────────────────────────
# 7.  Admin registration
# ──────────────────────────────────────────────────────────────

class AdminRegistrationTest(TestCase):

    def test_hosting_fee_payment_admin_registered(self):
        from django.contrib.admin.sites import site
        self.assertIn(TournamentHostingFeePayment, site._registry)

    def test_hosting_config_admin_registered(self):
        from django.contrib.admin.sites import site
        self.assertIn(TournamentHostingConfig, site._registry)

    def test_admin_list_page_accessible(self):
        superuser = User.objects.create_superuser(
            username=f"sadmin{uuid.uuid4().hex[:4]}", email=_test_email("sadmin"), password="x"
        )
        c = Client()
        c.force_login(superuser)
        resp = c.get("/admin/tournaments/tournamenthostingfeepayment/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_mark_verified_action(self):
        superuser = User.objects.create_superuser(
            username=f"sadmin2{uuid.uuid4().hex[:4]}", email=_test_email("sadmin2"), password="x"
        )
        user = User.objects.create_user(
            username=f"feeact{uuid.uuid4().hex[:4]}",
            email=_test_email("feeact"),
            password="x",
        )
        rec = TournamentHostingFeePayment.objects.create(
            user=user,
            amount_dc=0,
            status="waived",
            idempotency_key=f"admin-act-{uuid.uuid4().hex}",
        )
        c = Client()
        c.force_login(superuser)
        resp = c.post(
            "/admin/tournaments/tournamenthostingfeepayment/",
            {
                "action": "action_mark_verified",
                "_selected_action": [rec.pk],
            },
        )
        # Should redirect (302) after action, not 403/404
        self.assertIn(resp.status_code, [200, 302])
        rec.refresh_from_db()
        self.assertIsNotNone(rec.verified_at)

    def test_admin_mark_disputed_action(self):
        superuser = User.objects.create_superuser(
            username=f"sadmin3{uuid.uuid4().hex[:4]}", email=_test_email("sadmin3"), password="x"
        )
        user = User.objects.create_user(
            username=f"feedisp{uuid.uuid4().hex[:4]}",
            email=_test_email("feedisp"),
            password="x",
        )
        rec = TournamentHostingFeePayment.objects.create(
            user=user,
            amount_dc=500,
            status="paid",
            idempotency_key=f"admin-disp-{uuid.uuid4().hex}",
        )
        c = Client()
        c.force_login(superuser)
        c.post(
            "/admin/tournaments/tournamenthostingfeepayment/",
            {
                "action": "action_mark_disputed",
                "_selected_action": [rec.pk],
            },
        )
        rec.refresh_from_db()
        self.assertEqual(rec.status, "disputed")


# ──────────────────────────────────────────────────────────────
# 8.  JS file quality
# ──────────────────────────────────────────────────────────────

class JSFileQualityTest(TestCase):

    def setUp(self):
        import pathlib
        self.js = pathlib.Path("static/js/tournament_create.js").read_text(encoding="utf-8")

    def test_no_alert_calls(self):
        self.assertNotIn("alert(", self.js)

    def test_csrf_from_dataset(self):
        self.assertIn("createApp.dataset.csrfToken", self.js)

    def test_banner_logo_input_handlers_present(self):
        """Create flow intentionally supports banner/logo uploads before launch."""
        self.assertIn("bannerInput", self.js)
        self.assertIn("logoInput", self.js)
        self.assertIn("new FormData", self.js)
        self.assertIn('fd.append("banner_image", bannerFile)', self.js)
        self.assertIn('fd.append("thumbnail_image", logoFile)', self.js)

    def test_show_error_defined(self):
        self.assertIn("function showError", self.js)

    def test_proceed_launch_bound(self):
        self.assertIn("proceedLaunchButtons", self.js)
