"""
Test Live Feed widget on profile page.

Regression test for Phase 2B.3: Live Feed wiring.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


@pytest.mark.django_db
class TestProfileLiveFeed:
    """Test Live Feed widget shows correct state based on tournament matches."""
    
    def test_live_feed_empty_state_when_no_matches(self, client, user):
        """Verify Live Feed shows empty state when user has no live matches."""
        client.force_login(user)
        
        response = client.get(f'/@{user.username}/')
        assert response.status_code == 200
        
        content = response.content.decode('utf-8')
        
        # Should show empty state
        assert 'No live events' in content or 'Check back during tournaments' in content
        assert 'fa-satellite-dish' in content  # Empty state icon
    
    def test_live_feed_shows_live_match(self, client, user, live_tournament_match):
        """Verify Live Feed shows LIVE state when user has active match."""
        client.force_login(user)
        
        response = client.get(f'/@{user.username}/')
        assert response.status_code == 200
        
        content = response.content.decode('utf-8')
        
        # Should show live state
        assert 'Live Feed' in content
        assert 'animate-pulse' in content  # Pulse animation for live indicator
        
        # Should show tournament name
        assert live_tournament_match.tournament.name in content
        
        # Should show match info
        assert f'Round {live_tournament_match.round_number}' in content
    
    def test_live_feed_shows_opponent_name(self, client, user, live_tournament_match_with_opponent):
        """Verify Live Feed shows opponent name in subtitle."""
        client.force_login(user)
        
        response = client.get(f'/@{user.username}/')
        assert response.status_code == 200
        
        content = response.content.decode('utf-8')
        
        # Should show opponent name
        assert 'OpponentUser' in content or 'vs' in content
    
    def test_live_feed_shows_watch_match_button(self, client, user, live_tournament_match):
        """Verify Live Feed shows Watch Match button with correct URL."""
        client.force_login(user)
        
        response = client.get(f'/@{user.username}/')
        assert response.status_code == 200
        
        content = response.content.decode('utf-8')
        
        # Should have match detail URL
        assert f'/tournaments/{live_tournament_match.tournament.slug}/matches/{live_tournament_match.id}/' in content
        
        # Should have CTA button
        assert 'Watch Match' in content or 'View Match' in content
    
    def test_live_feed_shows_stream_button_when_available(self, client, user, live_tournament_match_with_stream):
        """Verify Live Feed shows Watch Stream button when stream_url is present."""
        client.force_login(user)
        
        response = client.get(f'/@{user.username}/')
        assert response.status_code == 200
        
        content = response.content.decode('utf-8')
        
        # Should have stream URL
        assert 'https://twitch.tv/test_stream' in content
        
        # Should have stream button
        assert 'Watch Stream' in content
    
    def test_live_feed_ignores_non_live_matches(self, client, user, completed_tournament_match):
        """Verify Live Feed ignores matches that are not in LIVE state."""
        client.force_login(user)
        
        response = client.get(f'/@{user.username}/')
        assert response.status_code == 200
        
        content = response.content.decode('utf-8')
        
        # Should show empty state, not completed match
        assert 'No live events' in content
        assert completed_tournament_match.tournament.name not in content
    
    def test_live_feed_visible_to_visitors(self, client, user, other_user, live_tournament_match):
        """Verify Live Feed is visible to profile visitors."""
        client.force_login(other_user)
        
        response = client.get(f'/@{user.username}/')
        assert response.status_code == 200
        
        content = response.content.decode('utf-8')
        
        # Visitor should see live match info
        assert live_tournament_match.tournament.name in content
        assert 'Live Feed' in content
    
    def test_live_feed_context_structure(self, user, live_tournament_match):
        """Verify live_feed context has correct structure."""
        from apps.user_profile.services.profile_context import build_profile_context
        
        context = build_profile_context(user, user)
        
        # Should have live_feed key
        assert 'live_feed' in context
        
        live_feed = context['live_feed']
        
        # Should have required keys
        assert 'is_live' in live_feed
        assert 'title' in live_feed
        assert 'subtitle' in live_feed
        assert 'cta_label' in live_feed
        assert 'cta_url' in live_feed
        
        # Should be in live state
        assert live_feed['is_live'] is True
        assert live_feed['title'] == live_tournament_match.tournament.name
        assert f'Round {live_tournament_match.round_number}' in live_feed['subtitle']
        assert live_feed['cta_label'] == 'Watch Match'
        assert live_feed['cta_url'] is not None
    
    def test_live_feed_context_empty_state(self, user):
        """Verify live_feed context when no live matches."""
        from apps.user_profile.services.profile_context import build_profile_context
        
        context = build_profile_context(user, user)
        
        live_feed = context['live_feed']
        
        # Should be in empty state
        assert live_feed['is_live'] is False
        assert 'No live events' in live_feed['title']
        assert live_feed['cta_label'] is None
        assert live_feed['cta_url'] is None


# Fixtures
@pytest.fixture
def user():
    """Create test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
    )


