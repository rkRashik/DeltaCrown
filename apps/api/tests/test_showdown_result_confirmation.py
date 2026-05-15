import pytest
from rest_framework.test import APIClient

from apps.competition.models import Challenge, ChallengeResultSubmission
from apps.competition.services import ChallengeService
from apps.organizations.choices import MembershipRole
from apps.organizations.tests.factories import (
    GameFactory,
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def game():
    return GameFactory(short_code="SDR", slug="showdown-result")


@pytest.fixture
def showdown(game):
    challenger_user = UserFactory()
    challenged_user = UserFactory()
    challenger = TeamFactory(game_id=game.id)
    challenged = TeamFactory(game_id=game.id)
    TeamMembershipFactory(team=challenger, user=challenger_user, role=MembershipRole.MANAGER)
    TeamMembershipFactory(team=challenged, user=challenged_user, role=MembershipRole.MANAGER)
    challenge = Challenge.objects.create(
        challenger_team=challenger,
        challenged_team=challenged,
        game=game,
        title="Final Score Check",
        status="ACCEPTED",
        created_by=challenger_user,
        accepted_by=challenged_user,
        entry_fee_dc=0,
    )
    return challenge, challenger_user, challenged_user


def auth(client, user):
    client.force_authenticate(user=user)
    return client


def result_url(challenge):
    return f"/api/v1/challenges/{challenge.id}/result/"


def payload(team_id, result="CHALLENGER_WIN", challenger=2, challenged=1):
    return {
        "submitting_team_id": team_id,
        "result": result,
        "score_details": {"challenger": challenger, "challenged": challenged},
        "evidence_url": "",
    }


@pytest.mark.django_db
def test_authorized_manager_can_submit_showdown_result(api_client, showdown):
    challenge, challenger_user, _ = showdown

    response = auth(api_client, challenger_user).post(
        result_url(challenge),
        payload(challenge.challenger_team_id),
        format="json",
    )

    assert response.status_code == 200
    challenge.refresh_from_db()
    assert challenge.status == "PENDING_CONFIRMATION"
    assert ChallengeResultSubmission.objects.filter(challenge=challenge).count() == 1


@pytest.mark.django_db
def test_unauthorized_user_cannot_submit_showdown_result(api_client, showdown):
    challenge, _, _ = showdown
    outsider = UserFactory()

    response = auth(api_client, outsider).post(
        result_url(challenge),
        payload(challenge.challenger_team_id),
        format="json",
    )

    assert response.status_code == 403
    assert ChallengeResultSubmission.objects.filter(challenge=challenge).count() == 0


@pytest.mark.django_db
def test_matching_result_confirmation_settles_once(api_client, showdown):
    challenge, challenger_user, challenged_user = showdown

    first = auth(api_client, challenger_user).post(
        result_url(challenge),
        payload(challenge.challenger_team_id),
        format="json",
    )
    second = auth(api_client, challenged_user).post(
        result_url(challenge),
        payload(challenge.challenged_team_id),
        format="json",
    )

    assert first.status_code == 200
    assert second.status_code == 200
    challenge.refresh_from_db()
    assert challenge.status == "SETTLED"
    assert challenge.result == "CHALLENGER_WIN"
    assert ChallengeResultSubmission.objects.filter(challenge=challenge).count() == 2


@pytest.mark.django_db
def test_conflicting_result_marks_showdown_under_review(api_client, showdown):
    challenge, challenger_user, challenged_user = showdown

    auth(api_client, challenger_user).post(
        result_url(challenge),
        payload(challenge.challenger_team_id, result="CHALLENGER_WIN"),
        format="json",
    )
    response = auth(api_client, challenged_user).post(
        result_url(challenge),
        payload(challenge.challenged_team_id, result="CHALLENGED_WIN"),
        format="json",
    )

    assert response.status_code == 200
    challenge.refresh_from_db()
    assert challenge.status == "DISPUTED"


@pytest.mark.django_db
def test_duplicate_submit_is_idempotent_for_same_payload(api_client, showdown):
    challenge, challenger_user, _ = showdown
    body = payload(challenge.challenger_team_id)

    first = auth(api_client, challenger_user).post(result_url(challenge), body, format="json")
    second = auth(api_client, challenger_user).post(result_url(challenge), body, format="json")

    assert first.status_code == 200
    assert second.status_code == 200
    assert ChallengeResultSubmission.objects.filter(challenge=challenge).count() == 1


@pytest.mark.django_db
def test_matching_confirmation_calls_service_settlement(monkeypatch, api_client, showdown):
    challenge, challenger_user, challenged_user = showdown
    calls = []
    real_settle = ChallengeService.settle_challenge

    def spy_settle(*, challenge_id, settled_by=None):
        calls.append((challenge_id, settled_by))
        return real_settle(challenge_id=challenge_id, settled_by=settled_by)

    monkeypatch.setattr(ChallengeService, "settle_challenge", staticmethod(spy_settle))

    auth(api_client, challenger_user).post(
        result_url(challenge),
        payload(challenge.challenger_team_id),
        format="json",
    )
    auth(api_client, challenged_user).post(
        result_url(challenge),
        payload(challenge.challenged_team_id),
        format="json",
    )

    assert len(calls) == 1
    assert calls[0][0] == challenge.id
