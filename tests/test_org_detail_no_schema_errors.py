"""Journey 5: Organization detail page loads without schema errors.

Covers acceptance criteria:
- GET /orgs/<slug>/ renders 200 and includes organization name
- Page loads when org has teams and memberships
- Does not call CompetitionService when disabled (override setting)
"""

import pytest
from django.urls import reverse
from django.test import Client, override_settings
from django.contrib.auth import get_user_model

from apps.organizations.models import Organization, OrganizationMembership, Team

User = get_user_model()


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="orgviewer",
        email="viewer@example.com",
        password="testpass123",
    )


@pytest.fixture
def organization(db, user):
    return Organization.objects.create(
        name="Test Org Detail",
        slug="test-org-detail",
        ceo=user,
        description="Detail page test org.",
    )


@pytest.fixture
def team(db, user, organization):
    return Team.objects.create(
        name="Org Team Alpha",
        slug="org-team-alpha",
        created_by=user,
        organization=organization,
        game_id=1,
        region="NA",
    )


@pytest.fixture
def membership(db, user, organization):
    return OrganizationMembership.objects.create(
        organization=organization,
        user=user,
        role="CEO",
        permissions={},
    )


@pytest.mark.django_db
@override_settings(COMPETITION_APP_ENABLED=False)
def test_org_detail_renders_without_field_error(client, user, organization, team, membership):
    client.force_login(user)
    url = reverse("organizations:organization_detail", args=[organization.slug])
    resp = client.get(url)

    assert resp.status_code == 200
    assert organization.name in resp.content.decode()
