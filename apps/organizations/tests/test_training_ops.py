from datetime import timedelta
import json

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.games.models import Game
from apps.organizations.choices import MembershipRole, MembershipStatus
from apps.organizations.models import Team, TeamMembership
from apps.organizations.models.join_request import TeamJoinRequest
from apps.organizations.models.recruitment import RecruitmentPosition
from apps.organizations.models.training import ScrimRequest, TryoutApplication, TryoutSession
from apps.organizations.services.team_detail_context import get_team_detail_context
from apps.organizations.services.training_service import TeamTrainingService


pytestmark = pytest.mark.django_db


def _user(username):
    return User.objects.create_user(username=username, email=f"{username}@example.com", password="pass")


def _game():
    return Game.objects.create(
        name="Valorant Training",
        display_name="Valorant Training",
        slug="valorant-training",
        short_code="VTR",
        category="FPS",
        game_type="TEAM_VS_TEAM",
        platforms=["PC"],
    )


def _team(name, owner, game):
    team = Team.objects.create(
        name=name,
        slug=name.lower().replace(" ", "-"),
        created_by=owner,
        game_id=game.pk,
        region="Bangladesh",
    )
    TeamMembership.objects.create(
        team=team,
        user=owner,
        role=MembershipRole.OWNER,
        status=MembershipStatus.ACTIVE,
    )
    return team


def test_team_owner_can_post_scrim_request():
    game = _game()
    owner = _user("owner")
    team = _team("Alpha", owner, game)

    scrim = TeamTrainingService.create_scrim_request(
        team=team,
        actor=owner,
        scheduled_at=timezone.now() + timedelta(days=1),
        format=ScrimRequest.Format.BO3,
        notes="Practice only, no rewards.",
    )

    assert scrim.requesting_team == team
    assert scrim.status == ScrimRequest.Status.OPEN
    assert scrim.game == game


def test_regular_player_cannot_post_scrim_request():
    game = _game()
    owner = _user("owner2")
    player = _user("player")
    team = _team("Beta", owner, game)
    TeamMembership.objects.create(
        team=team,
        user=player,
        role=MembershipRole.PLAYER,
        status=MembershipStatus.ACTIVE,
    )

    with pytest.raises(PermissionDenied):
        TeamTrainingService.create_scrim_request(
            team=team,
            actor=player,
            scheduled_at=timezone.now() + timedelta(days=1),
        )


def test_player_can_apply_for_tryout():
    game = _game()
    owner = _user("owner3")
    applicant = _user("applicant")
    team = _team("Gamma", owner, game)

    app = TeamTrainingService.apply_for_tryout(
        team=team,
        applicant=applicant,
        ign="Applicant#BD",
        preferred_role="IGL",
        rank_tier="Diamond",
        availability="Weekend evenings",
    )

    assert app.status == TryoutApplication.Status.PENDING
    assert app.applicant == applicant
    assert app.team == team


def test_manager_can_review_tryout_application():
    game = _game()
    owner = _user("owner4")
    manager = _user("manager")
    applicant = _user("candidate")
    team = _team("Delta", owner, game)
    TeamMembership.objects.create(
        team=team,
        user=manager,
        role=MembershipRole.MANAGER,
        status=MembershipStatus.ACTIVE,
    )
    app = TeamTrainingService.apply_for_tryout(team=team, applicant=applicant)

    updated = TeamTrainingService.review_tryout_application(
        application=app,
        actor=manager,
        status=TryoutApplication.Status.OBSERVATION,
        review_notes="Needs one more session.",
    )

    assert updated.status == TryoutApplication.Status.OBSERVATION
    assert updated.reviewed_by == manager


def test_team_cannot_accept_own_scrim_request():
    game = _game()
    owner = _user("owner5")
    team = _team("Echo", owner, game)
    scrim = TeamTrainingService.create_scrim_request(
        team=team,
        actor=owner,
        scheduled_at=timezone.now() + timedelta(days=1),
    )

    with pytest.raises(ValidationError):
        TeamTrainingService.accept_scrim_request(
            scrim_request=scrim,
            accepting_team=team,
            actor=owner,
        )


