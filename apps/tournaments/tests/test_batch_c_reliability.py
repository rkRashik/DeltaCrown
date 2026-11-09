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


class StandingsIntegrityTests(CompletedTournamentFixtureMixin, TestCase):
    """The public page must never show a placement it cannot tie to a real registration or to the recorded result."""

    def _standings(self, final_standings, **result_kwargs):
        tournament, regs = self.make_completed(slug=f"batch-c-integrity-{len(result_kwargs)}-{id(final_standings) % 9973}")
        TournamentResult.objects.create(tournament=tournament, winner=regs[0], runner_up=regs[1],
                                        rules_applied={"determination": "test"}, final_standings=final_standings(regs),
                                        **result_kwargs)
        context = self.client.get(f"/tournaments/{tournament.slug}/results/").context
        return context["standings"], context["unplaced_participants"], regs

    @staticmethod
    def _row(placement, reg, **extra):
        return {"placement": placement, "registration_id": reg.id, "team_name": f"Team {reg.id}",
                "is_tied": False, "tied_with": [], **extra}

    def test_malformed_unknown_and_duplicate_rows_are_dropped(self):
        standings, unplaced, regs = self._standings(lambda r: [
            "garbage", None, 7,
            {"placement": "first", "registration_id": r[0].id},
            {"placement": True, "registration_id": r[0].id},
            {"placement": 0, "registration_id": r[0].id},
            {"placement": 1, "registration_id": 999999, "team_name": "Ghost"},
            self._row(1, r[0]),
            self._row(2, r[0]),            # same registration twice: first one wins
            self._row("2", r[1]),          # numeric string is accepted
        ])
        self.assertEqual([(s["placement"], s["name"]) for s in standings], [(1, f"Team {regs[0].id}"), (2, f"Team {regs[1].id}")])
        self.assertNotIn("Ghost", [s["name"] for s in standings])

    def test_non_list_standings_do_not_break_the_page(self):
        standings, unplaced, regs = self._standings(lambda r: {"placement": 1})
        self.assertEqual(standings, [])
        self.assertEqual(len(unplaced), 4)

    def test_duplicate_placement_needs_a_tie_flag(self):
        standings, _, regs = self._standings(lambda r: [self._row(1, r[0]), self._row(2, r[1]), self._row(2, r[2])])
        self.assertEqual([s["placement"] for s in standings], [1])  # ambiguous 2nd place is not official

    def test_flagged_tie_is_shown(self):
        standings, _, regs = self._standings(lambda r: [
            self._row(1, r[0]), self._row(2, r[1], is_tied=True, tied_with=[r[2].id]),
            self._row(2, r[2], is_tied=True, tied_with=[r[1].id])])
        self.assertEqual([(s["placement"], s["is_tied"]) for s in standings], [(1, False), (2, True), (2, True)])

    def test_standings_contradicting_the_recorded_winner_are_not_shown(self):
        standings, unplaced, regs = self._standings(lambda r: [self._row(1, r[2]), self._row(2, r[1])])
        self.assertEqual(standings, [])
        self.assertEqual(len(unplaced), 4)

    def test_other_participants_are_confirmed_registrations_only(self):
        tournament, regs = self.make_completed(slug="batch-c-integrity-status")
        Registration.objects.filter(pk=regs[3].pk).update(status=Registration.CANCELLED)
        Registration.objects.filter(pk=regs[2].pk).update(status=Registration.REJECTED)
        TournamentResult.objects.create(tournament=tournament, winner=regs[0], runner_up=regs[1],
                                        rules_applied={"determination": "test"},
                                        final_standings=[self._row(1, regs[0]), self._row(2, regs[1])])
        context = self.client.get(f"/tournaments/{tournament.slug}/results/").context
        self.assertEqual(context["unplaced_participants"], [])


