"""Journey 4: Organization create API contract tests.

Covers /api/vnext/organizations/create/ acceptance criteria:
- Success: redirects (organization_url) and creates CEO membership
- Conflict: duplicate name returns conflict code and does not create a second org

Note: Tests are placed in tests/ per tracker hygiene rules.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.organizations.models import Organization, OrganizationMembership

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="orgcreator",
        email="orgcreator@example.com",
        password="testpass123",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="othercreator",
        email="othercreator@example.com",
        password="testpass123",
    )


@pytest.mark.django_db
class TestOrganizationCreate:
    def test_create_org_redirects_and_creates_ceo_membership(self, api_client, user):
        api_client.force_authenticate(user=user)

        payload = {
            "name": "Syntax Esports",
            "slug": "syntax-esports",
            "branding": {
                "description": "We build champions.",
                "primary_color": "#FF5733",
            },
        }

        resp = api_client.post("/api/vnext/organizations/create/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["ok"] is True
        assert resp.data["organization_slug"] == "syntax-esports"
        assert resp.data["organization_url"] == "/orgs/syntax-esports/"

        org = Organization.objects.get(slug="syntax-esports")
        assert org.name == "Syntax Esports"
        assert org.ceo_id == user.id
        assert org.description == "We build champions."

        membership = OrganizationMembership.objects.get(organization=org, user=user)
        assert membership.role == "CEO"

    def test_duplicate_name_returns_conflict(self, api_client, user, other_user):
        api_client.force_authenticate(user=user)
        resp1 = api_client.post(
            "/api/vnext/organizations/create/",
            {"name": "Cloud9 Bangladesh", "slug": "cloud9-bd"},
            format="json",
        )
        assert resp1.status_code == status.HTTP_201_CREATED, resp1.data

        api_client.force_authenticate(user=other_user)
        resp2 = api_client.post(
            "/api/vnext/organizations/create/",
            {"name": "Cloud9 Bangladesh", "slug": "cloud9-bd-2"},
            format="json",
        )

        assert resp2.status_code in (status.HTTP_409_CONFLICT, status.HTTP_400_BAD_REQUEST), resp2.data
        assert resp2.data.get("error_code") in {"NAME_CONFLICT", "organization_already_exists"}
        assert Organization.objects.filter(name="Cloud9 Bangladesh").count() == 1

    def test_validate_name_endpoint_reports_availability(self, api_client, user):
        api_client.force_authenticate(user=user)

        ok_resp = api_client.get(
            "/api/vnext/organizations/validate-name/",
            {"name": "New Org"},
        )
        assert ok_resp.status_code == status.HTTP_200_OK, ok_resp.data
        assert ok_resp.data.get("ok") is True
        assert ok_resp.data.get("available") is True

        # Reserve the name
        api_client.post(
            "/api/vnext/organizations/create/",
            {"name": "New Org", "slug": "new-org"},
            format="json",
        )

        conflict_resp = api_client.get(
            "/api/vnext/organizations/validate-name/",
            {"name": "New Org"},
        )
        assert conflict_resp.status_code == status.HTTP_200_OK, conflict_resp.data
        assert conflict_resp.data.get("ok") is False
        assert conflict_resp.data.get("available") is False
        assert "field_errors" in conflict_resp.data

    def test_validate_slug_endpoint_blocks_existing_slug(self, api_client, user):
        api_client.force_authenticate(user=user)

        ok_resp = api_client.get(
            "/api/vnext/organizations/validate-slug/",
            {"slug": "fresh-slug"},
        )
        assert ok_resp.status_code == status.HTTP_200_OK, ok_resp.data
        assert ok_resp.data.get("ok") is True
        assert ok_resp.data.get("available") is True

        # Reserve the slug
        api_client.post(
            "/api/vnext/organizations/create/",
            {"name": "Fresh Org", "slug": "fresh-slug"},
            format="json",
        )

        conflict_resp = api_client.get(
            "/api/vnext/organizations/validate-slug/",
            {"slug": "fresh-slug"},
        )
        assert conflict_resp.status_code == status.HTTP_200_OK, conflict_resp.data
        assert conflict_resp.data.get("ok") is False
        assert conflict_resp.data.get("available") is False
        assert "field_errors" in conflict_resp.data

    def test_validate_badge_endpoint_rejects_short_badge(self, api_client, user):
        api_client.force_authenticate(user=user)

        too_short = api_client.get(
            "/api/vnext/organizations/validate-badge/",
            {"badge": "A"},
        )
        assert too_short.status_code == status.HTTP_200_OK, too_short.data
        assert too_short.data.get("ok") is False
        assert "field_errors" in too_short.data

        ok_resp = api_client.get(
            "/api/vnext/organizations/validate-badge/",
            {"badge": "DC"},
        )
        assert ok_resp.status_code == status.HTTP_200_OK, ok_resp.data
        assert ok_resp.data.get("ok") is True
        assert ok_resp.data.get("available") is True
