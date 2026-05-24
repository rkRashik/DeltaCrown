import json
from unittest.mock import patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.organizations.choices import MembershipRole, MembershipStatus, TeamStatus
from apps.organizations.models import OrganizationMembership, TeamCompetitiveSettings
from apps.organizations.services.team_authority import (
    can_manage_competitive_settings,
    can_view_competitive_settings,
)
from apps.organizations.tests.factories import (
    OrganizationFactory,
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)
from apps.organizations.views.team import team_manage


def api_url(name, **kwargs):
    return reverse(f"organizations_api:{name}", kwargs=kwargs)


def _json(data):
    return json.dumps(data)


class TeamManagePhase2BApiTests(TestCase):
    def _independent_team(self, name="Phase 2B Team"):
        owner = UserFactory()
        team = TeamFactory.create_independent(created_by=owner, name=name)
        TeamMembershipFactory(team=team, user=owner, role=MembershipRole.OWNER)
        return team, owner

    def _add_member_payload(self, user, role=MembershipRole.PLAYER):
        return _json({"identifier": user.username, "role": role})

    def test_coach_can_get_bootstrap_but_cannot_add_or_remove_member(self):
        team, owner = self._independent_team("Phase 2B Coach Team")
        coach = UserFactory(username="phase2b_coach")
        target = UserFactory(username="phase2b_target")
        target_membership = TeamMembershipFactory(team=team, user=target, role=MembershipRole.PLAYER)
        candidate = UserFactory(username="phase2b_candidate")
        TeamMembershipFactory(team=team, user=coach, role=MembershipRole.COACH)

        self.client.force_login(coach)
        self.assertEqual(self.client.get(api_url("team_manage_detail", slug=team.slug)).status_code, 200)
        add_response = self.client.post(
            api_url("team_manage_add_member", slug=team.slug),
            data=self._add_member_payload(candidate),
            content_type="application/json",
        )
        self.assertEqual(add_response.status_code, 403)
        remove_response = self.client.post(
            api_url("team_manage_remove_member", slug=team.slug, membership_id=target_membership.id)
        )
        self.assertEqual(remove_response.status_code, 403)

    def test_owner_can_add_member_and_update_profile(self):
        team, owner = self._independent_team("Phase 2B Owner Team")
        candidate = UserFactory(username="phase2b_owner_candidate")

        self.client.force_login(owner)
        add_response = self.client.post(
            api_url("team_manage_add_member", slug=team.slug),
            data=self._add_member_payload(candidate),
            content_type="application/json",
        )
        self.assertEqual(add_response.status_code, 200)
        profile_response = self.client.post(
            api_url("team_manage_update_profile", slug=team.slug),
            data=_json({"tagline": "Owner update"}),
            content_type="application/json",
        )
        self.assertEqual(profile_response.status_code, 200)

    def test_manager_can_add_member_and_update_profile_and_settings(self):
        team, _owner = self._independent_team("Phase 2B Manager Team")
        manager = UserFactory(username="phase2b_manager")
        candidate = UserFactory(username="phase2b_manager_candidate")
        TeamMembershipFactory(team=team, user=manager, role=MembershipRole.MANAGER)

        self.client.force_login(manager)
        add_response = self.client.post(
            api_url("team_manage_add_member", slug=team.slug),
            data=self._add_member_payload(candidate),
            content_type="application/json",
        )
        self.assertEqual(add_response.status_code, 200)
        profile_response = self.client.post(
            api_url("team_manage_update_profile", slug=team.slug),
            data=_json({"tagline": "Manager profile update"}),
            content_type="application/json",
        )
        self.assertEqual(profile_response.status_code, 200)
        settings_response = self.client.post(
            api_url("team_manage_update_settings", slug=team.slug),
            data=_json({"tagline": "Manager settings update"}),
            content_type="application/json",
        )
        self.assertEqual(settings_response.status_code, 200)

    def test_org_ceo_and_manager_can_add_member_to_org_team(self):
        ceo = UserFactory(username="phase2b_org_ceo")
        org_manager = UserFactory(username="phase2b_org_manager")
        org = OrganizationFactory(ceo=ceo)
        OrganizationMembership.objects.create(organization=org, user=org_manager, role="MANAGER")
        team = TeamFactory(organization=org, created_by=None, name="Phase 2B Org Add Team")

        for user, username in ((ceo, "phase2b_ceo_candidate"), (org_manager, "phase2b_mgr_candidate")):
            candidate = UserFactory(username=username)
            self.client.force_login(user)
            response = self.client.post(
                api_url("team_manage_add_member", slug=team.slug),
                data=self._add_member_payload(candidate),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

    def test_inactive_member_gets_forbidden_from_bootstrap(self):
        team, _owner = self._independent_team("Phase 2B Inactive Team")
        inactive = UserFactory(username="phase2b_inactive")
        TeamMembershipFactory(
            team=team,
            user=inactive,
            role=MembershipRole.MANAGER,
            status=MembershipStatus.INACTIVE,
        )

        self.client.force_login(inactive)
        response = self.client.get(api_url("team_manage_detail", slug=team.slug))
        self.assertEqual(response.status_code, 403)

    def test_disbanded_team_bootstrap_returns_forbidden(self):
        team, owner = self._independent_team("Phase 2B Disbanded Bootstrap")
        team.status = TeamStatus.DISBANDED
        team.save(update_fields=["status"])

        self.client.force_login(owner)
        response = self.client.get(api_url("team_manage_detail", slug=team.slug))
        self.assertEqual(response.status_code, 403)

    def test_competitive_settings_get_allows_active_player(self):
        team, _owner = self._independent_team("Phase 2B Competitive View")
        player = UserFactory(username="phase2b_comp_player")
        TeamMembershipFactory(team=team, user=player, role=MembershipRole.PLAYER)

        self.client.force_login(player)
        response = self.client.get(api_url("team_manage_competitive_settings", slug=team.slug))
        self.assertEqual(response.status_code, 200)

    def test_creator_without_membership_can_view_competitive_settings(self):
        creator = UserFactory(username="phase2b_comp_creator")
        non_member = UserFactory(username="phase2b_comp_non_member")
        inactive_member = UserFactory(username="phase2b_comp_inactive")
        team = TeamFactory.create_independent(created_by=creator, name="Phase 2B Creator Competitive")
        TeamMembershipFactory(
            team=team,
            user=inactive_member,
            role=MembershipRole.MANAGER,
            status=MembershipStatus.INACTIVE,
        )

        self.assertIs(can_view_competitive_settings(creator, team), True)
        self.assertIs(can_manage_competitive_settings(creator, team), True)
        self.assertIs(can_view_competitive_settings(non_member, team), False)
        self.assertIs(can_view_competitive_settings(inactive_member, team), False)

    def test_competitive_settings_patch_blocks_player_and_coach(self):
        team, _owner = self._independent_team("Phase 2B Competitive Block")
        player = UserFactory(username="phase2b_patch_player")
        coach = UserFactory(username="phase2b_patch_coach")
        TeamMembershipFactory(team=team, user=player, role=MembershipRole.PLAYER)
        TeamMembershipFactory(team=team, user=coach, role=MembershipRole.COACH)

        for user in (player, coach):
            self.client.force_login(user)
            response = self.client.patch(
                api_url("team_manage_competitive_settings", slug=team.slug),
                data=_json({"allow_public_scrim_availability": True}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 403)

    def test_competitive_settings_patch_allows_owner_and_manager(self):
        team, owner = self._independent_team("Phase 2B Competitive Edit")
        manager = UserFactory(username="phase2b_comp_manager")
        TeamMembershipFactory(team=team, user=manager, role=MembershipRole.MANAGER)
        TeamCompetitiveSettings.objects.get_or_create(team=team)

        for user in (owner, manager):
            self.client.force_login(user)
            response = self.client.patch(
                api_url("team_manage_competitive_settings", slug=team.slug),
                data=_json({"allow_public_scrim_availability": True}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

    def test_disband_independent_team_blocks_manager(self):
        team, _owner = self._independent_team("Phase 2B Manager Disband Block")
        manager = UserFactory(username="phase2b_disband_manager")
        TeamMembershipFactory(team=team, user=manager, role=MembershipRole.MANAGER)

        self.client.force_login(manager)
        response = self.client.post(
            api_url("team_manage_disband", slug=team.slug),
            data=_json({"confirm": team.name}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_disband_org_owned_team_allows_ceo_and_blocks_org_manager(self):
        ceo = UserFactory(username="phase2b_disband_ceo")
        org_manager = UserFactory(username="phase2b_disband_org_manager")
        org = OrganizationFactory(ceo=ceo)
        OrganizationMembership.objects.create(organization=org, user=org_manager, role="MANAGER")

        blocked_team = TeamFactory(organization=org, created_by=None, name="Phase 2B Org Manager Disband")
        self.client.force_login(org_manager)
        blocked = self.client.post(
            api_url("team_manage_disband", slug=blocked_team.slug),
            data=_json({"confirm": blocked_team.name}),
            content_type="application/json",
        )
        self.assertEqual(blocked.status_code, 403)

        allowed_team = TeamFactory(organization=org, created_by=None, name="Phase 2B Org CEO Disband")
        self.client.force_login(ceo)
        allowed = self.client.post(
            api_url("team_manage_disband", slug=allowed_team.slug),
            data=_json({"confirm": allowed_team.name}),
            content_type="application/json",
        )
        self.assertEqual(allowed.status_code, 200)

    def test_transfer_ownership_blocks_manager(self):
        team, _owner = self._independent_team("Phase 2B Transfer Block")
        manager = UserFactory(username="phase2b_transfer_manager")
        target = UserFactory(username="phase2b_transfer_target")
        target_membership = TeamMembershipFactory(team=team, user=target, role=MembershipRole.PLAYER)
        TeamMembershipFactory(team=team, user=manager, role=MembershipRole.MANAGER)

        self.client.force_login(manager)
        response = self.client.post(
            api_url("team_manage_transfer", slug=team.slug),
            data=_json({"member_id": target_membership.id, "confirm": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_api_user_role_never_returns_creator_or_none(self):
        creator = UserFactory(username="phase2b_creator_role")
        team = TeamFactory.create_independent(created_by=creator, name="Phase 2B Creator Role")

        self.client.force_login(creator)
        response = self.client.get(api_url("team_manage_detail", slug=team.slug))
        self.assertEqual(response.status_code, 200)
        user_role = response.json()["permissions"]["user_role"]
        self.assertEqual(user_role, "OWNER")
        self.assertNotIn(user_role, {"CREATOR", "NONE"})


class TeamManagePhase2BViewTests(TestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def _request(self, user, path="/teams/test/manage/"):
        request = self.rf.get(path)
        request.user = user
        request.session = SessionStore()
        request._messages = FallbackStorage(request)
        return request

    def _render_response(self, request, template, context):
        response = HttpResponse("ok")
        response.context_data = context
        return response

    def _independent_team(self, name="Phase 2B View Team"):
        owner = UserFactory()
        team = TeamFactory.create_independent(created_by=owner, name=name)
        TeamMembershipFactory(team=team, user=owner, role=MembershipRole.OWNER)
        return team, owner

    def test_team_manage_view_coach_is_coach_but_not_admin(self):
        team, _owner = self._independent_team("Phase 2B View Coach")
        coach = UserFactory(username="phase2b_view_coach")
        TeamMembershipFactory(team=team, user=coach, role=MembershipRole.COACH)

        with patch("apps.organizations.views.team.render", side_effect=self._render_response):
            response = team_manage(self._request(coach), team_slug=team.slug)

        self.assertEqual(response.status_code, 200)
        self.assertIs(response.context_data["is_coach"], True)
        self.assertIs(response.context_data["is_admin"], False)
        self.assertIs(response.context_data["can_manage_training"], True)
        self.assertIs(response.context_data["can_edit_team_profile"], False)

    def test_team_manage_view_disbanded_team_redirects_away(self):
        team, owner = self._independent_team("Phase 2B View Disbanded")
        team.status = TeamStatus.DISBANDED
        team.save(update_fields=["status"])

        response = team_manage(self._request(owner), team_slug=team.slug)
        self.assertEqual(response.status_code, 302)

    def test_team_manage_view_org_manager_is_admin_in_context(self):
        org_manager = UserFactory(username="phase2b_view_org_manager")
        org = OrganizationFactory()
        OrganizationMembership.objects.create(organization=org, user=org_manager, role="MANAGER")
        team = TeamFactory(organization=org, created_by=None, name="Phase 2B View Org Manager")

        with patch("apps.organizations.views.team.render", side_effect=self._render_response):
            response = team_manage(
                self._request(org_manager, path=f"/orgs/{org.slug}/teams/{team.slug}/manage/"),
                org_slug=org.slug,
                team_slug=team.slug,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIs(response.context_data["is_admin"], True)
        self.assertIs(response.context_data["can_manage_roster"], True)
        self.assertIs(response.context_data["can_delete_team"], False)

    def test_team_manage_view_non_member_redirects_to_detail(self):
        team, _owner = self._independent_team("Phase 2B View Non Member")
        outsider = UserFactory(username="phase2b_view_outsider")

        response = team_manage(self._request(outsider), team_slug=team.slug)
        self.assertEqual(response.status_code, 302)