class PublicDetailPresentationTests(CompletedTournamentFixtureMixin, TestCase):
    def test_completed_page_offers_results_and_says_completed(self):
        tournament, _ = self.make_completed(slug="batch-c-cta-done")
        html = self.client.get(f"/tournaments/{tournament.slug}/").content.decode()
        self.assertIn("Tournament completed", html)
        self.assertIn(f'href="/tournaments/{tournament.slug}/results/"', html)
        self.assertIn("View results", html)

    def test_cancelled_page_says_cancelled_not_registration_closed(self):
        tournament, _ = self.make_completed(slug="batch-c-cta-cancel")
        Tournament.objects.filter(pk=tournament.pk).update(status=Tournament.CANCELLED)
        html = self.client.get(f"/tournaments/{tournament.slug}/").content.decode()
        self.assertIn("Tournament cancelled", html)

    def test_hero_has_no_fake_brand_image_and_no_placeholder_chips(self):
        tournament, _ = self.make_completed(slug="batch-c-hero")
        html = self.client.get(f"/tournaments/{tournament.slug}/").content.decode()
        self.assertNotRegex(html, r"<img[^>]+og-preview")
        for jargon in ("Live Updates Enabled", "Community Links Active", "Tournament Runtime", "Recent activity", "Vanguard Network"):
            self.assertNotIn(jargon, html)

    def test_entry_fee_uses_one_currency_format(self):
        tournament, _ = self.make_completed(slug="batch-c-fee")
        Tournament.objects.filter(pk=tournament.pk).update(
            status=Tournament.REGISTRATION_OPEN, has_entry_fee=True, entry_fee_amount=150, entry_fee_currency="BDT")
        html = self.client.get(f"/tournaments/{tournament.slug}/").content.decode()
        self.assertIn("৳150", html)
        self.assertNotIn("BDT 150", html)

    def test_poll_widget_cannot_be_unhidden_by_a_style_binding(self):
        """A string :style binding replaces the whole style attribute and defeats x-show (the placeholder poll stayed visible)."""
        from pathlib import Path
        from django.conf import settings
        stack = (Path(settings.BASE_DIR) / "templates/tournaments/detailPages/widgets/_overview_widget_stack.html").read_text(encoding="utf-8")
        section = stack[stack.index('id="fan-predictions"'):][:600]
        self.assertIn('x-show="shouldShowFanPoll()"', section)
        self.assertNotRegex(section, r""":style="[^"]*\? *'[^']*' *: *''""")
        methods = (Path(settings.BASE_DIR) / "templates/tournaments/detailPages/widgets/_widget_methods.js.html").read_text(encoding="utf-8")
        self.assertIn("fanPollIsConfigured", methods)

    def test_tournament_page_family_uses_the_shared_scope(self):
        from pathlib import Path
        from django.conf import settings
        css = (Path(settings.BASE_DIR) / "static/ownlobby/foundation.css").read_text(encoding="utf-8")
        self.assertIn(".ol-tourney", css)
        tournament, _ = self.make_completed(slug="batch-c-scope")
        self.assertIn("ol-tourney", self.client.get(f"/tournaments/{tournament.slug}/").content.decode())

    def test_registration_confirmation_copy_has_no_invented_tiers_or_neon_cta(self):
        from pathlib import Path
        from django.conf import settings
        tpl = (Path(settings.BASE_DIR) / "templates/tournaments/registration/smart_success.html").read_text(encoding="utf-8")
        for phrase in ("VIP Access Secured", "Access Tier", "CONTENDERS", "CHALLENGER", "Servers</span>", "Tournament Ops", "neonPulse;", "animation: neonPulse"):
            self.assertNotIn(phrase, tpl)
        self.assertIn("Registration confirmed", tpl)

    def test_featured_hero_shows_the_real_status(self):
        """The featured hero/carousel read t.effective_status; it was only set for the paginated cards, so an open
        tournament was labelled 'Upcoming'/'Closed' on the list page while its detail page said 'Registration open'."""
        cache.clear()
        tournament, _ = self.make_completed(slug="batch-c-featured")
        Tournament.objects.filter(pk=tournament.pk).update(
            status=Tournament.REGISTRATION_OPEN, is_featured=True,
            registration_start=timezone.now() - timedelta(days=1), registration_end=timezone.now() + timedelta(days=2))
        html = self.client.get("/tournaments/").content.decode()
        self.assertIn("Registration open", html)