@pytest.fixture
def other_user():
    """Create another test user."""
    return User.objects.create_user(
        username='visitor',
        email='visitor@example.com',
        password='testpass123',
    )


@pytest.fixture
def client():
    """Create Django test client."""
    return Client()


@pytest.fixture
def tournament(user):
    """Create test tournament."""
    from apps.tournaments.models import Tournament, Game
    
    # Create game first
    game, _ = Game.objects.get_or_create(
        name='Test Game',
        defaults={
            'slug': 'test-game',
            'profile_id_field': 'test_id',
        }
    )
    
    return Tournament.objects.create(
        name='Test Tournament 2025',
        slug='test-tournament-2025',
        organizer=user,
        game=game,
        status=Tournament.LIVE,
        format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.SOLO,
        start_date=timezone.now(),
    )


@pytest.fixture
def live_tournament_match(user, tournament):
    """Create live tournament match with user as participant."""
    from apps.tournaments.models import Match as TournamentMatch, Bracket
    
    # Create bracket
    bracket = Bracket.objects.create(
        tournament=tournament,
        name='Main Bracket',
        format='single_elimination',
    )
    
    return TournamentMatch.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=2,
        match_number=1,
        participant1_id=user.id,
        participant1_name=user.username,
        participant2_id=999,
        participant2_name='Opponent',
        state=TournamentMatch.LIVE,
        scheduled_time=timezone.now(),
    )


@pytest.fixture
def live_tournament_match_with_opponent(user, tournament):
    """Create live match with named opponent."""
    from apps.tournaments.models import Match as TournamentMatch, Bracket
    
    bracket = Bracket.objects.create(
        tournament=tournament,
        name='Main Bracket',
        format='single_elimination',
    )
    
    return TournamentMatch.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=1,
        participant1_id=user.id,
        participant1_name=user.username,
        participant2_id=888,
        participant2_name='OpponentUser',
        state=TournamentMatch.LIVE,
        scheduled_time=timezone.now(),
    )


@pytest.fixture
def live_tournament_match_with_stream(user, tournament):
    """Create live match with stream URL."""
    from apps.tournaments.models import Match as TournamentMatch, Bracket
    
    bracket = Bracket.objects.create(
        tournament=tournament,
        name='Main Bracket',
        format='single_elimination',
    )
    
    return TournamentMatch.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=3,
        match_number=1,
        participant1_id=user.id,
        participant1_name=user.username,
        participant2_id=777,
        participant2_name='StreamOpponent',
        state=TournamentMatch.LIVE,
        stream_url='https://twitch.tv/test_stream',
        scheduled_time=timezone.now(),
    )


@pytest.fixture
def completed_tournament_match(user, tournament):
    """Create completed (non-live) tournament match."""
    from apps.tournaments.models import Match as TournamentMatch, Bracket
    
    bracket = Bracket.objects.create(
        tournament=tournament,
        name='Main Bracket',
        format='single_elimination',
    )
    
    return TournamentMatch.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=2,
        participant1_id=user.id,
        participant1_name=user.username,
        participant2_id=666,
        participant2_name='PastOpponent',
        state=TournamentMatch.COMPLETED,
        winner_id=user.id,
        completed_at=timezone.now() - timedelta(hours=2),
    )
