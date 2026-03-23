import pytest
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.games.models import Game
from apps.tournaments.models import DisputeRecord, HubSupportTicket, Match, MatchResultSubmission, Tournament


User = get_user_model()


@pytest.fixture
def organizer(db):
    return User.objects.create_user(
        username='toc_bridge_organizer',
        email='toc-bridge-organizer@test.local',
        password='pass1234',
    )


@pytest.fixture
def assignee(db):
    return User.objects.create_user(
        username='toc_bridge_assignee',
        email='toc-bridge-assignee@test.local',
        password='pass1234',
    )


@pytest.fixture
def organizer_client(organizer):
    client = APIClient()
    client.force_login(organizer)
    return client


@pytest.fixture
def game(db):
    return Game.objects.create(
        slug='toc-bridge-game',
        name='TOC Bridge Game',
        is_active=True,
        primary_color='#2563EB',
        secondary_color='#0EA5E9',
        accent_color='#22D3EE',
    )


@pytest.fixture
def tournament(db, organizer, game):
    now = timezone.now()
    return Tournament.objects.create(
        name='TOC Hub Bridge Tournament',
        slug='toc-hub-bridge-tournament',
        description='TOC hub bridge test tournament',
        organizer=organizer,
        game=game,
        format='single_elimination',
        participation_type='team',
        max_participants=16,
        min_participants=2,
        registration_start=now - timedelta(days=10),
        registration_end=now - timedelta(days=5),
        tournament_start=now - timedelta(days=1),
        status='live',
    )


@pytest.fixture
def match_dispute(db, tournament, organizer):
    match = Match.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=1,
        state=Match.PENDING_RESULT,
        participant1_id=11,
        participant1_name='Alpha',
        participant2_id=12,
        participant2_name='Bravo',
    )
    submission = MatchResultSubmission.objects.create(
        match=match,
        submitted_by_user=organizer,
        raw_result_payload={'winner_id': 11, 'score': '2-1'},
    )
    return DisputeRecord.objects.create(
        submission=submission,
        opened_by_user=organizer,
        opened_by_team_id=501,
        reason_code=DisputeRecord.REASON_SCORE_MISMATCH,
        description='Submitted score does not match opponent screenshot.',
    )


@pytest.fixture
def hub_ticket(db, tournament, organizer):
    return HubSupportTicket.objects.create(
        tournament=tournament,
        created_by=organizer,
        category=HubSupportTicket.CATEGORY_GENERAL,
        subject='Cannot report result from hub',
        message='Hub result form keeps timing out after submit button click.',
        status=HubSupportTicket.STATUS_OPEN,
        match_ref='Match #99',
    )