def test_duplicate_active_tryout_application_blocked():
    game = _game()
    owner = _user("owner6")
    applicant = _user("candidate2")
    team = _team("Foxtrot", owner, game)

    TeamTrainingService.apply_for_tryout(team=team, applicant=applicant, ign="Candidate")

    with pytest.raises(ValidationError):
        TeamTrainingService.apply_for_tryout(team=team, applicant=applicant, ign="CandidateAgain")


def test_public_tryout_application_api_accepts_player_payload(client):
    game = _game()
    owner = _user("owner7")
    applicant = _user("candidate3")
    team = _team("Hotel", owner, game)
    team.is_recruiting = True
    team.save(update_fields=["is_recruiting"])
    client.force_login(applicant)

    response = client.post(
        f"/api/vnext/teams/{team.slug}/training/tryouts/",
        data=json.dumps({
            "game_id": game.pk,
            "ign": "Candidate#BD",
            "preferred_role": "Support",
            "rank_tier": "Diamond",
            "availability": "Friday evening",
            "profile_links": ["https://example.com/profile"],
            "notes": "Available for a scrim tryout.",
        }),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert TryoutApplication.objects.filter(team=team, applicant=applicant).exists()


def test_manager_can_schedule_tryout_via_api(client):
    game = _game()
    owner = _user("owner8")
    applicant = _user("candidate4")
    team = _team("India", owner, game)
    app = TeamTrainingService.apply_for_tryout(team=team, applicant=applicant)
    client.force_login(owner)

    response = client.post(
        f"/api/vnext/teams/{team.slug}/training/tryouts/{app.pk}/schedule/",
        data=json.dumps({
            "date": (timezone.now() + timedelta(days=2)).date().isoformat(),
            "time": "20:30",
            "format": "BO3 role test",
            "room_details": "Private lobby details",
        }),
        content_type="application/json",
    )

    assert response.status_code == 200
    app.refresh_from_db()
    assert app.status == TryoutApplication.Status.SCHEDULED


def test_unauthorized_user_cannot_review_tryout_via_api(client):
    game = _game()
    owner = _user("owner9")
    applicant = _user("candidate5")
    outsider = _user("outsider")
    team = _team("Juliet", owner, game)
    app = TeamTrainingService.apply_for_tryout(team=team, applicant=applicant)
    client.force_login(outsider)

    response = client.post(
        f"/api/vnext/teams/{team.slug}/training/tryouts/{app.pk}/review/",
        data=json.dumps({"action": "ACCEPT", "notes": "No authority"}),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_public_team_training_context_excludes_private_scrim_notes():
    game = _game()
    owner = _user("owner10")
    viewer = _user("viewer")
    team = _team("Kilo", owner, game)
    team.is_recruiting = True
    team.save(update_fields=["is_recruiting"])
    RecruitmentPosition.objects.create(team=team, title="Support", short_pitch="Support tryouts open.")
    TeamTrainingService.create_scrim_request(
        team=team,
        actor=owner,
        scheduled_at=timezone.now() + timedelta(days=1),
        format=ScrimRequest.Format.BO3,
        skill_level="Diamond+",
        server_region="Singapore",
        notes="Private lobby password should not be public.",
    )

    context = get_team_detail_context(team_slug=team.slug, viewer=viewer)
    public_scrim = context["training"]["public_scrims"][0]

    assert context["training"]["tryouts_enabled"] is True
    assert public_scrim["format"] == ScrimRequest.Format.BO3
    assert "notes" not in public_scrim


def test_public_team_context_shows_applicant_safe_tryout_status():
    game = _game()
    owner = _user("owner11")
    applicant = _user("candidate6")
    team = _team("Lima", owner, game)
    team.is_recruiting = True
    team.save(update_fields=["is_recruiting"])
    RecruitmentPosition.objects.create(team=team, title="Entry")
    app = TeamTrainingService.apply_for_tryout(team=team, applicant=applicant, ign="Candidate")
    session = TryoutSession.objects.create(
        application=app,
        team=team,
        applicant=applicant,
        scheduled_at=timezone.now() + timedelta(days=2),
        review_notes="Private manager-only review note.",
    )
    app.status = TryoutApplication.Status.SCHEDULED
    app.review_notes = "Private application review note."
    app.save(update_fields=["status", "review_notes"])

    context = get_team_detail_context(team_slug=team.slug, viewer=applicant)
    status = context["training"]["applicant_status"]

    assert status["title"] == "Tryout Scheduled"
    assert status["scheduled_at"] == session.scheduled_at
    assert "review_notes" not in status
    assert context["pending_actions"]["can_request_to_join"] is False


def test_tryout_status_endpoint_is_applicant_safe(client):
    game = _game()
    owner = _user("owner12")
    applicant = _user("candidate7")
    team = _team("Mike", owner, game)
    app = TeamTrainingService.apply_for_tryout(team=team, applicant=applicant, ign="Candidate")
    app.review_notes = "Private note."
    app.save(update_fields=["review_notes"])
    client.force_login(applicant)

    response = client.get(f"/api/vnext/teams/{team.slug}/training/tryouts/status/")
    payload = response.json()

    assert response.status_code == 200
    assert payload["applicant_status"]["title"] == "Tryout Applied"
    assert payload["tryout"]["notes"] == ""
    assert payload["tryout"]["review_notes"] == ""


def test_active_join_request_blocks_tryout_application_api(client):
    game = _game()
    owner = _user("owner13")
    applicant = _user("candidate8")
    team = _team("November", owner, game)
    TeamJoinRequest.objects.create(team=team, user=applicant, status=TeamJoinRequest.Status.PENDING)
    client.force_login(applicant)

    response = client.post(
        f"/api/vnext/teams/{team.slug}/training/tryouts/",
        data=json.dumps({"ign": "Candidate#BD"}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "active join request" in response.json()["error"]


def test_send_tryout_offer_creates_join_request_without_membership():
    game = _game()
    owner = _user("owner14")
    applicant = _user("candidate9")
    team = _team("Oscar", owner, game)
    app = TeamTrainingService.apply_for_tryout(
        team=team,
        applicant=applicant,
        ign="Candidate",
        preferred_role="Entry",
    )

    join_request, updated = TeamTrainingService.move_tryout_to_join_pipeline(
        application=app,
        actor=owner,
        notes="Strong comms.",
    )

    assert join_request.status == TeamJoinRequest.Status.OFFER_SENT
    assert join_request.applied_position == "Entry"
    assert updated.status == TryoutApplication.Status.ACCEPTED
    assert updated.join_request == join_request
    assert not team.vnext_memberships.filter(user=applicant, status=MembershipStatus.ACTIVE).exists()


def test_send_tryout_offer_links_existing_join_request_idempotently():
    game = _game()
    owner = _user("owner15")
    applicant = _user("candidate10")
    team = _team("Papa", owner, game)
    app = TeamTrainingService.apply_for_tryout(team=team, applicant=applicant, preferred_role="Support")
    existing = TeamJoinRequest.objects.create(
        team=team,
        user=applicant,
        status=TeamJoinRequest.Status.PENDING,
        message="General application.",
    )

    first_join_request, updated = TeamTrainingService.move_tryout_to_join_pipeline(application=app, actor=owner)
    second_join_request, _ = TeamTrainingService.move_tryout_to_join_pipeline(application=updated, actor=owner)

    assert first_join_request == existing
    assert second_join_request == existing
    assert TeamJoinRequest.objects.filter(team=team, user=applicant).count() == 1
    existing.refresh_from_db()
    assert existing.status == TeamJoinRequest.Status.OFFER_SENT


def test_unauthorized_user_cannot_send_tryout_offer():
    game = _game()
    owner = _user("owner16")
    applicant = _user("candidate11")
    outsider = _user("outsider2")
    team = _team("Quebec", owner, game)
    app = TeamTrainingService.apply_for_tryout(team=team, applicant=applicant)

    with pytest.raises(PermissionDenied):
        TeamTrainingService.move_tryout_to_join_pipeline(application=app, actor=outsider)


def test_send_tryout_offer_api_returns_join_pipeline_status(client):
    game = _game()
    owner = _user("owner17")
    applicant = _user("candidate12")
    team = _team("Romeo", owner, game)
    app = TeamTrainingService.apply_for_tryout(team=team, applicant=applicant)
    client.force_login(owner)

    response = client.post(
        f"/api/vnext/teams/{team.slug}/training/tryouts/{app.pk}/offer/",
        data=json.dumps({"notes": "Ready for roster offer."}),
        content_type="application/json",
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["join_request"]["status"] == TeamJoinRequest.Status.OFFER_SENT
    assert payload["tryout"]["join_request_id"] == payload["join_request"]["id"]
    assert not team.vnext_memberships.filter(user=applicant, status=MembershipStatus.ACTIVE).exists()


def test_applicant_context_shows_offer_after_tryout_bridge():
    game = _game()
    owner = _user("owner18")
    applicant = _user("candidate13")
    team = _team("Sierra", owner, game)
    team.is_recruiting = True
    team.save(update_fields=["is_recruiting"])
    RecruitmentPosition.objects.create(team=team, title="Flex")
    app = TeamTrainingService.apply_for_tryout(team=team, applicant=applicant)
    TeamTrainingService.move_tryout_to_join_pipeline(application=app, actor=owner)

    context = get_team_detail_context(team_slug=team.slug, viewer=applicant)

    assert context["training"]["applicant_status"]["title"] == "Offer Sent"
    assert context["training"]["applicant_status"]["kind"] == "tryout"


def test_applicant_accepts_offer_and_membership_created_once(client):
    game = _game()
    owner = _user("owner19")
    applicant = _user("candidate14")
    team = _team("Tango", owner, game)
    app = TeamTrainingService.apply_for_tryout(team=team, applicant=applicant)
    join_request, _ = TeamTrainingService.move_tryout_to_join_pipeline(application=app, actor=owner)
    client.force_login(applicant)

    response = client.post(
        f"/api/vnext/teams/{team.slug}/apply/offers/{join_request.pk}/",
        data=json.dumps({"action": "accept"}),
        content_type="application/json",
    )
    duplicate = client.post(
        f"/api/vnext/teams/{team.slug}/apply/offers/{join_request.pk}/",
        data=json.dumps({"action": "accept"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert duplicate.status_code == 400
    join_request.refresh_from_db()
    app.refresh_from_db()
    assert join_request.status == TeamJoinRequest.Status.ACCEPTED
    assert app.status == TryoutApplication.Status.ACCEPTED
    assert team.vnext_memberships.filter(user=applicant, status=MembershipStatus.ACTIVE).count() == 1


def test_applicant_declines_offer_without_membership(client):
    game = _game()
    owner = _user("owner20")
    applicant = _user("candidate15")
    team = _team("Uniform", owner, game)
    app = TeamTrainingService.apply_for_tryout(team=team, applicant=applicant)
    join_request, _ = TeamTrainingService.move_tryout_to_join_pipeline(application=app, actor=owner)
    client.force_login(applicant)

    response = client.post(
        f"/api/vnext/teams/{team.slug}/apply/offers/{join_request.pk}/",
        data=json.dumps({"action": "decline"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    join_request.refresh_from_db()
    app.refresh_from_db()
    assert join_request.status == TeamJoinRequest.Status.DECLINED
    assert app.status == TryoutApplication.Status.REJECTED
    assert not team.vnext_memberships.filter(user=applicant, status=MembershipStatus.ACTIVE).exists()


def test_unrelated_user_cannot_accept_offer(client):
    game = _game()
    owner = _user("owner21")
    applicant = _user("candidate16")
    outsider = _user("outsider3")
    team = _team("Victor", owner, game)
    app = TeamTrainingService.apply_for_tryout(team=team, applicant=applicant)
    join_request, _ = TeamTrainingService.move_tryout_to_join_pipeline(application=app, actor=owner)
    client.force_login(outsider)

    response = client.post(
        f"/api/vnext/teams/{team.slug}/apply/offers/{join_request.pk}/",
        data=json.dumps({"action": "accept"}),
        content_type="application/json",
    )

    assert response.status_code == 404
    assert not team.vnext_memberships.filter(user=outsider, status=MembershipStatus.ACTIVE).exists()


def test_manager_cannot_sign_offer_without_applicant_acceptance(client):
    game = _game()
    owner = _user("owner22")
    applicant = _user("candidate17")
    team = _team("Whiskey", owner, game)
    app = TeamTrainingService.apply_for_tryout(team=team, applicant=applicant)
    join_request, _ = TeamTrainingService.move_tryout_to_join_pipeline(application=app, actor=owner)
    client.force_login(owner)

    response = client.post(
        f"/api/vnext/teams/{team.slug}/join-requests/{join_request.pk}/tryout/advance/",
        data=json.dumps({}),
        content_type="application/json",
    )

    assert response.status_code == 400
    join_request.refresh_from_db()
    assert join_request.status == TeamJoinRequest.Status.OFFER_SENT
    assert not team.vnext_memberships.filter(user=applicant, status=MembershipStatus.ACTIVE).exists()


def test_my_team_applications_endpoint_returns_own_history(client):
    game = _game()
    owner = _user("owner23")
    applicant = _user("candidate18")
    team = _team("Xray", owner, game)
    app = TeamTrainingService.apply_for_tryout(
        team=team,
        applicant=applicant,
        ign="Candidate#18",
        preferred_role="Flex",
        notes="Applicant-visible note.",
    )
    session = TeamTrainingService.schedule_tryout_session(
        application=app,
        actor=owner,
        scheduled_at=timezone.now() + timedelta(days=3),
        format="BO3 role test",
        room_details="Private lobby details.",
    )
    join_request, _ = TeamTrainingService.move_tryout_to_join_pipeline(application=app, actor=owner)
    client.force_login(applicant)

    response = client.get("/api/vnext/me/team-applications/")
    payload = response.json()

    assert response.status_code == 200
    assert payload["count"] == 1
    item = payload["results"][0]
    assert item["source_type"] == "tryout"
    assert item["team_name"] == team.name
    assert item["role"] == "Flex"
    assert item["status"] == "Offer Sent"
    assert item["scheduled_at"] == session.scheduled_at.isoformat()
    assert item["session"]["format"] == "BO3 role test"
    assert item["action_label"] == "Accept Offer"
    assert item["action_url"] == f"/api/vnext/teams/{team.slug}/apply/offers/{join_request.pk}/"
    assert "room_details" not in item["session"]
    assert "review_notes" not in item


def test_my_team_applications_endpoint_excludes_other_users(client):
    game = _game()
    owner = _user("owner24")
    applicant = _user("candidate19")
    outsider = _user("outsider4")
    team = _team("Yankee", owner, game)
    TeamTrainingService.apply_for_tryout(team=team, applicant=applicant, preferred_role="Duelist")
    client.force_login(outsider)

    response = client.get("/api/vnext/me/team-applications/")
    payload = response.json()

    assert response.status_code == 200
    assert payload["count"] == 0
    assert payload["results"] == []


def test_my_team_applications_join_request_offer_actions_only_for_offer_sent(client):
    game = _game()
    owner = _user("owner25")
    applicant = _user("candidate20")
    team = _team("Zulu", owner, game)
    offer = TeamJoinRequest.objects.create(
        team=team,
        user=applicant,
        status=TeamJoinRequest.Status.OFFER_SENT,
        applied_position="Support",
        message="General join request.",
    )
    accepted = TeamJoinRequest.objects.create(
        team=team,
        user=applicant,
        status=TeamJoinRequest.Status.ACCEPTED,
        applied_position="Entry",
    )
    client.force_login(applicant)

    response = client.get("/api/vnext/me/team-applications/")
    results = response.json()["results"]
    by_request_id = {item["join_request_id"]: item for item in results}

    assert response.status_code == 200
    assert by_request_id[offer.pk]["status"] == "Offer Sent"
    assert [action["action"] for action in by_request_id[offer.pk]["actions"]] == ["accept", "decline"]
    assert by_request_id[accepted.pk]["status"] == "Accepted / Signed"
    assert by_request_id[accepted.pk]["actions"] == []
