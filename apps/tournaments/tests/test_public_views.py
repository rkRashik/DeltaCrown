"""
Tests for public tournament views (browse and detail pages).

Ensures public views use correct template paths after frontend reorganization.
"""

import json

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.models import Tournament, Game, TournamentAnnouncement

User = get_user_model()


@pytest.fixture
def game(db):
    """Create a test game."""
    return Game.objects.create(
        name='Test Game',
        slug='test-game',
        default_team_size=5,
        profile_id_field='riot_id',
        default_result_type='map_score'
    )


@pytest.fixture
def published_tournament(db, game):
    """Create a published tournament."""
    organizer = User.objects.create_user(
        username='organizer',
        email='organizer@example.com',
        password='testpass123'
    )
    
    return Tournament.objects.create(
        name='Public Tournament',
        slug='public-tournament',
        description='Public description',
        organizer=organizer,
        game=game,
        format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.TEAM,
        max_participants=16,
        min_participants=4,
        registration_start=timezone.now(),
        registration_end=timezone.now() + timedelta(days=7),
        tournament_start=timezone.now() + timedelta(days=14),
        status=Tournament.REGISTRATION_OPEN,
        published_at=timezone.now()
    )


@pytest.mark.django_db
class TestTournamentListView:
    """Test public tournament list/browse page."""
    
    def test_list_view_uses_public_template(self, client, published_tournament):
        """Tournament list should use public/browse template."""
        url = reverse('tournaments:list')
        response = client.get(url)
        
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert 'tournaments/list.html' in template_names
    
    def test_list_view_shows_published_tournaments(self, client, published_tournament):
        """List view should display published tournaments."""
        url = reverse('tournaments:list')
        response = client.get(url)
        
        assert response.status_code == 200
        assert published_tournament in response.context['tournament_list']
    
    def test_list_view_filters_by_game(self, client, published_tournament, game):
        """List view should filter tournaments by game."""
        url = reverse('tournaments:list') + f'?game={game.slug}'
        response = client.get(url)
        
        assert response.status_code == 200
        tournaments = list(response.context['tournament_list'])
        assert all(t.game == game for t in tournaments)


@pytest.mark.django_db
class TestTournamentDetailView:
    """Test public tournament detail page."""
    
    def test_detail_view_uses_public_template(self, client, published_tournament):
        """Tournament detail should use public/detail template."""
        url = reverse('tournaments:detail', kwargs={'slug': published_tournament.slug})
        response = client.get(url)
        
        assert response.status_code == 200
        template_names = [t.name for t in response.templates]
        assert 'tournaments/detailPages/detail.html' in template_names
    
    def test_detail_view_shows_tournament_info(self, client, published_tournament):
        """Detail view should show tournament information."""
        url = reverse('tournaments:detail', kwargs={'slug': published_tournament.slug})
        response = client.get(url)
        
        assert response.status_code == 200
        assert response.context['tournament'] == published_tournament
        assert 'can_register' in response.context
        assert 'registration_action_url' in response.context
        assert 'registration_action_label' in response.context
        assert 'slots_filled' in response.context
    
    def test_detail_view_shows_registration_cta(self, client, published_tournament):
        """Detail view should show registration CTA with proper state."""
        url = reverse('tournaments:detail', kwargs={'slug': published_tournament.slug})
        response = client.get(url)
        
        assert response.status_code == 200
        # Anonymous users should receive not_authenticated eligibility state
        assert response.context['eligibility_status'] == 'not_authenticated'
        assert response.context['can_register'] is False

    def test_detail_view_renders_tournament_announcements(self, client, published_tournament):
        """Detail page should render TournamentAnnouncement rows without lobby-only fields."""
        TournamentAnnouncement.objects.create(
            tournament=published_tournament,
            title='Matches Starting Soon',
            message='Please check in before the countdown ends.',
            created_by=published_tournament.organizer,
            is_pinned=True,
            is_important=True,
        )

        url = reverse('tournaments:detail', kwargs={'slug': published_tournament.slug})
        response = client.get(url)

        assert response.status_code == 200
        assert b'Matches Starting Soon' in response.content


