"""Real ORM/template regressions on disposable PostgreSQL, never production.

The immutable pre-change view is loaded from Git for the before/after comparison.
CI must retain history (checkout fetch-depth: 0). No ORM/cache builder is stubbed
in measurements; timings describe synthetic QA only, not production latency.
"""
import ast
from copy import deepcopy
from datetime import datetime, timedelta, timezone as dt_timezone
import inspect
import json
import subprocess
from time import perf_counter
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.cache import cache
from django.db import connection
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from apps.games.models import Game
from apps.organizations.models import Team, TeamMembership
from apps.siteui import cache_safe, views
from apps.siteui.homepage_extras import get_homepage_extras
from apps.siteui.models import HomePageContent
from apps.tournaments.models import Registration, Tournament
from apps.user_profile.models import UserProfile


BASELINE_SHA = "f6a27d7cb3dc6f12938d30868f36bb187723d368"
NOW = datetime(2026, 10, 30, 6, 0, tzinfo=dt_timezone.utc)


def baseline_home():
    """Compile only the actual reviewed baseline home(), preserving its decorator."""
    source = subprocess.run(
        ["git", "show", f"{BASELINE_SHA}:apps/siteui/views.py"],
        cwd=settings.BASE_DIR, check=True, capture_output=True, encoding="utf-8",
    ).stdout
    function = next(node for node in ast.parse(source).body
                    if isinstance(node, ast.FunctionDef) and node.name == "home")
    namespace = dict(vars(views))
    exec(compile(ast.Module(body=[function], type_ignores=[]),
                 "<reviewed-baseline-home>", "exec"), namespace)
    return namespace["home"]


