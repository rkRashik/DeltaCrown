"""
Factory fixtures for apps/organizations/ test suite.

Provides org_factory, player_factory, org_membership_factory,
team_factory, and authenticated_client for contract tests.
"""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

_factory_counter = 0


def _next_id():
    global _factory_counter
    _factory_counter += 1
    return _factory_counter


@pytest.fixture
def player_factory(db):
    """
    Factory that creates a User instance (tests use 'player' as alias for user).
    Returns an object with a `.user` attribute for compatibility with test code
    that does `player.user`.
    """
    created = []

    class _PlayerProxy:
        """Thin wrapper so tests can do player_factory(...).user"""
        def __init__(self, user):
            self.user = user
            # Forward common attrs
            self.pk = user.pk
            self.id = user.pk
            self.username = user.username

        def __eq__(self, other):
            if isinstance(other, _PlayerProxy):
                return self.user == other.user
            return NotImplemented

        def __hash__(self):
            return hash(self.user)

    def _create(**kwargs):
        uid = _next_id()
        defaults = {
            'username': f'player_{uid}',
            'email': f'player_{uid}@test.deltacrown.local',
        }
        defaults.update(kwargs)
        user = User.objects.create_user(**defaults)
        created.append(user)
        return _PlayerProxy(user)

    yield _create


@pytest.fixture
def org_factory(db, player_factory):
    """Factory that creates Organization instances."""
    created = []

    def _create(**kwargs):
        if 'ceo' not in kwargs:
            ceo_proxy = player_factory(username=f'ceo_{_next_id()}')
            kwargs['ceo'] = ceo_proxy.user
        elif hasattr(kwargs['ceo'], 'user'):
            # Unwrap PlayerProxy
            kwargs['ceo'] = kwargs['ceo'].user
        if 'name' not in kwargs:
            kwargs['name'] = f'Test Org {_next_id()}'
        from apps.organizations.models.organization import Organization
        org = Organization.objects.create(**kwargs)
        created.append(org)
        return org

    yield _create


@pytest.fixture
def org_membership_factory(db):
    """Factory that creates OrganizationMembership instances."""

    def _create(**kwargs):
        if 'player' in kwargs:
            player = kwargs.pop('player')
            kwargs['user'] = getattr(player, 'user', player)
        from apps.organizations.models.organization import OrganizationMembership
        return OrganizationMembership.objects.create(**kwargs)

    return _create


@pytest.fixture
def team_factory(db, org_factory):
    """Factory that creates Organization Team instances."""

    def _create(**kwargs):
        if 'organization' not in kwargs and 'organization_id' not in kwargs:
            kwargs['organization'] = org_factory()
        uid = _next_id()
        if 'name' not in kwargs:
            kwargs['name'] = f'Test Team {uid}'
        if 'region' not in kwargs:
            kwargs['region'] = 'BD'
        from apps.organizations.models.team import Team
        return Team.objects.create(**kwargs)

    return _create


@pytest.fixture
def authenticated_client(db):
    """A Django test client logged in as a regular user."""
    user = User.objects.create_user(
        username=f'authuser_{_next_id()}',
        email=f'authuser_{_next_id()}@test.deltacrown.local',
        password='testpass123',
    )
    c = Client()
    c.force_login(user)
    c.user = user
    return c
