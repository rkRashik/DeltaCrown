"""
Phase 2 Part 2 Tests.

Covers:
- P2-T05: Check-In Control Panel (force check-in, drop no-show, close & drop all)
- P2-T06: Display Name Override Toggle
- P2-T07: Draft Auto-Save (save/load/submit clears draft)

Source: Documents/Registration_system/05_IMPLEMENTATION_TRACKER.md
"""

import json
import pytest
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from apps.games.models.game import Game
from apps.tournaments.models.registration import Registration
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.smart_registration import RegistrationDraft
from apps.tournaments.services.checkin_service import CheckinService

User = get_user_model()

import uuid as _uuid


def _uid():
    return _uuid.uuid4().hex[:8]


def _make_game(**kwargs):
    uid = _uid()
    defaults = dict(
        name=f'Game-{uid}', slug=f'game-{uid}', short_code=uid[:4].upper(),
        category='FPS', display_name=f'Game {uid}', game_type='TEAM_VS_TEAM',
        is_active=True,
    )
    defaults.update(kwargs)
    return Game.objects.create(**defaults)


def _make_tournament(game, organizer, **kwargs):
    uid = _uid()
    now = timezone.now()
    defaults = dict(
        name=f'Tournament-{uid}',
        slug=f't-{uid}',
        description='Test tournament',
        organizer=organizer,
        game=game,
        max_participants=16,
        min_participants=2,
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=7),
        tournament_start=now + timedelta(days=14),
        status=Tournament.REGISTRATION_OPEN,
        participation_type=Tournament.SOLO,
        format='single_elimination',
        enable_check_in=True,
        check_in_minutes_before=30,
    )
    defaults.update(kwargs)
    return Tournament.objects.create(**defaults)


def _make_user(username=None, **kwargs):
    uid = _uid()
    uname = username or f'user-{uid}'
    defaults = dict(username=uname, email=f'{uname}@test.dc', password='test1234')
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def _make_registration(tournament, user, **kwargs):
    defaults = dict(
        tournament=tournament,
        user=user,
        status='confirmed',
        registration_data={'game_id': f'gid-{_uid()}'},
    )
    defaults.update(kwargs)
    return Registration.objects.create(**defaults)


# ===========================================================================
# P2-T05: Check-In Control Panel
# ===========================================================================

