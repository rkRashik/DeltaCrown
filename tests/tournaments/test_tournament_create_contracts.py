"""Regression tests for tournament create contracts.

These tests focus on API/view contracts and avoid database setup so they can
run in smoke mode on machines without Docker test DB services.
"""

from types import SimpleNamespace
from contextlib import nullcontext
from unittest.mock import Mock, patch

from django.test import RequestFactory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.tournaments.api.tournament_views import TournamentViewSet
from apps.tournaments.views.create import TournamentCreatePageView


def _payload():
    return {
        "name": "Contract Cup",
        "description": "Contract test tournament",
        "game_id": 99,
        "format": "single_elimination",
        "participation_type": "team",
        "max_participants": 16,
        "min_participants": 4,
        "registration_start": "2030-03-01T10:00:00Z",
        "registration_end": "2030-03-02T10:00:00Z",
        "tournament_start": "2030-03-03T10:00:00Z",
    }


def _user(**overrides):
    base = {
        "pk": 1,
        "is_authenticated": True,
        "is_staff": False,
        "is_superuser": False,
        "username": "contract_user",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class TestTournamentCreateApiContracts:
    def test_create_requires_authentication(self):
        request = APIRequestFactory().post(
            reverse("tournaments_api:tournament-list"),
            _payload(),
            format="json",
        )
        response = TournamentViewSet.as_view({"post": "create"})(request)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "not provided" in str(response.data.get("error", "")).lower()

    def test_create_returns_402_when_balance_is_insufficient(self):
        request = APIRequestFactory().post(
            reverse("tournaments_api:tournament-list"),
            _payload(),
            format="json",
        )
        force_authenticate(request, user=_user())

        serializer = Mock()
        serializer.is_valid.return_value = True

        with (
            patch(
                "apps.tournaments.api.tournament_views.TournamentViewSet.get_serializer",
                return_value=serializer,
            ),
            patch("apps.tournaments.api.tournament_views.get_hosting_fee", return_value=500),
            patch("apps.tournaments.api.tournament_views.get_user_balance", return_value=125),
        ):
            response = TournamentViewSet.as_view({"post": "create"})(request)

        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert response.data["error"] == "INSUFFICIENT_DELTACOIN"
        assert response.data["hosting_fee"] == 500
        assert response.data["balance"] == 125
        serializer.save.assert_not_called()

    def test_staff_create_returns_redirect_contract(self):
        request = APIRequestFactory().post(
            reverse("tournaments_api:tournament-list"),
            _payload(),
            format="json",
        )
        staff_user = _user(is_staff=True, username="contract_staff")
        force_authenticate(request, user=staff_user)

        tournament_obj = SimpleNamespace(id=101, slug="contract-cup-staff")
        serializer = Mock()
        serializer.is_valid.return_value = True
        serializer.save.return_value = tournament_obj

        with (
            patch(
                "apps.tournaments.api.tournament_views.TournamentViewSet.get_serializer",
                return_value=serializer,
            ),
            patch(
                "apps.tournaments.api.tournament_views.get_user_balance",
                return_value=777,
            ),
            patch(
                "apps.tournaments.api.tournament_views.charge_hosting_fee",
                return_value=None,
            ) as charge_mock,
            patch(
                "apps.tournaments.api.tournament_views.transaction.atomic",
                return_value=nullcontext(),
            ),
            patch(
                "apps.tournaments.api.tournament_views.TournamentDetailSerializer"
            ) as detail_serializer_cls,
        ):
            detail_serializer_cls.return_value.data = {
                "id": 101,
                "slug": "contract-cup-staff",
                "name": "Contract Cup Staff Success",
            }
            response = TournamentViewSet.as_view({"post": "create"})(request)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["message"] == "Tournament created successfully"
        assert response.data["hosting_fee_charged"] == 0
        assert response.data["balance_after"] == 777
        assert response.data["redirect_url"] == "/toc/contract-cup-staff/?onboarding=true"
        assert response.data["tournament"]["id"] == 101

        charge_mock.assert_called_once_with(staff_user, tournament_obj)
        serializer.save.assert_called_once()


class TestTournamentCreatePageContracts:
    def test_create_page_context_uses_namespaced_api_list_url(self):
        request = RequestFactory().get(reverse("tournaments:create"))
        request.user = _user()

        games_qs = Mock(name="games_qs")
        games_qs.select_related.return_value = games_qs
        games_qs.order_by.return_value = games_qs
        game_manager = Mock()
        game_manager.filter.return_value = games_qs

        with (
            patch("apps.tournaments.views.create.Game.objects", game_manager),
            patch(
                "apps.tournaments.views.create.build_game_intelligence_payload",
                return_value=[],
            ),
            patch("apps.tournaments.views.create.get_hosting_fee", return_value=500),
            patch("apps.tournaments.views.create.get_user_balance", return_value=200),
        ):
            view = TournamentCreatePageView()
            view.setup(request)
            context = view.get_context_data()

        assert context["api_create_url"] == reverse("tournaments_api:tournament-list")
        assert context["after_balance"] == 0
        assert context["can_afford"] is False