# apps/tournaments/tests/conftest.py
"""
Test fixtures for tournament API tests.

Provides centralized fixtures for:
- Game creation (all 8 supported titles)
- Tournament factories (solo + team)
- User/profile management
"""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.tournaments.models import Game, Tournament


def _ensure_profile(user):
    """
    Create or fetch the UserProfile for the given user without
    importing project-specific helpers in production code.
    
    This is a test-only utility to unblock team registration tests
    that require UserProfile for Team.captain foreign key.
    """
    # Try common locations; adapt if your project uses a different path/name.
    try:
        from apps.user_profile.models import UserProfile
    except Exception:  # pragma: no cover
        try:
            from accounts.models import UserProfile
        except Exception:
            try:
                from users.models import UserProfile
            except Exception:
                raise RuntimeError("UserProfile model not found. Update import path.")

    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@pytest.fixture
def user_with_profile(db):
    """
    Create a user with associated UserProfile for team captain tests.
    Returns: (User, UserProfile) tuple
    """
    User = get_user_model()
    user = User.objects.create_user(
        username="captain_user",
        email="captain@example.com",
        password="pass1234",
    )
    profile = _ensure_profile(user)
    return user, profile


@pytest.fixture
def member_with_profile(db):
    """
    Create a user with associated UserProfile for team member tests.
    Returns: (User, UserProfile) tuple
    """
    User = get_user_model()
    user = User.objects.create_user(
        username="member_user",
        email="member@example.com",
        password="pass1234",
    )
    profile = _ensure_profile(user)
    return user, profile


# ========== Game Fixtures (8 Supported Titles) ==========

@pytest.fixture
def game_factory(db):
    """
    Factory to create Game instances.
    Usage: game_factory(slug='valorant', name='Valorant', team_size=5)
    """
    def _make(slug: str, name: str = None, team_size: int = 5, **kwargs):
        defaults = {
            'name': name or slug.replace('-', ' ').title(),
            'slug': slug,
            'default_team_size': team_size,
            'profile_id_field': kwargs.get('profile_id_field', 'riot_id'),
            'default_result_type': kwargs.get('default_result_type', 'map_score'),
            'is_active': kwargs.get('is_active', True),
        }
        defaults.update(kwargs)
        return Game.objects.create(**defaults)
    return _make


@pytest.fixture
def all_games(game_factory):
    """
    Create all 8 supported game titles per planning requirements.
    Returns: list of Game instances
    """
    games = [
        game_factory(slug='valorant', name='Valorant', team_size=5, profile_id_field='riot_id'),
        game_factory(slug='efootball', name='eFootball', team_size=1, profile_id_field='efootball_id'),
        game_factory(slug='pubgm', name='PUBG Mobile', team_size=4, profile_id_field='pubg_mobile_id'),
        game_factory(slug='fifa', name='FIFA', team_size=1, profile_id_field='ea_id'),
        game_factory(slug='apex', name='Apex Legends', team_size=3, profile_id_field='ea_id'),
        game_factory(slug='cod', name='Call of Duty Mobile', team_size=5, profile_id_field='cod_id'),
        game_factory(slug='cs2', name='Counter-Strike 2', team_size=5, profile_id_field='steam_id'),
        game_factory(slug='csgo', name='CS:GO', team_size=5, profile_id_field='steam_id'),
    ]
    return games


@pytest.fixture(params=[
    ('valorant', 5, 'riot_id'),
    ('efootball', 1, 'efootball_id'),
    ('pubgm', 4, 'pubg_mobile_id'),
    ('fifa', 1, 'ea_id'),
    ('apex', 3, 'ea_id'),
    ('cod', 5, 'cod_id'),
    ('cs2', 5, 'steam_id'),
    ('csgo', 5, 'steam_id'),
])
def game(request, game_factory):
    """
    Parametrized fixture providing each supported game.
    Use with @pytest.mark.parametrize or indirect=True.
    """
    slug, team_size, profile_field = request.param
    return game_factory(slug=slug, name=slug.upper(), team_size=team_size, profile_id_field=profile_field)


# ========== Tournament Fixtures ==========

@pytest.fixture
def tournament_factory(db):
    """
    Factory to create Tournament instances.
    Usage: tournament_factory(game=game_instance, participation_type='solo')
    """
    from apps.accounts.models import User
    
    def _make(game, participation_type: str = None, **kwargs):
        # Determine participation type from game if not provided
        if participation_type is None:
            participation_type = 'solo' if game.default_team_size == 1 else 'team'
        
        # Create organizer if not provided
        organizer = kwargs.pop('organizer', None)
        if not organizer:
            timestamp = int(timezone.now().timestamp() * 1000000)  # Microsecond precision
            organizer = User.objects.create_user(
                username=f'org_{game.slug}_{timestamp}',
                email=f'org_{game.slug}_{timestamp}@test.com',
                password='pass123'
            )
        
        # Map common kwargs to actual field names
        entry_fee = kwargs.pop('entry_fee', None)
        if entry_fee:
            kwargs['has_entry_fee'] = True
            kwargs['entry_fee_amount'] = Decimal(str(entry_fee))
        
        defaults = {
            'name': kwargs.get('name', f'{game.name} Tournament'),
            'slug': kwargs.get('slug', f'{game.slug}-cup-{int(timezone.now().timestamp() * 1000000)}'),
            'description': kwargs.get('description', f'Test tournament for {game.name}'),
            'game': game,
            'organizer': organizer,
            'format': kwargs.get('format', 'single_elimination'),
            'participation_type': participation_type,
            'min_participants': kwargs.get('min_participants', 4),
            'max_participants': kwargs.get('max_participants', 16),
            'prize_pool': kwargs.get('prize_pool', Decimal('1000.00')),
            'registration_start': kwargs.get('registration_start', timezone.now()),
            'registration_end': kwargs.get('registration_end', timezone.now() + timezone.timedelta(days=7)),
            'tournament_start': kwargs.get('tournament_start', timezone.now() + timezone.timedelta(days=10)),
            'status': kwargs.get('status', 'registration_open'),
        }
        defaults.update({k: v for k, v in kwargs.items() if k not in defaults})
        return Tournament.objects.create(**defaults)
    
    return _make


# ========== API Client Fixtures ==========

@pytest.fixture
def staff_user(db):
    """Staff user for API auth (conftest global version)."""
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    user = User.objects.create_superuser(
        username='staffer',
        email='staff@example.com',
        password='pass1234'
    )
    user.refresh_from_db()
    assert user.is_staff is True, f"Staff user creation failed: is_staff={user.is_staff}"
    assert user.is_superuser is True
    return user


@pytest.fixture
def staff_client(staff_user):
    """API client authenticated as staff user using session-backed force_login."""
    from rest_framework.test import APIClient
    
    client = APIClient()
    client.force_login(staff_user)  # Session-backed auth, not force_authenticate
    return client


@pytest.fixture
def participant_user(db):
    """Regular participant user."""
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    return User.objects.create_user(
        username='player1',
        email='p1@example.com',
        password='pass1234'
    )


@pytest.fixture
def participant_client(participant_user):
    """API client authenticated as regular user (participant)."""
    from rest_framework.test import APIClient
    
    client = APIClient()
    client.force_login(participant_user)  # Session-backed auth
    return client