@override_settings(CACHES={"default": {
    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    "LOCATION": "ol04-b-homepage-regression",
}})
class HomepageContextRemovalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Fail closed even if someone supplies a different test settings module.
        if (connection.vendor != "postgresql"
                or connection.settings_dict["HOST"] not in {"localhost", "127.0.0.1", "::1"}
                or connection.settings_dict["NAME"] != "ownlobby_test"):
            raise RuntimeError("Homepage QA requires local disposable ownlobby_test PostgreSQL")
        User = get_user_model()
        cls.people = {}
        for role in ("player", "organizer", "registered", "manager"):
            user = User.objects.create_user(username=f"qa-{role}", email=f"{role}@example.invalid")
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.display_name = f"QA {role}"
            profile.save(update_fields=["display_name"])
            cls.people[role] = user.pk
        # Create the legacy singleton in fixture setup, outside request measures.
        HomePageContent.get_instance()

    def setUp(self):
        self.enterContext(patch("django.utils.timezone.now", return_value=NOW))
        # Only synthetic CSRF randomness is fixed; HTML is compared byte for byte.
        self.enterContext(patch("django.middleware.csrf._get_new_csrf_string", return_value="a" * 32))
        self.previous_cooldown = cache_safe._CACHE_FAIL_UNTIL_MONO
        self.addCleanup(setattr, cache_safe, "_CACHE_FAIL_UNTIL_MONO", self.previous_cooldown)
        cache_safe._CACHE_FAIL_UNTIL_MONO = 0.0
        cache.clear()
        self.addCleanup(cache.clear)
        self.before = baseline_home()
        self.fixture = "empty"

    def populate(self):
        self.fixture = "populated"
        # Remove seeded catalog data only within the disposable test transaction.
        Game.objects.all().delete()
        game = Game.objects.create(
            name="QA eFootball", display_name="QA eFootball", slug="efootball",
            short_code="QA-EF", category="SPORTS", game_type="1V1", is_active=True,
        )
        organizer = get_user_model().objects.get(pk=self.people["organizer"])
        for index in range(3):
            tournament = Tournament.objects.create(
                name=f"QA Cup {index}", slug=f"qa-cup-{index}", game=game,
                organizer=organizer, status=Tournament.REGISTRATION_OPEN,
                participation_type=Tournament.SOLO, max_participants=16, min_participants=2,
                registration_start=NOW - timedelta(days=1), registration_end=NOW + timedelta(days=1),
                tournament_start=NOW + timedelta(days=2 + index), prize_pool=1000,
            )
            if index == 0:
                Registration.objects.create(
                    tournament=tournament, user_id=self.people["registered"],
                    status=Registration.CONFIRMED, registration_data={"game_id": "qa-player"},
                )
        team = Team.objects.create(
            name="QA Team", slug="qa-team", created_by_id=self.people["manager"],
            game_id=game.pk, region="Bangladesh", status="ACTIVE",
        )
        TeamMembership.objects.create(
            team=team, user_id=self.people["manager"], role="MANAGER", status="ACTIVE",
        )

    def request(self, role="guest"):
        request = RequestFactory().get("/")
        request.user = (AnonymousUser() if role == "guest" else
                        get_user_model().objects.get(pk=self.people[role]))
        request.session = {}
        request._messages = FallbackStorage(request)
        request.META["CSRF_COOKIE"] = "a" * 32
        return request

    def measure(self, view, role="guest"):
        request = self.request(role)
        phases = {}
        sql_ms = 0.0
        context = {}
        original_timed, original_render = views._homepage_timed, views.render

        def execute(execute, sql, params, many, execution_context):
            nonlocal sql_ms
            started = perf_counter()
            try:
                return execute(sql, params, many, execution_context)
            finally:
                sql_ms += (perf_counter() - started) * 1000

        def timed(phase, callback):
            count, sql_before, started = len(queries), sql_ms, perf_counter()
            result = original_timed(phase, callback)
            phases[phase] = {"queries": len(queries) - count,
                             "sql_ms": round(sql_ms - sql_before, 3),
                             "wall_ms": round((perf_counter() - started) * 1000, 3)}
            return result

        def render(request, template, payload):
            context.update(payload)
            return original_render(request, template, payload)

        with CaptureQueriesContext(connection) as queries, connection.execute_wrapper(execute):
            with patch.dict(inspect.unwrap(view).__globals__, _homepage_timed=timed, render=render):
                response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("text/html", response["Content-Type"])
        return response.content, context, {"queries": len(queries), "sql_ms": round(sql_ms, 3), "phases": phases}

    def compare(self, role, cache_state):
        rows = []
        for label, view in (("before", self.before), ("after", views.home)):
            cache.clear()
            cache_safe._CACHE_FAIL_UNTIL_MONO = 0.0
            if cache_state == "warm":
                self.measure(view, role)
            html, context, metrics = self.measure(view, role)
            rows.append((html, context, metrics))
            print("OL04B_QA " + json.dumps({"role": role, "cache": cache_state,
                  "fixture": self.fixture, "revision": label,
                  "baseline": BASELINE_SHA, **metrics}, sort_keys=True))
        self.assertEqual(rows[0][0], rows[1][0], "Homepage HTML changed")
        for key in ("hero_ctx", "home_state", "seo", "v3", "home_ui"):
            self.assertEqual(rows[0][1][key], rows[1][1][key], key)
        self.assertNotIn("context", rows[1][2]["phases"])
        self.assertIn("context", rows[0][2]["phases"])
        before_count, after_count = rows[0][2]["queries"], rows[1][2]["queries"]
        if cache_state == "cold":
            self.assertGreater(before_count, after_count)
        else:
            self.assertEqual(before_count, after_count)
        self.assertIn(b'class="dc-home-m"', rows[1][0])
        self.assertIn(b'data-section="tournaments"', rows[1][0])
        self.assertIn(b'rel="canonical"', rows[1][0])
        return rows[1]

    def test_empty_guest_output_and_cold_warm_queries(self):
        Tournament.objects.all().delete()
        Game.objects.all().delete()
        for state in ("cold", "warm"):
            with self.subTest(cache=state):
                self.compare("guest", state)

    def test_populated_roles_output_and_cold_warm_queries(self):
        self.populate()
        for role, expected_mode in (("guest", "guest"), ("player", "no_team"),
                                    ("organizer", "organizer"), ("registered", "registered"),
                                    ("manager", "team_manager")):
            for state in ("cold", "warm"):
                with self.subTest(role=role, cache=state):
                    html, context, _ = self.compare(role, state)
                    self.assertEqual(context["hero_ctx"]["mode"], expected_mode)
                    self.assertIn(b"/static/img/games/posters/efootball.jpg", html)
                    self.assertIn(b"qa-cup-", html)

    def test_legacy_builder_and_singleton_are_never_invoked(self):
        with patch("apps.siteui.homepage_context.get_homepage_context", side_effect=AssertionError("legacy called")) as legacy:
            with patch.object(HomePageContent, "get_instance", side_effect=AssertionError("singleton called")):
                self.measure(views.home)
        legacy.assert_not_called()

    def test_cached_extras_object_is_never_personalized_or_mutated(self):
        self.populate()
        shared = get_homepage_extras()
        original = deepcopy(shared)
        with patch("apps.siteui.homepage_extras.get_homepage_extras", return_value=shared):
            for role, mode in (("registered", "registered"), ("organizer", "organizer"), ("guest", "guest")):
                _, context, _ = self.measure(views.home, role)
                self.assertEqual(context["hero_ctx"]["mode"], mode)
                self.assertEqual(shared, original)
                self.assertNotIn("hero_ctx", shared)
                self.assertNotIn("seo", shared)

    def test_safe_cache_get_timeout_preserves_baseline_output(self):
        self.populate()
        self.fixture = "populated-read-timeout"
        # Fail only the guarded homepage cache access. The separate common
        # processor has unguarded cache calls; a global outage is a separate risk.
        real_get = cache.get
        def timeout(key, default=None, **kwargs):
            if key in {"homepage_context_v2", "homepage_extras_v3"}:
                raise TimeoutError("synthetic Redis read timeout")
            return real_get(key, default, **kwargs)
        with patch.object(cache_safe.cache, "get", side_effect=timeout):
            self.compare("registered", "cold")

    def test_safe_cache_set_timeout_preserves_baseline_output(self):
        self.populate()
        self.fixture = "populated-write-timeout"
        real_set = cache.set
        def timeout(key, value, *args, **kwargs):
            if key in {"homepage_context_v2", "homepage_extras_v3"}:
                raise TimeoutError("synthetic Redis write timeout")
            return real_set(key, value, *args, **kwargs)
        with patch.object(cache_safe.cache, "set", side_effect=timeout):
            self.compare("guest", "cold")
