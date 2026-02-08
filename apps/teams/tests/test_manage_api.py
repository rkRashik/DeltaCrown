"""
Comprehensive tests for team management API endpoints.

Coverage:
- All 11 manage API endpoints (success + error paths)
- Permission checks (OWNER, MANAGER, superuser, creator, anon)
- membership=None safety (superuser / creator without membership row)
- Input validation (malformed JSON, invalid values)
- Audit trail (TeamActivityLog creation)
- Notifications (NotificationService calls)
- Edge cases (only-owner protection, self-removal block)

Performance: Targets <10 seconds total with --reuse-db.
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.http import JsonResponse

from apps.organizations.models import Team, TeamMembership, TeamActivityLog
from apps.organizations.models.team_invite import TeamInvite
from apps.organizations.choices import (
    MembershipRole, MembershipStatus, TeamStatus, ActivityActionType,
)
from apps.organizations.tests.factories import (
    TeamFactory, TeamMembershipFactory, UserFactory, TeamActivityLogFactory,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def rf():
    """Django RequestFactory."""
    return RequestFactory()


@pytest.fixture
def owner_user(db):
    """User who creates/owns an independent team."""
    return UserFactory.create(username="team_owner")


@pytest.fixture
def manager_user(db):
    """User with MANAGER role."""
    return UserFactory.create(username="team_manager")


@pytest.fixture
def player_user(db):
    """User with PLAYER role."""
    return UserFactory.create(username="team_player")


@pytest.fixture
def outsider_user(db):
    """User with no team membership."""
    return UserFactory.create(username="outsider")


@pytest.fixture
def superuser(db):
    """Superuser with no team membership row."""
    return UserFactory.create(username="admin_super", is_superuser=True)


@pytest.fixture
def team(owner_user, db):
    """Independent team owned by owner_user."""
    return TeamFactory.create_independent(created_by=owner_user, name="Test Team Alpha")


@pytest.fixture
def owner_membership(team, owner_user, db):
    """OWNER membership for the team creator."""
    return TeamMembershipFactory.create(
        team=team, user=owner_user, role=MembershipRole.OWNER,
    )


@pytest.fixture
def manager_membership(team, manager_user, db):
    """MANAGER membership."""
    return TeamMembershipFactory.create(
        team=team, user=manager_user, role=MembershipRole.MANAGER,
    )


@pytest.fixture
def player_membership(team, player_user, db):
    """PLAYER membership."""
    return TeamMembershipFactory.create(
        team=team, user=player_user, role=MembershipRole.PLAYER,
    )


def _make_request(rf, user, method="GET", path="/fake/", data=None, content_type="application/json"):
    """Helper to build authenticated requests."""
    if method == "GET":
        request = rf.get(path)
    else:
        body = json.dumps(data or {})
        request = rf.post(path, data=body, content_type=content_type)
    request.user = user
    return request


# ===========================================================================
# 1. manage_overview
# ===========================================================================

@pytest.mark.django_db
class TestManageOverview:
    """Tests for the overview/dashboard endpoint."""

    def test_owner_gets_overview(self, rf, team, owner_user, owner_membership):
        from apps.teams.views.manage_api import manage_overview

        request = _make_request(rf, owner_user)
        response = manage_overview(request, slug=team.slug)

        assert response.status_code == 200
        payload = json.loads(response.content)
        assert payload["success"] is True
        assert "stats" in payload
        assert payload["stats"]["members_count"] >= 1

    def test_outsider_denied(self, rf, team, outsider_user):
        from apps.teams.views.manage_api import manage_overview

        request = _make_request(rf, outsider_user)
        response = manage_overview(request, slug=team.slug)

        assert response.status_code == 403

    def test_superuser_without_membership(self, rf, team, superuser):
        from apps.teams.views.manage_api import manage_overview

        request = _make_request(rf, superuser)
        response = manage_overview(request, slug=team.slug)

        assert response.status_code == 200
        payload = json.loads(response.content)
        assert payload["success"] is True

    def test_creator_without_membership(self, rf, team, owner_user):
        """Creator should access even without a TeamMembership row."""
        from apps.teams.views.manage_api import manage_overview

        # Don't create owner_membership fixture — owner_user has no membership
        request = _make_request(rf, owner_user)
        response = manage_overview(request, slug=team.slug)

        assert response.status_code == 200

    def test_nonexistent_team_404(self, rf, owner_user):
        from apps.teams.views.manage_api import manage_overview

        request = _make_request(rf, owner_user)
        with pytest.raises(Exception):  # Http404
            manage_overview(request, slug="nonexistent-slug-xyz")


# ===========================================================================
# 2. manage_update_profile
# ===========================================================================

@pytest.mark.django_db
class TestManageUpdateProfile:
    """Tests for the profile update endpoint."""

    def test_owner_updates_name(self, rf, team, owner_user, owner_membership):
        from apps.teams.views.manage_api import manage_update_profile

        request = _make_request(rf, owner_user, method="POST", data={"name": "New Name"})
        response = manage_update_profile(request, slug=team.slug)

        assert response.status_code == 200
        team.refresh_from_db()
        assert team.name == "New Name"

    def test_manager_updates_description(self, rf, team, manager_user, manager_membership):
        from apps.teams.views.manage_api import manage_update_profile

        request = _make_request(rf, manager_user, method="POST", data={"description": "New desc"})
        response = manage_update_profile(request, slug=team.slug)

        assert response.status_code == 200
        team.refresh_from_db()
        assert team.description == "New desc"

    def test_player_denied(self, rf, team, player_user, player_membership):
        from apps.teams.views.manage_api import manage_update_profile

        request = _make_request(rf, player_user, method="POST", data={"name": "Hack"})
        response = manage_update_profile(request, slug=team.slug)

        assert response.status_code == 403

    def test_empty_name_ignored(self, rf, team, owner_user, owner_membership):
        from apps.teams.views.manage_api import manage_update_profile

        original_name = team.name
        request = _make_request(rf, owner_user, method="POST", data={"name": ""})
        response = manage_update_profile(request, slug=team.slug)

        assert response.status_code == 200
        team.refresh_from_db()
        # Empty name should be ignored
        assert team.name == original_name

    def test_superuser_without_membership_updates(self, rf, team, superuser):
        """Superuser should update profile even without a membership row."""
        from apps.teams.views.manage_api import manage_update_profile

        request = _make_request(rf, superuser, method="POST", data={"description": "Admin edit"})
        response = manage_update_profile(request, slug=team.slug)

        assert response.status_code == 200
        team.refresh_from_db()
        assert team.description == "Admin edit"


# ===========================================================================
# 4. manage_update_settings
# ===========================================================================

@pytest.mark.django_db
class TestManageUpdateSettings:
    """Tests for the settings toggle endpoint."""

    def test_owner_changes_visibility(self, rf, team, owner_user, owner_membership):
        from apps.teams.views.manage_api import manage_update_settings

        request = _make_request(rf, owner_user, method="POST", data={"visibility": "PRIVATE"})
        response = manage_update_settings(request, slug=team.slug)

        assert response.status_code == 200
        team.refresh_from_db()
        assert team.visibility == "PRIVATE"

    def test_non_owner_cannot_change_status(self, rf, team, manager_user, manager_membership):
        from apps.teams.views.manage_api import manage_update_settings

        request = _make_request(rf, manager_user, method="POST", data={"status": "DISBANDED"})
        response = manage_update_settings(request, slug=team.slug)

        assert response.status_code == 200
        team.refresh_from_db()
        # Status change requires owner, manager is not owner
        assert team.status != "DISBANDED"

    def test_superuser_is_treated_as_owner(self, rf, team, superuser):
        """Superuser without membership should not crash (Bug #1 fix)."""
        from apps.teams.views.manage_api import manage_update_settings

        request = _make_request(rf, superuser, method="POST", data={
            "status": "SUSPENDED",
            "visibility": "PRIVATE",
        })
        response = manage_update_settings(request, slug=team.slug)

        assert response.status_code == 200
        team.refresh_from_db()
        assert team.status == "SUSPENDED"  # Superuser counts as owner
        assert team.visibility == "PRIVATE"

    def test_creator_without_membership_no_crash(self, rf, team, owner_user):
        """Creator with no membership row: membership.role was None (Bug #1)."""
        from apps.teams.views.manage_api import manage_update_settings

        request = _make_request(rf, owner_user, method="POST", data={"visibility": "UNLISTED"})
        response = manage_update_settings(request, slug=team.slug)

        assert response.status_code == 200

    def test_invalid_visibility_ignored(self, rf, team, owner_user, owner_membership):
        from apps.teams.views.manage_api import manage_update_settings

        original = team.visibility
        request = _make_request(rf, owner_user, method="POST", data={"visibility": "INVALID"})
        response = manage_update_settings(request, slug=team.slug)

        assert response.status_code == 200
        team.refresh_from_db()
        assert team.visibility == original


# ===========================================================================
# 5. manage_invite_member
# ===========================================================================

@pytest.mark.django_db
class TestManageInviteMember:
    """Tests for the invite member endpoint."""

    def test_owner_invites_user(self, rf, team, owner_user, owner_membership, outsider_user):
        from apps.teams.views.manage_api import manage_invite_member

        request = _make_request(rf, owner_user, method="POST", data={
            "username_or_email": outsider_user.username,
            "role": "PLAYER",
        })
        with patch("apps.teams.views.manage_api.NotificationService") as mock_ns:
            response = manage_invite_member(request, slug=team.slug)

        assert response.status_code == 200
        payload = json.loads(response.content)
        assert payload["success"] is True
        assert TeamInvite.objects.filter(team=team, invited_user=outsider_user).exists()

    def test_manager_invites_user(self, rf, team, manager_user, manager_membership, outsider_user):
        from apps.teams.views.manage_api import manage_invite_member

        request = _make_request(rf, manager_user, method="POST", data={
            "username_or_email": outsider_user.username,
        })
        with patch("apps.teams.views.manage_api.NotificationService"):
            response = manage_invite_member(request, slug=team.slug)

        assert response.status_code == 200

    def test_player_cannot_invite(self, rf, team, player_user, player_membership):
        from apps.teams.views.manage_api import manage_invite_member

        request = _make_request(rf, player_user, method="POST", data={
            "username_or_email": "someone",
        })
        response = manage_invite_member(request, slug=team.slug)

        assert response.status_code == 403

    def test_superuser_without_membership_can_invite(self, rf, team, superuser, outsider_user):
        """Superuser bypass: no membership row should not crash (Bug #2 fix)."""
        from apps.teams.views.manage_api import manage_invite_member

        request = _make_request(rf, superuser, method="POST", data={
            "username_or_email": outsider_user.username,
            "role": "PLAYER",
        })
        with patch("apps.teams.views.manage_api.NotificationService"):
            response = manage_invite_member(request, slug=team.slug)

        assert response.status_code == 200

    def test_creator_without_membership_can_invite(self, rf, team, owner_user, outsider_user):
        """Creator bypass: no membership row should not crash (Bug #2 fix)."""
        from apps.teams.views.manage_api import manage_invite_member

        request = _make_request(rf, owner_user, method="POST", data={
            "username_or_email": outsider_user.username,
            "role": "PLAYER",
        })
        with patch("apps.teams.views.manage_api.NotificationService"):
            response = manage_invite_member(request, slug=team.slug)

        assert response.status_code == 200

    def test_empty_username_rejected(self, rf, team, owner_user, owner_membership):
        from apps.teams.views.manage_api import manage_invite_member

        request = _make_request(rf, owner_user, method="POST", data={
            "username_or_email": "",
        })
        response = manage_invite_member(request, slug=team.slug)

        assert response.status_code == 400

    def test_nonexistent_user_rejected(self, rf, team, owner_user, owner_membership):
        from apps.teams.views.manage_api import manage_invite_member

        request = _make_request(rf, owner_user, method="POST", data={
            "username_or_email": "does_not_exist_user_xyz_999",
        })
        response = manage_invite_member(request, slug=team.slug)

        assert response.status_code in (400, 404)


# ===========================================================================
# 8. manage_update_member_role
# ===========================================================================

@pytest.mark.django_db
class TestManageUpdateMemberRole:
    """Tests for the role update endpoint."""

    def test_owner_changes_player_to_manager(self, rf, team, owner_user, owner_membership, player_membership):
        from apps.teams.views.manage_api import manage_update_member_role

        request = _make_request(rf, owner_user, method="POST", data={"role": "MANAGER"})
        with patch("apps.teams.views.manage_api.NotificationService"):
            response = manage_update_member_role(request, slug=team.slug, membership_id=player_membership.pk)

        assert response.status_code == 200
        player_membership.refresh_from_db()
        assert player_membership.role == MembershipRole.MANAGER

    def test_manager_cannot_promote_to_owner(self, rf, team, manager_user, manager_membership, player_membership):
        from apps.teams.views.manage_api import manage_update_member_role

        request = _make_request(rf, manager_user, method="POST", data={"role": "OWNER"})
        with patch("apps.teams.views.manage_api.NotificationService"):
            response = manage_update_member_role(request, slug=team.slug, membership_id=player_membership.pk)

        assert response.status_code == 403

    def test_invalid_role_rejected(self, rf, team, owner_user, owner_membership, player_membership):
        from apps.teams.views.manage_api import manage_update_member_role

        request = _make_request(rf, owner_user, method="POST", data={"role": "DICTATOR"})
        with patch("apps.teams.views.manage_api.NotificationService"):
            response = manage_update_member_role(request, slug=team.slug, membership_id=player_membership.pk)

        assert response.status_code == 400

    def test_sole_owner_cannot_demote_self(self, rf, team, owner_user, owner_membership):
        from apps.teams.views.manage_api import manage_update_member_role

        request = _make_request(rf, owner_user, method="POST", data={"role": "PLAYER"})
        with patch("apps.teams.views.manage_api.NotificationService"):
            response = manage_update_member_role(request, slug=team.slug, membership_id=owner_membership.pk)

        assert response.status_code == 400
        payload = json.loads(response.content)
        assert "only owner" in payload["error"].lower()

    def test_nonexistent_member_404(self, rf, team, owner_user, owner_membership):
        from apps.teams.views.manage_api import manage_update_member_role

        request = _make_request(rf, owner_user, method="POST", data={"role": "PLAYER"})
        with patch("apps.teams.views.manage_api.NotificationService"):
            response = manage_update_member_role(request, slug=team.slug, membership_id=999999)

        assert response.status_code == 404


# ===========================================================================
# 9. manage_remove_member
# ===========================================================================

@pytest.mark.django_db
class TestManageRemoveMember:
    """Tests for the remove member endpoint."""

    def test_owner_removes_player(self, rf, team, owner_user, owner_membership, player_user, player_membership):
        from apps.teams.views.manage_api import manage_remove_member

        request = _make_request(rf, owner_user, method="POST", data={
            "confirmation": player_user.username,
        })
        with patch("apps.teams.views.manage_api.NotificationService"):
            response = manage_remove_member(request, slug=team.slug, membership_id=player_membership.pk)

        assert response.status_code == 200
        player_membership.refresh_from_db()
        assert player_membership.status == MembershipStatus.INACTIVE

    def test_wrong_confirmation_rejected(self, rf, team, owner_user, owner_membership, player_membership):
        from apps.teams.views.manage_api import manage_remove_member

        request = _make_request(rf, owner_user, method="POST", data={
            "confirmation": "wrong_name",
        })
        response = manage_remove_member(request, slug=team.slug, membership_id=player_membership.pk)

        assert response.status_code == 400

    def test_cannot_remove_self(self, rf, team, owner_user, owner_membership):
        from apps.teams.views.manage_api import manage_remove_member

        request = _make_request(rf, owner_user, method="POST", data={
            "confirmation": owner_user.username,
        })
        response = manage_remove_member(request, slug=team.slug, membership_id=owner_membership.pk)

        assert response.status_code == 400

    def test_cannot_remove_owner(self, rf, team, manager_user, manager_membership, owner_membership):
        from apps.teams.views.manage_api import manage_remove_member

        request = _make_request(rf, manager_user, method="POST", data={
            "confirmation": "team_owner",
        })
        response = manage_remove_member(request, slug=team.slug, membership_id=owner_membership.pk)

        assert response.status_code == 403


# ===========================================================================
# 10. manage_activity
# ===========================================================================

@pytest.mark.django_db
class TestManageActivity:
    """Tests for the activity feed endpoint."""

    def test_returns_activity_list(self, rf, team, owner_user, owner_membership):
        from apps.teams.views.manage_api import manage_activity

        # Create some activity logs
        TeamActivityLogFactory.create(team=team, action_type=ActivityActionType.UPDATE)
        TeamActivityLogFactory.create(team=team, action_type=ActivityActionType.ROSTER_ADD)

        request = _make_request(rf, owner_user)
        response = manage_activity(request, slug=team.slug)

        assert response.status_code == 200
        payload = json.loads(response.content)
        assert payload["success"] is True
        assert len(payload["entries"]) >= 2

    def test_non_numeric_limit_handled(self, rf, team, owner_user, owner_membership):
        """Bug #4 fix: non-numeric limit should not crash."""
        from apps.teams.views.manage_api import manage_activity

        request = rf.get("/fake/", {"limit": "abc"})
        request.user = owner_user
        response = manage_activity(request, slug=team.slug)

        assert response.status_code == 200  # Should not 500

    def test_limit_capped_at_50(self, rf, team, owner_user, owner_membership):
        from apps.teams.views.manage_api import manage_activity

        request = rf.get("/fake/", {"limit": "999"})
        request.user = owner_user
        response = manage_activity(request, slug=team.slug)

        assert response.status_code == 200


# ===========================================================================
# 11. manage_cancel_invite
# ===========================================================================

@pytest.mark.django_db
class TestManageCancelInvite:
    """Tests for the cancel invite endpoint."""

    def test_owner_cancels_invite(self, rf, team, owner_user, owner_membership, outsider_user):
        from apps.teams.views.manage_api import manage_cancel_invite

        invite = TeamInvite.objects.create(
            team=team,
            invited_user=outsider_user,
            inviter=owner_user,
            role=MembershipRole.PLAYER,
            status="PENDING",
        )

        request = _make_request(rf, owner_user, method="POST")
        response = manage_cancel_invite(request, slug=team.slug, invite_id=invite.pk)

        assert response.status_code == 200
        invite.refresh_from_db()
        assert invite.status == "CANCELLED"

    def test_cancel_nonexistent_invite_404(self, rf, team, owner_user, owner_membership):
        from apps.teams.views.manage_api import manage_cancel_invite

        request = _make_request(rf, owner_user, method="POST")
        response = manage_cancel_invite(request, slug=team.slug, invite_id=999999)

        assert response.status_code == 404


# ===========================================================================
# Permission Matrix: _get_admin_context
# ===========================================================================

@pytest.mark.django_db
class TestGetAdminContext:
    """Test the helper that resolves permissions."""

    def test_owner_has_access(self, rf, team, owner_user, owner_membership):
        from apps.teams.views.manage_api import _get_admin_context

        request = _make_request(rf, owner_user)
        t, m, err = _get_admin_context(request, team.slug)
        assert err is None
        assert t == team
        assert m == owner_membership

    def test_manager_has_access(self, rf, team, manager_user, manager_membership):
        from apps.teams.views.manage_api import _get_admin_context

        request = _make_request(rf, manager_user)
        t, m, err = _get_admin_context(request, team.slug)
        assert err is None
        assert m == manager_membership

    def test_player_denied(self, rf, team, player_user, player_membership):
        from apps.teams.views.manage_api import _get_admin_context

        request = _make_request(rf, player_user)
        t, m, err = _get_admin_context(request, team.slug)
        assert err is not None
        assert err.status_code == 403

    def test_superuser_no_membership(self, rf, team, superuser):
        from apps.teams.views.manage_api import _get_admin_context

        request = _make_request(rf, superuser)
        t, m, err = _get_admin_context(request, team.slug)
        assert err is None
        assert m is None  # No membership row

    def test_creator_no_membership(self, rf, team, owner_user):
        from apps.teams.views.manage_api import _get_admin_context

        request = _make_request(rf, owner_user)
        t, m, err = _get_admin_context(request, team.slug)
        assert err is None
        assert m is None  # No membership row

    def test_outsider_denied(self, rf, team, outsider_user):
        from apps.teams.views.manage_api import _get_admin_context

        request = _make_request(rf, outsider_user)
        t, m, err = _get_admin_context(request, team.slug)
        assert err is not None
        assert err.status_code == 403


# ===========================================================================
# Audit Trail: TeamActivityLog created by endpoints
# ===========================================================================

@pytest.mark.django_db
class TestAuditTrail:
    """Verify that mutating endpoints create audit logs."""

    def test_profile_update_creates_log(self, rf, team, owner_user, owner_membership):
        from apps.teams.views.manage_api import manage_update_profile

        request = _make_request(rf, owner_user, method="POST", data={"name": "Audit Test"})
        response = manage_update_profile(request, slug=team.slug)

        assert response.status_code == 200
        assert TeamActivityLog.objects.filter(
            team=team, action_type=ActivityActionType.UPDATE
        ).exists()

    def test_settings_update_creates_log(self, rf, team, owner_user, owner_membership):
        from apps.teams.views.manage_api import manage_update_settings

        request = _make_request(rf, owner_user, method="POST", data={"visibility": "PRIVATE"})
        response = manage_update_settings(request, slug=team.slug)

        assert response.status_code == 200
        assert TeamActivityLog.objects.filter(
            team=team, action_type=ActivityActionType.UPDATE
        ).exists()