@pytest.mark.django_db
class TestTOCDisputesHubBridge:
    def test_disputes_list_returns_mixed_payload(self, organizer_client, tournament, match_dispute, hub_ticket):
        url = reverse('toc_api:disputes', kwargs={'slug': tournament.slug})
        response = organizer_client.get(url)
        assert response.status_code == 200

        payload = response.json()
        rows = payload.get('disputes', [])
        source_types = {row.get('source_type') for row in rows}

        assert 'match_dispute' in source_types
        assert 'hub_support' in source_types
        assert payload.get('open_count', 0) >= 2

        hub_rows = [row for row in rows if row.get('source_type') == 'hub_support']
        assert hub_rows
        assert hub_rows[0].get('opened_by_name') == tournament.organizer.username
        assert hub_rows[0].get('reason_display') in {
            'General Inquiry',
            'Match Dispute',
            'Technical Issue',
            'Payment / Prize',
        }

    def test_hub_ticket_detail_endpoint_returns_ticket(self, organizer_client, tournament, hub_ticket):
        url = reverse('toc_api:dispute-hub-ticket-detail', kwargs={'slug': tournament.slug, 'pk': hub_ticket.id})
        response = organizer_client.get(url)
        assert response.status_code == 200

        data = response.json()
        assert data.get('id') == hub_ticket.id
        assert data.get('source_type') == 'hub_support'
        assert data.get('opened_by_name') == tournament.organizer.username
        assert data.get('description') == hub_ticket.message

    def test_resolve_hub_ticket_via_disputes_action(self, organizer_client, tournament, hub_ticket):
        url = reverse('toc_api:dispute-resolve', kwargs={'slug': tournament.slug, 'pk': hub_ticket.id})
        response = organizer_client.post(
            url,
            {
                'source_type': 'hub_support',
                'ruling': 'submitter_wins',
                'resolution_notes': 'Issue verified and resolved by TOC staff.',
            },
            format='json',
        )
        assert response.status_code == 200

        hub_ticket.refresh_from_db()
        assert hub_ticket.status == HubSupportTicket.STATUS_RESOLVED
        assert hub_ticket.organizer_notes == 'Issue verified and resolved by TOC staff.'
        assert hub_ticket.resolved_by_id is not None
        assert hub_ticket.resolved_at is not None

    def test_escalate_and_assign_hub_ticket_via_disputes_actions(self, organizer_client, tournament, hub_ticket, assignee):
        escalate_url = reverse('toc_api:dispute-escalate', kwargs={'slug': tournament.slug, 'pk': hub_ticket.id})
        escalate_response = organizer_client.post(
            escalate_url,
            {
                'source_type': 'hub_support',
                'reason': 'Needs senior review due to repeated failures.',
            },
            format='json',
        )
        assert escalate_response.status_code == 200

        hub_ticket.refresh_from_db()
        assert hub_ticket.status == HubSupportTicket.STATUS_IN_REVIEW
        assert hub_ticket.organizer_notes.startswith('[ESCALATED] Needs senior review')

        assign_url = reverse('toc_api:dispute-assign', kwargs={'slug': tournament.slug, 'pk': hub_ticket.id})
        assign_response = organizer_client.post(
            assign_url,
            {
                'source_type': 'hub_support',
                'staff_user_id': assignee.id,
            },
            format='json',
        )
        assert assign_response.status_code == 200

        hub_ticket.refresh_from_db()
        assert hub_ticket.resolved_by_id == assignee.id

    def test_resolve_rejects_invalid_source_type(self, organizer_client, tournament, hub_ticket):
        url = reverse('toc_api:dispute-resolve', kwargs={'slug': tournament.slug, 'pk': hub_ticket.id})
        response = organizer_client.post(
            url,
            {
                'source_type': 'unknown_source',
                'ruling': 'submitter_wins',
            },
            format='json',
        )
        assert response.status_code == 400
        assert response.json().get('error') == 'invalid_source_type'

    def test_assign_rejects_invalid_staff_user_id(self, organizer_client, tournament, hub_ticket):
        url = reverse('toc_api:dispute-assign', kwargs={'slug': tournament.slug, 'pk': hub_ticket.id})
        response = organizer_client.post(
            url,
            {
                'source_type': 'hub_support',
                'staff_user_id': 'abc',
            },
            format='json',
        )
        assert response.status_code == 400
        assert response.json().get('error') == 'invalid_staff_user_id'

    def test_disputes_list_source_filter_match_only(self, organizer_client, tournament, match_dispute, hub_ticket):
        url = reverse('toc_api:disputes', kwargs={'slug': tournament.slug})
        response = organizer_client.get(url, {'source': 'match_dispute'})
        assert response.status_code == 200
        payload = response.json()
        rows = payload.get('disputes', [])
        assert rows
        assert all(row.get('source_type') == 'match_dispute' for row in rows)
        assert payload.get('open_count') == 1

    def test_disputes_list_source_filter_hub_only(self, organizer_client, tournament, match_dispute, hub_ticket):
        url = reverse('toc_api:disputes', kwargs={'slug': tournament.slug})
        response = organizer_client.get(url, {'source': 'hub_support'})
        assert response.status_code == 200
        payload = response.json()
        rows = payload.get('disputes', [])
        assert rows
        assert all(row.get('source_type') == 'hub_support' for row in rows)
        assert payload.get('open_count') == 1

    def test_disputes_list_rejects_invalid_source_filter(self, organizer_client, tournament):
        url = reverse('toc_api:disputes', kwargs={'slug': tournament.slug})
        response = organizer_client.get(url, {'source': 'unknown'})
        assert response.status_code == 400
        assert response.json().get('error') == 'invalid_source_filter'