@pytest.mark.django_db
class TestTournamentDetailWidgets:
    """Test backend-persisted detail widget flows."""

    def test_detail_context_includes_widget_payload(self, client, published_tournament):
        url = reverse('tournaments:detail', kwargs={'slug': published_tournament.slug})
        response = client.get(url)

        assert response.status_code == 200
        assert 'detail_widgets' in response.context
        assert isinstance(response.context['detail_widgets'], dict)
        assert 'sponsor' in response.context['detail_widgets']
        assert 'bottom_board' in response.context['detail_widgets']

    def test_organizer_can_save_widgets_and_persist_to_config(self, client, published_tournament):
        client.force_login(published_tournament.organizer)
        url = reverse('tournaments:detail_widgets_save', kwargs={'slug': published_tournament.slug})

        payload = {
            'detail_widgets': {
                'sponsor': {
                    'enabled': True,
                    'title': 'SteelSeries Arena',
                    'subtitle': 'Official gear partner',
                    'badge': 'SS',
                    'logo_url': 'https://example.com/ss.png',
                },
                'talent': {
                    'enabled': True,
                    'items': [
                        {
                            'name': 'Caster Nova',
                            'role': 'CAST',
                            'avatar_url': 'https://example.com/caster.png',
                        }
                    ],
                },
                'bounty': {
                    'enabled': True,
                    'title': 'Clutch Hunter',
                    'task': 'Win the most 1v2 rounds.',
                    'reward': 4200,
                },
                'poll': {
                    'enabled': True,
                    'active': True,
                    'question': 'Which team wins?',
                    'options': [
                        {'name': 'Alpha', 'percent': 60},
                        {'name': 'Bravo', 'percent': 40},
                    ],
                },
                'socials': {
                    'enabled': True,
                    'discord': 'https://discord.gg/example',
                    'facebook': 'https://facebook.com/example',
                    'youtube': 'https://youtube.com/@example',
                },
                'bottom_board': {
                    'enabled': True,
                    'title': 'Partners',
                    'banner_url': 'https://example.com/banner.png',
                    'logos': ['ACME', 'ZEN'],
                },
            }
        }

        response = client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        assert response.status_code == 200
        body = response.json()
        assert body.get('success') is True
        assert body['detail_widgets']['sponsor']['title'] == 'SteelSeries Arena'
        assert body['detail_widgets']['talent']['items'][0]['name'] == 'Caster Nova'
        assert body['detail_widgets']['bounty']['title'] == 'Clutch Hunter'
        assert body['detail_widgets']['poll']['question'] == 'Which team wins?'
        assert body['detail_widgets']['socials']['discord'] == 'https://discord.gg/example'
        assert body['detail_widgets']['bottom_board']['logos'] == ['ACME', 'ZEN']

        published_tournament.refresh_from_db()
        assert 'detail_widgets' in (published_tournament.config or {})
        assert published_tournament.config['detail_widgets']['talent']['items'][0]['name'] == 'Caster Nova'
        assert published_tournament.config['detail_widgets']['bounty']['reward'] == 4200
        assert published_tournament.config['detail_widgets']['poll']['question'] == 'Which team wins?'
        assert published_tournament.config['detail_widgets']['socials']['facebook'] == 'https://facebook.com/example'
        assert published_tournament.config['detail_widgets']['bottom_board']['title'] == 'Partners'

        detail_response = client.get(reverse('tournaments:detail', kwargs={'slug': published_tournament.slug}))
        assert detail_response.status_code == 200
        assert detail_response.context['detail_widgets']['sponsor']['title'] == 'SteelSeries Arena'
        assert detail_response.context['detail_widgets']['talent']['items'][0]['name'] == 'Caster Nova'
        assert detail_response.context['detail_widgets']['bounty']['reward'] == 4200
        assert detail_response.context['detail_widgets']['poll']['question'] == 'Which team wins?'
        assert detail_response.context['detail_widgets']['socials']['youtube'] == 'https://youtube.com/@example'
        assert detail_response.context['detail_widgets']['bottom_board']['title'] == 'Partners'

    def test_non_organizer_cannot_save_widgets(self, client, published_tournament):
        non_organizer = User.objects.create_user(
            username='random-user',
            email='random@example.com',
            password='testpass123',
        )
        client.force_login(non_organizer)

        url = reverse('tournaments:detail_widgets_save', kwargs={'slug': published_tournament.slug})
        response = client.post(
            url,
            data=json.dumps({'detail_widgets': {'sponsor': {'title': 'Should Fail'}}}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        assert response.status_code == 403
        body = response.json()
        assert body.get('success') is False

    def test_detail_page_exposes_widget_save_url_and_feedback_hooks(self, client, published_tournament):
        detail_url = reverse('tournaments:detail', kwargs={'slug': published_tournament.slug})
        save_url = reverse('tournaments:detail_widgets_save', kwargs={'slug': published_tournament.slug})

        response = client.get(detail_url)

        assert response.status_code == 200
        assert response.context['detail_widgets_save_url'] == save_url
        assert response.context['can_manage_detail_widgets'] is False

        html = response.content.decode('utf-8')
        assert f'data-widget-save-url="{save_url}"' in html
        assert 'fetch(this.widgetSaveUrl' in html
        assert 'widgetSaveError' in html
        assert 'widgetSaveSuccess' in html

    def test_detail_page_renders_backend_seeded_widget_values_after_reload(self, client, published_tournament):
        published_tournament.config = {
            'detail_widgets': {
                'sponsor': {
                    'enabled': True,
                    'title': 'Seeded Sponsor Title',
                    'subtitle': 'Loaded from backend config',
                    'badge': 'SSD',
                    'logo_url': 'https://example.com/seeded-logo.png',
                }
            }
        }
        published_tournament.save(update_fields=['config'])

        response = client.get(reverse('tournaments:detail', kwargs={'slug': published_tournament.slug}))

        assert response.status_code == 200
        assert 'detail_widgets' in response.context
        assert response.context['detail_widgets']['sponsor']['title'] == 'Seeded Sponsor Title'

        html = response.content.decode('utf-8')
        assert 'dc-detail-widget-seed' in html
        assert 'Seeded Sponsor Title' in html

    def test_canonical_widget_edit_permission_for_organizer(self, client, published_tournament):
        anonymous_response = client.get(reverse('tournaments:detail', kwargs={'slug': published_tournament.slug}))
        assert anonymous_response.status_code == 200
        assert anonymous_response.context['can_manage_detail_widgets'] is False

        client.force_login(published_tournament.organizer)
        organizer_response = client.get(reverse('tournaments:detail', kwargs={'slug': published_tournament.slug}))
        assert organizer_response.status_code == 200
        assert organizer_response.context['can_manage_detail_widgets'] is True

    def test_canonical_widget_edit_permission_for_staff_and_superuser(self, client, published_tournament):
        staff_user = User.objects.create_user(
            username='staff-manager',
            email='staff@example.com',
            password='testpass123',
        )
        staff_group, _ = Group.objects.get_or_create(name='Support Staff')
        staff_user.groups.add(staff_group)
        staff_user.refresh_from_db()

        super_user = User.objects.create_superuser(
            username='super-manager',
            email='super@example.com',
            password='testpass123',
        )

        detail_url = reverse('tournaments:detail', kwargs={'slug': published_tournament.slug})

        client.force_login(staff_user)
        staff_response = client.get(detail_url)
        assert staff_response.status_code == 200
        assert staff_response.context['can_manage_detail_widgets'] is True

        client.force_login(super_user)
        super_response = client.get(detail_url)
        assert super_response.status_code == 200
        assert super_response.context['can_manage_detail_widgets'] is True

    def test_detail_page_sets_csrf_cookie_for_widget_save(self, client, published_tournament):
        client.force_login(published_tournament.organizer)
        detail_url = reverse('tournaments:detail', kwargs={'slug': published_tournament.slug})

        response = client.get(detail_url)

        assert response.status_code == 200
        assert 'csrftoken' in response.cookies
        assert response.cookies['csrftoken'].value

    def test_widget_save_requires_and_accepts_csrf_token(self, published_tournament):
        secure_client = Client(enforce_csrf_checks=True)
        secure_client.force_login(published_tournament.organizer)

        detail_url = reverse('tournaments:detail', kwargs={'slug': published_tournament.slug})
        save_url = reverse('tournaments:detail_widgets_save', kwargs={'slug': published_tournament.slug})

        detail_response = secure_client.get(detail_url)
        csrf_token = detail_response.cookies['csrftoken'].value

        payload = {
            'detail_widgets': {
                'sponsor': {
                    'enabled': True,
                    'title': 'Secure Save Sponsor',
                    'subtitle': 'CSRF validated',
                    'badge': 'SEC',
                    'logo_url': 'https://example.com/secure.png',
                }
            }
        }

        missing_token_response = secure_client.post(
            save_url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert missing_token_response.status_code == 403

        ok_response = secure_client.post(
            save_url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert ok_response.status_code == 200
        ok_body = ok_response.json()
        assert ok_body.get('success') is True
        assert ok_body['detail_widgets']['sponsor']['title'] == 'Secure Save Sponsor'

    def test_official_tournament_uses_vanguard_default_socials_when_missing(self, client, published_tournament):
        published_tournament.is_official = True
        published_tournament.social_discord = ''
        published_tournament.social_facebook = ''
        published_tournament.social_youtube = ''
        published_tournament.social_instagram = ''
        published_tournament.save(
            update_fields=['is_official', 'social_discord', 'social_facebook', 'social_youtube', 'social_instagram']
        )

        response = client.get(reverse('tournaments:detail', kwargs={'slug': published_tournament.slug}))

        assert response.status_code == 200
        socials = response.context['detail_widgets']['socials']
        assert socials['enabled'] is True
        assert socials['discord'] == 'https://discord.gg/UaHRC8Cd'
        assert socials['facebook'] == 'https://www.facebook.com/DeltaCrownGG'
        assert socials['youtube'] == 'https://www.youtube.com/@DeltaCrownGG'
        assert socials['instagram'] == 'https://instagram.com/deltacrowngg'

    def test_authenticated_user_can_vote_on_fan_prediction_question(self, client, published_tournament):
        voter = User.objects.create_user(
            username='poll-voter',
            email='poll-voter@example.com',
            password='testpass123',
        )
        client.force_login(voter)

        published_tournament.enable_fan_voting = True
        published_tournament.config = {
            'detail_widgets': {
                'poll': {
                    'enabled': True,
                    'active': True,
                    'questions': [
                        {
                            'id': 'grand-final-winner',
                            'question': 'Who wins the grand final?',
                            'options': [
                                {'id': 'alpha', 'name': 'Team Alpha'},
                                {'id': 'bravo', 'name': 'Team Bravo'},
                            ],
                        }
                    ],
                }
            }
        }
        published_tournament.save(update_fields=['enable_fan_voting', 'config'])

        vote_url = reverse('tournaments:fan_prediction_vote', kwargs={'slug': published_tournament.slug})

        first_response = client.post(
            vote_url,
            data=json.dumps({'poll_id': 'grand-final-winner', 'option_id': 'alpha'}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert first_response.status_code == 200
        first_body = first_response.json()
        assert first_body.get('success') is True
        assert first_body['poll']['id'] == 'grand-final-winner'
        assert first_body['poll']['user_choice_id'] == 'alpha'

        alpha_option = next(opt for opt in first_body['poll']['options'] if opt['id'] == 'alpha')
        bravo_option = next(opt for opt in first_body['poll']['options'] if opt['id'] == 'bravo')
        assert alpha_option['votes'] == 1
        assert bravo_option['votes'] == 0

        second_response = client.post(
            vote_url,
            data=json.dumps({'poll_id': 'grand-final-winner', 'option_id': 'bravo'}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert second_response.status_code == 200
        second_body = second_response.json()
        assert second_body.get('success') is True
        assert second_body['poll']['user_choice_id'] == 'bravo'

        alpha_option_after = next(opt for opt in second_body['poll']['options'] if opt['id'] == 'alpha')
        bravo_option_after = next(opt for opt in second_body['poll']['options'] if opt['id'] == 'bravo')
        assert alpha_option_after['votes'] == 0
        assert bravo_option_after['votes'] == 1

    def test_fan_prediction_vote_requires_login(self, client, published_tournament):
        vote_url = reverse('tournaments:fan_prediction_vote', kwargs={'slug': published_tournament.slug})
        response = client.post(
            vote_url,
            data=json.dumps({'poll_id': 'poll-1', 'option_id': 'option-a'}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        assert response.status_code == 302
