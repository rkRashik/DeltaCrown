"""Batch C1 regressions: completed-tournament page stability and canonical final standings."""
import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.tournaments.models import Game, Registration, Tournament, TournamentResult
from apps.user_profile.models import UserProfile

User = get_user_model()


class CompletedTournamentFixtureMixin:
    def _user(self, name):
        user = User.objects.create_user(username=name, email=f"{name}@example.test", password="pw-12345-x")
        UserProfile.objects.get_or_create(user=user)
        return user

    def make_completed(self, slug="batch-c-cup"):
        organizer = self._user(f"{slug}-org")
        game = Game.objects.create(name="Batch C Game", slug=f"game-{slug}")
        now = timezone.now()
        tournament = Tournament.objects.create(
            name="Batch C Cup", slug=slug, game=game, organizer=organizer, status=Tournament.COMPLETED,
            participation_type=Tournament.SOLO, max_participants=8, min_participants=2,
            registration_start=now - timedelta(days=8), registration_end=now - timedelta(days=5),
            tournament_start=now - timedelta(days=4), tournament_end=now - timedelta(days=3),
            published_at=now - timedelta(days=9),
        )
        regs = [Registration.objects.create(tournament=tournament, user=self._user(f"{slug}-p{i}"),
                                            status=Registration.CONFIRMED, registration_data={"game_id": f"p{i}"})
                for i in range(1, 5)]
        return tournament, regs


class CompletedDetailCspTests(CompletedTournamentFixtureMixin, TestCase):
    """Root cause of the intermittent Alpine `detailPage()` failure: the anonymous completed-tournament page was
    cached for an hour with the original request's CSP nonce, while every cache hit carried a fresh nonce in the
    Content-Security-Policy header, so the browser blocked all inline scripts."""

    def setUp(self):
        cache.clear()

    def test_csp_header_nonce_matches_inline_script_nonce_on_every_request(self):
        tournament, _ = self.make_completed()
        url = f"/tournaments/{tournament.slug}/"
        nonces = []
        for _ in range(3):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            header = response["Content-Security-Policy"]
            header_nonce = re.search(r"'nonce-([^']+)'", header).group(1)
            body = response.content.decode()
            body_nonces = set(re.findall(r'<script[^>]*\snonce="([^"]+)"', body))
            self.assertTrue(body_nonces, "page should contain nonce'd inline scripts")
            self.assertEqual(body_nonces, {header_nonce})
            nonces.append(header_nonce)
        self.assertEqual(len(set(nonces)), 3, "each request must get its own nonce")

    def test_completed_detail_is_not_publicly_cacheable_for_an_hour(self):
        tournament, _ = self.make_completed(slug="batch-c-nocache")
        response = self.client.get(f"/tournaments/{tournament.slug}/")
        self.assertNotIn("max-age=3600", response.get("Cache-Control", ""))

    def test_detail_script_registers_the_alpine_component(self):
        tournament, _ = self.make_completed(slug="batch-c-alpine")
        body = self.client.get(f"/tournaments/{tournament.slug}/").content.decode()
        self.assertIn("Alpine.data('detailPage'", body)
        self.assertIn('x-data="detailPage()"', body)


class ResultsStandingsTests(CompletedTournamentFixtureMixin, TestCase):
    def _finalize(self, tournament, regs, standings):
        return TournamentResult.objects.create(
            tournament=tournament, winner=regs[0], runner_up=regs[1], rules_applied={"determination": "test"},
            final_standings=standings,
        )

    def test_final_standings_follow_recorded_placements_not_seed_order(self):
        tournament, regs = self.make_completed(slug="batch-c-standings")
        # Seeds deliberately disagree with the final result.
        for seed, reg in zip((4, 3, 2, 1), regs):
            reg.seed = seed
            reg.save(update_fields=["seed"])
        self._finalize(tournament, regs, [
            {"placement": 1, "registration_id": regs[0].id, "team_name": "Champion", "is_tied": False, "tied_with": []},
            {"placement": 2, "registration_id": regs[1].id, "team_name": "Runner Up", "is_tied": False, "tied_with": []},
        ])
        context = self.client.get(f"/tournaments/{tournament.slug}/results/").context
        self.assertEqual([(row["placement"], row["name"]) for row in context["standings"]],
                         [(1, "Champion"), (2, "Runner Up")])
        self.assertEqual(context["winner"].id, regs[0].id)  # podium and standings agree
        # participants without a recorded placement are never ranked
        self.assertEqual({p["name"] for p in context["unplaced_participants"]},
                         {regs[2].user.username, regs[3].user.username})

    def test_results_page_shows_unpublished_message_when_no_placements_exist(self):
        tournament, regs = self.make_completed(slug="batch-c-unpublished")
        TournamentResult.objects.create(tournament=tournament, winner=regs[0], rules_applied={"determination": "test"})
        response = self.client.get(f"/tournaments/{tournament.slug}/results/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertNotIn("Seed ", html)
        self.assertIn("Participants", html)
