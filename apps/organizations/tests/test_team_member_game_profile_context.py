from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore
from django.core.cache import cache
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.http import HttpResponse
from unittest.mock import patch

from apps.organizations.choices import MembershipRole
from apps.organizations.services.team_detail_context import (
    _build_roster_context,
    get_team_detail_context,
)
from apps.organizations.tests.factories import (
    GameFactory,
    TeamFactory,
    TeamMembershipFactory,
    UserFactory,
)
from apps.organizations.views.team import team_manage
from apps.user_profile.models import GameProfile


class TeamMemberGameProfileContextTests(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.game = GameFactory(name="Roster Context Game")
        self.other_game = GameFactory(name="Other Roster Game")
        self.owner = UserFactory(username="gpctx_owner")
        self.member = UserFactory(username="gpctx_member")
        self.team = TeamFactory.create_independent(
            created_by=self.owner,
            game_id=self.game.id,
            name="Game Profile Context Team",
            visibility="PUBLIC",
        )
        TeamMembershipFactory(team=self.team, user=self.owner, role=MembershipRole.OWNER)
        TeamMembershipFactory(team=self.team, user=self.member, role=MembershipRole.PLAYER)

    def _passport(self, user, game, **kwargs):
        defaults = {
            "ign": f"{user.username}_{game.slug}",
            "discriminator": "",
            "platform": "PC",
            "rank_name": "Diamond",
            "main_role": "Duelist",
            "region": "SA",
            "visibility": GameProfile.VISIBILITY_PUBLIC,
            "verification_status": GameProfile.VERIFICATION_VERIFIED,
        }
        defaults.update(kwargs)
        return GameProfile.objects.create(user=user, game=game, **defaults)

    def _request(self, user, path="/teams/game-profile-context-team/manage/"):
        request = self.factory.get(path)
        request.user = user
        request.session = SessionStore()
        request._messages = FallbackStorage(request)
        return request

    def _render_response(self, request, template, context):
        response = HttpResponse("ok")
        response.context_data = context
        return response

    def _roster_item_for(self, context, user):
        return next(
            item for item in context["roster"]["items"]
            if item["user_id"] == user.id
        )

    def test_team_detail_uses_game_profile_for_team_game(self):
        self._passport(self.member, self.game, ign="TeamGameIGN", rank_name="Ascendant")

        context = get_team_detail_context(team_slug=self.team.slug, viewer=None)
        item = self._roster_item_for(context, self.member)

        self.assertEqual(item["game_passport"]["game_id"], self.game.id)
        self.assertEqual(item["game_passport"]["ign"], "TeamGameIGN")
        self.assertEqual(item["game_passport"]["rank"], "Ascendant")

    def test_team_detail_ignores_other_game_profiles(self):
        self._passport(self.member, self.other_game, ign="WrongGameIGN")
        self._passport(self.member, self.game, ign="CorrectGameIGN")

        context = get_team_detail_context(team_slug=self.team.slug, viewer=None)
        item = self._roster_item_for(context, self.member)

        self.assertEqual(item["game_passport"]["game_id"], self.game.id)
        self.assertEqual(item["game_passport"]["ign"], "CorrectGameIGN")

    def test_missing_or_private_game_profile_returns_safe_fallback(self):
        private_user = UserFactory(username="gpctx_private")
        missing_user = UserFactory(username="gpctx_missing")
        TeamMembershipFactory(team=self.team, user=private_user, role=MembershipRole.PLAYER)
        TeamMembershipFactory(team=self.team, user=missing_user, role=MembershipRole.PLAYER)
        self._passport(
            private_user,
            self.game,
            ign="PrivateIGN",
            visibility=GameProfile.VISIBILITY_PRIVATE,
        )

        context = get_team_detail_context(team_slug=self.team.slug, viewer=None)

        self.assertEqual(self._roster_item_for(context, private_user)["game_passport"], {})
        self.assertEqual(self._roster_item_for(context, missing_user)["game_passport"], {})

    def test_public_team_detail_does_not_expose_sensitive_passport_data(self):
        self._passport(
            self.member,
            self.game,
            ign="SafeIGN",
            metadata={"secret_note": "do-not-leak"},
            provider_data={"riot": {"puuid": "secret-puuid"}},
            preferences={"private_pref": "hidden"},
        )

        context = get_team_detail_context(team_slug=self.team.slug, viewer=None)
        passport = self._roster_item_for(context, self.member)["game_passport"]

        self.assertEqual(passport["ign"], "SafeIGN")
        self.assertNotIn("metadata", passport)
        self.assertNotIn("provider_data", passport)
        self.assertNotIn("preferences", passport)

    def test_team_manage_uses_team_game_profile(self):
        self._passport(self.member, self.other_game, ign="ManageWrongIGN")
        self._passport(
            self.member,
            self.game,
            ign="ManageCorrect",
            discriminator="TAG",
            rank_name="Immortal",
        )

        with patch("apps.organizations.views.team.render", side_effect=self._render_response):
            response = team_manage(self._request(self.owner), team_slug=self.team.slug)

        member = next(m for m in response.context_data["members"] if m.user_id == self.member.id)
        self.assertEqual(member.gp_in_game_name, "ManageCorrect#TAG")
        self.assertEqual(member.gp_rank_name, "Immortal")
        self.assertEqual(member.game_profile["game_id"], self.game.id)
        self.assertNotEqual(member.game_profile["ign"], "ManageWrongIGN")

    def test_roster_context_batches_game_profile_lookup(self):
        users = [UserFactory(username=f"gpctx_batch_{idx}") for idx in range(3)]
        for idx, user in enumerate(users):
            TeamMembershipFactory(team=self.team, user=user, role=MembershipRole.PLAYER)
            self._passport(user, self.game, ign=f"Batch{idx}")

        with CaptureQueriesContext(connection) as queries:
            context = _build_roster_context(self.team, is_restricted=False)

        self.assertGreaterEqual(context["count"], 5)
        # Expected fixed categories: active memberships, team-game passports,
        # and starting lineup size. This guards against per-member passport queries.
        self.assertLessEqual(len(queries.captured_queries), 3)