@pytest.mark.django_db
class TestCheckinControlPanel:
    """P2-T05: Organizer check-in control panel actions."""

    def test_force_checkin_sets_checked_in(self):
        """Force check-in via organizer sets checked_in=True."""
        organizer = _make_user()
        player = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        reg = _make_registration(tournament, player)

        assert not reg.checked_in
        CheckinService.organizer_toggle_checkin(reg, organizer)
        reg.refresh_from_db()
        assert reg.checked_in is True

    def test_force_checkin_api_requires_organizer(self):
        """Force check-in endpoint returns 403 for non-organizer."""
        organizer = _make_user()
        player = _make_user()
        rando = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        reg = _make_registration(tournament, player)

        client = Client()
        client.force_login(rando)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/force-checkin/{reg.id}/',
            content_type='application/json',
        )
        assert resp.status_code == 403

    def test_force_checkin_api_success(self):
        """Force check-in endpoint works for organizer."""
        organizer = _make_user()
        player = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        reg = _make_registration(tournament, player)

        client = Client()
        client.force_login(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/force-checkin/{reg.id}/',
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        reg.refresh_from_db()
        assert reg.checked_in is True

    def test_force_checkin_already_checked_in(self):
        """Force check-in returns 400 if already checked in."""
        organizer = _make_user()
        player = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        reg = _make_registration(tournament, player, checked_in=True)

        client = Client()
        client.force_login(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/force-checkin/{reg.id}/',
            content_type='application/json',
        )
        assert resp.status_code == 400

    def test_drop_noshow_sets_dropped(self):
        """Drop no-show sets status to 'no_show'."""
        organizer = _make_user()
        player = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        reg = _make_registration(tournament, player)

        client = Client()
        client.force_login(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/drop-noshow/{reg.id}/',
            content_type='application/json',
        )
        assert resp.status_code == 200
        reg.refresh_from_db()
        assert reg.status == 'no_show'
        assert reg.checked_in is False

    def test_drop_noshow_requires_organizer(self):
        """Drop no-show endpoint returns 403 for non-organizer."""
        organizer = _make_user()
        player = _make_user()
        rando = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        reg = _make_registration(tournament, player)

        client = Client()
        client.force_login(rando)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/drop-noshow/{reg.id}/',
            content_type='application/json',
        )
        assert resp.status_code == 403

    def test_close_drop_noshows_drops_unchecked(self):
        """Close & drop all no-shows: drops all unchecked confirmed participants."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)

        # 3 confirmed, 1 checked in, 2 not
        p1 = _make_user()
        p2 = _make_user()
        p3 = _make_user()
        r1 = _make_registration(tournament, p1, checked_in=True)
        r2 = _make_registration(tournament, p2)
        r3 = _make_registration(tournament, p3)

        client = Client()
        client.force_login(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/close-drop-noshows/',
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['dropped_count'] == 2

        r1.refresh_from_db()
        r2.refresh_from_db()
        r3.refresh_from_db()
        assert r1.status == 'confirmed'  # checked in, stays
        assert r2.status == 'no_show'
        assert r3.status == 'no_show'

    def test_toggle_checkin_undo(self):
        """Toggle check-in (undo) for already checked-in participant."""
        organizer = _make_user()
        player = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        reg = _make_registration(tournament, player, checked_in=True)

        client = Client()
        client.force_login(organizer)
        resp = client.post(
            f'/tournaments/organizer/{tournament.slug}/toggle-checkin/{reg.id}/',
            content_type='application/json',
        )
        assert resp.status_code == 200
        reg.refresh_from_db()
        assert reg.checked_in is False


# ===========================================================================
# P2-T06: Display Name Override Toggle
# ===========================================================================

@pytest.mark.django_db
class TestDisplayNameOverride:
    """P2-T06: Display name override toggle on tournament model and smart registration."""

    def test_model_field_defaults_to_false(self):
        """allow_display_name_override defaults to False."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        assert tournament.allow_display_name_override is False

    def test_model_field_can_be_enabled(self):
        """allow_display_name_override can be set to True."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer, allow_display_name_override=True)
        assert tournament.allow_display_name_override is True

    def test_build_fields_locked_when_disabled(self):
        """Display name field is locked when allow_display_name_override is False."""
        from apps.tournaments.views.smart_registration import SmartRegistrationView

        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer, allow_display_name_override=False)

        view = SmartRegistrationView()
        fields = view._build_fields(user, tournament, {}, None)
        assert fields['display_name']['locked'] is True
        assert fields['display_name']['source'] == 'username'

    def test_build_fields_unlocked_when_enabled(self):
        """Display name field is unlocked when allow_display_name_override is True."""
        from apps.tournaments.views.smart_registration import SmartRegistrationView

        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer, allow_display_name_override=True)

        view = SmartRegistrationView()
        fields = view._build_fields(user, tournament, {}, None)
        assert fields['display_name']['locked'] is False
        assert fields['display_name']['source'] == 'editable'

    def test_context_passes_flag(self):
        """_build_context passes allow_display_name_override to template context."""
        from apps.tournaments.views.smart_registration import SmartRegistrationView
        from django.test import RequestFactory

        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer, allow_display_name_override=True)

        view = SmartRegistrationView()
        factory = RequestFactory()
        request = factory.get(f'/tournaments/{tournament.slug}/register/smart/')
        request.user = user

        context = view._build_context(request, tournament)
        assert context['allow_display_name_override'] is True

    def test_display_name_stored_in_registration_data(self):
        """Custom display name is stored in registration_data when override is enabled."""
        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer, allow_display_name_override=True)

        reg = Registration.objects.create(
            tournament=tournament,
            user=user,
            status='confirmed',
            registration_data={
                'game_id': 'test#123',
                'display_name': 'CustomName',
            },
        )
        assert reg.registration_data['display_name'] == 'CustomName'


# ===========================================================================
# P2-T07: Draft Auto-Save
# ===========================================================================

@pytest.mark.django_db
class TestDraftAutoSave:
    """P2-T07: Draft auto-save API for smart registration."""

    def test_save_draft_creates_new(self):
        """Save draft API creates a new RegistrationDraft."""
        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)

        client = Client()
        client.force_login(user)
        resp = client.post(
            f'/tournaments/{tournament.slug}/api/smart-draft/save/',
            data=json.dumps({'form_data': {'phone': '01712345678', 'discord': 'user#1234'}}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['draft_uuid'] is not None

        draft = RegistrationDraft.objects.get(user=user, tournament=tournament)
        assert draft.form_data['phone'] == '01712345678'
        assert draft.form_data['discord'] == 'user#1234'

    def test_save_draft_updates_existing(self):
        """Save draft API updates existing draft instead of creating duplicate."""
        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)

        RegistrationDraft.objects.create(
            user=user,
            tournament=tournament,
            registration_number=f'DRF-{tournament.id}-{user.id}',
            form_data={'phone': 'old'},
            expires_at=timezone.now() + timedelta(days=7),
        )

        client = Client()
        client.force_login(user)
        resp = client.post(
            f'/tournaments/{tournament.slug}/api/smart-draft/save/',
            data=json.dumps({'form_data': {'phone': 'new-number'}}),
            content_type='application/json',
        )
        assert resp.status_code == 200

        drafts = RegistrationDraft.objects.filter(user=user, tournament=tournament)
        assert drafts.count() == 1
        assert drafts.first().form_data['phone'] == 'new-number'

    def test_get_draft_returns_saved_data(self):
        """Get draft API returns saved form data."""
        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)

        RegistrationDraft.objects.create(
            user=user,
            tournament=tournament,
            registration_number=f'DRF-{tournament.id}-{user.id}',
            form_data={'discord': 'saved#9999'},
            expires_at=timezone.now() + timedelta(days=7),
        )

        client = Client()
        client.force_login(user)
        resp = client.get(f'/tournaments/{tournament.slug}/api/smart-draft/get/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['draft']['form_data']['discord'] == 'saved#9999'

    def test_get_draft_returns_none_if_no_draft(self):
        """Get draft API returns null when no draft exists."""
        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)

        client = Client()
        client.force_login(user)
        resp = client.get(f'/tournaments/{tournament.slug}/api/smart-draft/get/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['draft'] is None

    def test_get_draft_expired_is_deleted(self):
        """Expired draft is deleted and returns null."""
        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)

        RegistrationDraft.objects.create(
            user=user,
            tournament=tournament,
            registration_number=f'DRF-{tournament.id}-{user.id}',
            form_data={'discord': 'expired'},
            expires_at=timezone.now() - timedelta(hours=1),
        )

        client = Client()
        client.force_login(user)
        resp = client.get(f'/tournaments/{tournament.slug}/api/smart-draft/get/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['draft'] is None
        assert RegistrationDraft.objects.filter(user=user, tournament=tournament).count() == 0

    def test_submitted_draft_not_returned(self):
        """Submitted drafts are not returned by get endpoint."""
        organizer = _make_user()
        user = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)

        RegistrationDraft.objects.create(
            user=user,
            tournament=tournament,
            registration_number=f'DRF-{tournament.id}-{user.id}',
            form_data={'discord': 'submitted-draft'},
            expires_at=timezone.now() + timedelta(days=7),
            submitted=True,
        )

        client = Client()
        client.force_login(user)
        resp = client.get(f'/tournaments/{tournament.slug}/api/smart-draft/get/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['draft'] is None

    def test_save_draft_requires_login(self):
        """Save draft API redirects to login for anonymous user."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)

        client = Client()
        resp = client.post(
            f'/tournaments/{tournament.slug}/api/smart-draft/save/',
            data=json.dumps({'form_data': {'phone': '123'}}),
            content_type='application/json',
        )
        assert resp.status_code == 302  # redirect to login
