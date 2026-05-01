"""
Format Strategy Layer — Phase 1 of the Tournament Engine Refactor.

Every tournament format has its own lifecycle logic instead of sharing
bracket-centric catch-alls.  This module is the single place where that
format-specific logic lives.

Design
------
* ``FormatStrategy`` is an abstract base that also holds shared helpers
  (participant resolution, confirmed-registration query).
* ``register_strategy`` is a class decorator that inserts each concrete
  strategy into the module-level ``_REGISTRY`` dict keyed by
  ``Tournament.format`` value.
* ``get_strategy(fmt)`` is the public entry-point used by TOC views.

Implementation status
---------------------
* ``RoundRobinStrategy``  — fully implemented (Phase 2).
* All other strategies    — thin delegates to existing services (Phase 1
  stubs).  They keep the registry complete so callers never have to
  special-case "no strategy found".

Routing for Round Robin
-----------------------
Round Robin uses the existing Group / GroupStage / GroupStanding /
GroupStageService infrastructure as its canonical data model — one
``GroupStage`` with one ``Group`` ("League Table").  This means the
TOC schedule, matches, and standings surfaces work without any extra
changes; they already understand group-tagged matches and GroupStanding
rows.

The ``BracketService._generate_round_robin()`` path (creates
BracketNodes but no Match rows) is intentionally bypassed for
``Tournament.format == round_robin`` in favour of this strategy.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from django.core.exceptions import ValidationError
from django.db import transaction

if TYPE_CHECKING:  # pragma: no cover
    from apps.tournaments.models.tournament import Tournament

logger = logging.getLogger(__name__)


# ─── Abstract base ─────────────────────────────────────────────────────────────

class FormatStrategy(ABC):
    """
    Abstract base for format-specific tournament lifecycle logic.

    Every method that differs between formats is abstract.  Shared
    boilerplate (registration queries, participant resolution) lives here
    as ``_protected`` helpers so concrete subclasses stay small.
    """

    key: str           # must match a Tournament.FORMAT_CHOICES value
    label: str         # human-readable name for logs / UI
    primary_surface: str  # 'bracket' | 'standings' | 'fixtures'

    # ── Participant helpers ───────────────────────────────────────────────────

    @staticmethod
    def _confirmed_registrations(tournament: "Tournament"):
        from apps.tournaments.models.registration import Registration
        return list(
            Registration.objects.filter(
                tournament=tournament,
                status=Registration.CONFIRMED,
                is_deleted=False,
            ).select_related("user")
        )

    @staticmethod
    def _participant_id_and_name(reg) -> Tuple[int, str]:
        """Return ``(participant_id, display_name)`` from a Registration row."""
        if reg.team_id:
            try:
                from apps.organizations.models.team import Team as OrgTeam
                name = OrgTeam.objects.values_list("name", flat=True).get(id=reg.team_id)
            except Exception:
                name = f"Team #{reg.team_id}"
            return reg.team_id, name
        if reg.user_id:
            user = reg.user
            name = (user.get_full_name() or user.username) if user else f"Player #{reg.user_id}"
            return reg.user_id, name
        raise ValidationError(
            f"Registration {reg.pk} has neither user nor team_id."
        )

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def generate_fixtures(self, tournament: "Tournament", options: Dict) -> Dict:
        """Create all match rows for the first playable phase and return a stats dict."""

    @abstractmethod
    def reset_fixtures(self, tournament: "Tournament", *, force: bool = False, actor=None) -> None:
        """
        Delete all generated fixtures so ``generate_fixtures()`` can be called again.

        Implementations MUST gate the destructive operation through
        ``_ensure_reset_allowed(tournament, force=force, actor=actor)`` — defined
        in ``apps.tournaments.api.toc.brackets_service`` — so that:

        * COMPLETED / ARCHIVED tournaments are never reset.
        * Tournaments with played matches require ``force=True`` AND a
          staff/superuser actor.

        Raises ``FixtureResetBlockedError`` when the safety gate refuses.
        """

    @abstractmethod
    def standings(self, tournament: "Tournament") -> Dict:
        """Return live standings structured for the TOC standings surface."""

    @abstractmethod
    def can_finalize(self, tournament: "Tournament") -> Tuple[bool, str]:
        """Return ``(True, '')`` when all matches are done, ``(False, reason)`` otherwise."""

    @abstractmethod
    def toc_steps(self, tournament: "Tournament") -> List[Dict]:
        """Return format-specific stepper step definitions for the TOC Overview rail."""

    # ── UI metadata — concrete classes may override ───────────────────────────

    def get_primary_surface_name(self) -> str:
        """
        Return the human-readable name for the primary competition surface.

        Used in the TOC sidebar format chip and breadcrumbs.
        Examples: "Bracket", "Fixtures & Standings", "Swiss Rounds".
        """
        return "Bracket"

    def get_toc_tab_labels(self) -> Dict[str, str]:
        """
        Return format-specific label overrides for TOC sidebar tabs.

        Keys are tab IDs from ``TOCView._build_tabs()``.
        Only tabs listed here get renamed; all others keep their defaults.

        Example:
            {'matches': 'Fixtures', 'schedule': 'Fixture Schedule'}
        """
        return {}

    def get_hub_ui(self) -> Dict:
        """
        Return a dict describing which HUB sidebar tabs to show/hide and
        how to label them for this format.

        Keys
        ----
        show_bracket : bool
            Whether the "Bracket" tab should appear in the HUB sidebar.
        bracket_label : str
            Label for the bracket nav button (ignored if show_bracket=False).
        bracket_icon : str
            Lucide icon name for the bracket button.
        show_standings : bool
            Whether the "Standings" tab should appear.
        matches_label : str
            Label for the matches/fixtures nav button.
        matches_icon : str
            Lucide icon name for the matches button.
        primary_tab : str
            Tab id that the HUB JS should auto-navigate to on first load
            (defaults to 'overview').
        """
        return {
            "show_bracket":   True,
            "bracket_label":  "Bracket",
            "bracket_icon":   "git-merge",
            "show_standings": False,
            "matches_label":  "Match Lobby",
            "matches_icon":   "swords",
            "primary_tab":    "overview",
        }


# ─── Registry ──────────────────────────────────────────────────────────────────

_REGISTRY: Dict[str, FormatStrategy] = {}


def register_strategy(cls):
    """Class decorator — register a ``FormatStrategy`` subclass by its ``key``."""
    instance = cls()
    _REGISTRY[instance.key] = instance
    return cls


def get_strategy(format_key: str) -> FormatStrategy:
    """
    Return the ``FormatStrategy`` for the given tournament format key.

    Raises ``KeyError`` when the format has no registered strategy.
    """
    strategy = _REGISTRY.get(format_key)
    if strategy is None:
        raise KeyError(
            f"No FormatStrategy registered for format '{format_key}'. "
            f"Available: {sorted(_REGISTRY)}"
        )
    return strategy


def format_has_strategy(format_key: str) -> bool:
    """Return ``True`` when *format_key* has a registered strategy."""
    return format_key in _REGISTRY


# ─── Round Robin (fully implemented) ───────────────────────────────────────────

@register_strategy
class RoundRobinStrategy(FormatStrategy):
    """
    League-table round robin: every participant plays every other once.

    Data model (uses existing group-stage infrastructure):

        Tournament
          └─ GroupStage  (name="League Table", num_groups=1)
               └─ Group  (name="League Table")
                    ├─ GroupStanding × n
                    └─ Match × n*(n-1)/2  (bracket=None, lobby_info.group_id set)

    Because the data model is identical to a single-group GroupStage, the
    existing TOC schedule, matches, and standings surfaces work without any
    template or API changes.
    """

    key = "round_robin"
    label = "Round Robin"
    primary_surface = "standings"

    # ── Fixture generation ────────────────────────────────────────────────────

    @transaction.atomic
    def generate_fixtures(self, tournament: "Tournament", options: Dict) -> Dict:
        """
        Bootstrap the league table and create all pairwise match rows.

        Steps:
        1. Idempotency guard — raises if a GroupStage already exists.
        2. Resolve confirmed participants.
        3. Create GroupStage(name="League Table", 1 group).
        4. Create Group(name="League Table").
        5. Create one GroupStanding per participant.
        6. Call GroupStageService.generate_group_matches() — creates Match rows.

        Returns a stats dict (no Bracket object is created).
        """
        from apps.tournaments.models.group import Group, GroupStage, GroupStanding
        from apps.tournaments.services.group_stage_service import GroupStageService

        # ── Idempotency guard ─────────────────────────────────────────────────
        if GroupStage.objects.filter(tournament=tournament).exists():
            raise ValidationError(
                "Fixtures have already been generated for this tournament. "
                "Reset them before regenerating."
            )

        # ── Validate participants ──────────────────────────────────────────────
        registrations = self._confirmed_registrations(tournament)
        n = len(registrations)
        if n < 2:
            raise ValidationError(
                f"Round Robin requires at least 2 confirmed registrations; "
                f"found {n}."
            )

        # ── Merge organizer-saved format options ──────────────────────────────
        # Frontend saves customisation via POST /brackets/format-config/ which
        # writes to tournament.config['format_options']. Generate may also pass
        # `options` directly (e.g. for tests). Direct `options` win over saved
        # config when both are present.
        saved_options = {}
        try:
            cfg = tournament.config if isinstance(tournament.config, dict) else {}
            saved_options = dict(cfg.get('format_options') or {})
        except Exception:
            saved_options = {}
        merged = {**saved_options, **(options or {})}

        # Number of round-robin cycles: 1 = single RR, 2 = double RR (home/away).
        rounds_cycles = int(merged.get('rounds') or 1)
        if rounds_cycles not in (1, 2):
            rounds_cycles = 1
        # Top-N advancement (next stage / champion qualifier count).
        advancement_count = int(merged.get('advancement_count') or 1)
        if advancement_count < 1:
            advancement_count = 1

        # ── Points / tiebreaker config ─────────────────────────────────────────
        points_system = merged.get("points_system") or {"win": 3, "draw": 1, "loss": 0}
        group_config = {
            "points_system": points_system,
            "tiebreaker_rules": merged.get("tiebreaker_rules") or [
                "points", "wins", "goal_difference", "goals_for"
            ],
            "match_format": merged.get("match_format") or "bo1",
            "rounds": rounds_cycles,
        }

        # ── GroupStage wrapper ─────────────────────────────────────────────────
        stage = GroupStage.objects.create(
            tournament=tournament,
            name="League Table",
            num_groups=1,
            group_size=n,
            format=("double_round_robin" if rounds_cycles == 2 else "round_robin"),
            state="active",
            advancement_count_per_group=advancement_count,
        )

        # ── Single group ───────────────────────────────────────────────────────
        group = Group.objects.create(
            tournament=tournament,
            name="League Table",
            display_order=0,
            max_participants=n,
            advancement_count=advancement_count,
            config=group_config,
        )

        # ── Seed GroupStanding rows ────────────────────────────────────────────
        for seed, reg in enumerate(registrations, start=1):
            pid, _name = self._participant_id_and_name(reg)
            standing_kwargs: Dict = {"group": group, "rank": seed}
            if reg.team_id:
                standing_kwargs["team_id"] = reg.team_id
            else:
                # user FK — pass the user object to get both user and user_id
                standing_kwargs["user"] = reg.user
            GroupStanding.objects.create(**standing_kwargs)

        # ── Generate all pairwise Match rows ──────────────────────────────────
        total_created = GroupStageService.generate_group_matches(
            stage.id, rounds=rounds_cycles
        )

        expected = (n * (n - 1) // 2) * rounds_cycles
        if total_created != expected:
            logger.warning(
                "RoundRobinStrategy: expected %d fixtures for %d participants "
                "but created %d (tournament=%s).",
                expected, n, total_created, tournament.id,
            )
        else:
            logger.info(
                "RoundRobinStrategy: created %d fixtures for %d participants "
                "(tournament=%s).",
                total_created, n, tournament.id,
            )

        # ── Stamp scheduled_time on generated matches ─────────────────────────
        # GroupStageService.generate_group_matches() creates Match rows without
        # a scheduled_time. Without a timestamp, the TOC schedule timeline view
        # considers them "unscheduled" and the schedule page's empty-state check
        # fires if the frontend sorts only by time.  We stamp all bracket-null
        # matches for this tournament with the tournament's start time (or now)
        # so they are immediately visible in both timeline and list views.
        # Organisers can re-schedule individual fixtures later via Auto-Schedule.
        from apps.tournaments.models.match import Match as _Match
        default_time = (
            getattr(tournament, "tournament_start", None)
            or timezone.now()
        )
        _Match.objects.filter(
            tournament=tournament,
            bracket__isnull=True,
            scheduled_time__isnull=True,
            is_deleted=False,
        ).update(scheduled_time=default_time)

        # ── Bust standings cache so the tab is live immediately ───────────────
        try:
            from apps.tournaments.api.toc.cache_utils import bump_toc_scope
            bump_toc_scope("standings", tournament.id)
        except Exception:
            pass  # non-critical: cache will expire naturally

        return {
            "status": "fixtures_generated",
            "participants": n,
            "fixtures": total_created,
            "expected_fixtures": expected,
            "group_stage_id": stage.id,
            "group_id": group.id,
            "message": (
                f"Generated {total_created} fixture"
                f"{'s' if total_created != 1 else ''} "
                f"for {n} participants."
            ),
        }

    # ── Reset ──────────────────────────────────────────────────────────────────

    @transaction.atomic
    def reset_fixtures(self, tournament: "Tournament", *, force: bool = False, actor=None) -> None:
        """
        Delete all Round Robin fixtures (Match rows + GroupStage / Group /
        GroupStanding rows).

        Safety gate:
        * If tournament status is COMPLETED/ARCHIVED — refuse always.
        * If any matches are dirty (played, live, or under dispute) and
          ``force=False`` — refuse with FixtureResetBlockedError(code='fixtures_in_progress').
        * If dirty AND force AND actor is staff/superuser — proceed with WARNING log.
        * Otherwise (no dirty matches, fresh fixtures) — proceed silently.

        Raises:
            FixtureResetBlockedError when reset would destroy live data
            without admin override.
        """
        from apps.tournaments.api.toc.brackets_service import _ensure_reset_allowed
        from apps.tournaments.models.group import Group, GroupStage, GroupStanding
        from apps.tournaments.models.match import Match

        # Enforce safety gate before any destructive action.
        _ensure_reset_allowed(tournament, force=force, actor=actor)

        # Delete bracket-less matches (round robin matches have bracket=None)
        deleted_matches, _ = Match.objects.filter(
            tournament=tournament,
            bracket__isnull=True,
            is_deleted=False,
        ).delete()

        # Delete group infrastructure
        group_ids = list(
            Group.objects.filter(tournament=tournament).values_list("id", flat=True)
        )
        if group_ids:
            GroupStanding.objects.filter(group_id__in=group_ids).delete()
        Group.objects.filter(tournament=tournament).delete()
        GroupStage.objects.filter(tournament=tournament).delete()

        logger.info(
            "RoundRobinStrategy.reset_fixtures: deleted %d matches and group "
            "infrastructure for tournament=%s.",
            deleted_matches, tournament.id,
        )

    # ── Standings ──────────────────────────────────────────────────────────────

    def standings(self, tournament: "Tournament") -> Dict:
        """Delegate to the shared standings service — no new logic needed."""
        from apps.tournaments.api.toc.standings_service import TOCStandingsService
        return TOCStandingsService.get_standings(tournament)

    # ── Finalization readiness ─────────────────────────────────────────────────

    def can_finalize(self, tournament: "Tournament") -> Tuple[bool, str]:
        from apps.tournaments.models.match import Match

        pending = Match.objects.filter(
            tournament=tournament,
            bracket__isnull=True,
            is_deleted=False,
        ).exclude(
            state__in=["completed", "forfeit", "cancelled"]
        ).count()

        if pending > 0:
            plural = "es" if pending != 1 else ""
            return False, f"{pending} match{plural} still pending."
        return True, ""

    # ── TOC stepper steps ──────────────────────────────────────────────────────

    def toc_steps(self, tournament: "Tournament") -> List[Dict]:
        return [
            {"key": "setup",             "label": "Setup",             "icon": "settings-2"},
            {"key": "registration",      "label": "Registration",      "icon": "users"},
            {"key": "generate_fixtures", "label": "Generate Fixtures", "icon": "list-ordered"},
            {"key": "live",              "label": "Live",              "icon": "radio"},
            {"key": "finalize_table",    "label": "Finalize Table",    "icon": "trophy"},
            {"key": "completed",         "label": "Completed",         "icon": "flag"},
        ]

    # ── UI metadata ───────────────────────────────────────────────────────────

    def get_primary_surface_name(self) -> str:
        return "Fixtures & Standings"

    def get_toc_tab_labels(self) -> Dict[str, str]:
        # Rename the generic "Matches" tab to "Fixtures" — it's the same data
        # (Match rows), just framed as a league fixture list rather than
        # knockout matches.  "Schedule" becomes "Fixture Schedule" so the
        # distinction from a bracket schedule is clear.
        return {
            "matches":  "Fixtures",
            "schedule": "Fixture Schedule",
        }

    def get_hub_ui(self) -> Dict:
        return {
            "show_bracket":   False,   # no bracket tree for round robin
            "bracket_label":  None,
            "bracket_icon":   None,
            "show_standings": True,    # standings is the primary surface
            "matches_label":  "Fixtures",
            "matches_icon":   "list-ordered",
            "primary_tab":    "standings",
        }


# ─── Single Elimination (thin delegate) ────────────────────────────────────────

@register_strategy
class SingleEliminationStrategy(FormatStrategy):
    """
    Single Elimination.

    Phase 3 guarantee: ``generate_fixtures()`` always calls
    ``create_matches_from_bracket()`` so that Round 1 Match rows exist
    immediately after generation — not just BracketNodes.

    BracketNode semantics after generation
    ---------------------------------------
    * Round 1 nodes: both participants assigned (real or bye slot).
      ``create_matches_from_bracket`` creates Match rows for all non-bye
      round 1 nodes.
    * Later-round nodes: TBD (waiting for winners).  No matches created
      yet — they are created in real-time by ``update_bracket_after_match``.
    """

    key = "single_elimination"
    label = "Single Elimination"
    primary_surface = "bracket"

    @transaction.atomic
    def generate_fixtures(self, tournament: "Tournament", options: Dict) -> Dict:
        from apps.tournaments.services.bracket_service import BracketService
        from apps.brackets.models import BracketNode

        bracket_format = (
            options.get("bracket_format")
            or options.get("format")
            or None  # falls through to tournament.format inside generate_bracket
        )
        bracket = BracketService.generate_bracket_universal_safe(
            tournament_id=tournament.id,
            bracket_format=bracket_format,
            seeding_method=options.get("seeding_method"),
        )

        # Phase 3: create playable Match rows for all ready (non-bye) nodes.
        matches = BracketService.create_matches_from_bracket(bracket)

        # Count byes for informational return (byes are real Round 1 nodes but
        # require no match — the participant advances automatically).
        bye_count = BracketNode.objects.filter(bracket=bracket, is_bye=True).count()

        logger.info(
            "SingleEliminationStrategy.generate_fixtures tournament=%s "
            "bracket=%s matches_created=%d byes=%d",
            tournament.id, bracket.id, len(matches), bye_count,
        )

        return {
            "status": "bracket_generated",
            "bracket_id": bracket.id,
            "matches_created": len(matches),
            "byes": bye_count,
        }

    @transaction.atomic
    def reset_fixtures(self, tournament: "Tournament", *, force: bool = False, actor=None) -> None:
        from apps.tournaments.api.toc.brackets_service import _ensure_reset_allowed
        from apps.brackets.models import Bracket
        from apps.tournaments.models.match import Match
        # Safety gate — blocks reset when matches are live/completed unless
        # force=True AND actor is a platform admin.
        _ensure_reset_allowed(tournament, force=force, actor=actor)
        Match.objects.filter(tournament=tournament, bracket__isnull=False).delete()
        Bracket.objects.filter(tournament=tournament).delete()

    def standings(self, tournament: "Tournament") -> Dict:
        from apps.tournaments.api.toc.standings_service import TOCStandingsService
        return TOCStandingsService._get_bracket_standings(tournament) or {}

    def can_finalize(self, tournament: "Tournament") -> Tuple[bool, str]:
        from apps.tournaments.models.match import Match
        pending = Match.objects.filter(
            tournament=tournament, bracket__isnull=False, is_deleted=False,
        ).exclude(state__in=["completed", "forfeit", "cancelled"]).count()
        if pending:
            plural = "es" if pending != 1 else ""
            return False, f"{pending} match{plural} pending."
        return True, ""

    def toc_steps(self, tournament: "Tournament") -> List[Dict]:
        return [
            {"key": "setup",            "label": "Setup",            "icon": "settings-2"},
            {"key": "registration",     "label": "Registration",     "icon": "users"},
            {"key": "generate_bracket", "label": "Generate Bracket", "icon": "git-branch"},
            {"key": "scheduling",       "label": "Scheduling",       "icon": "calendar-days"},
            {"key": "live",             "label": "Live",             "icon": "radio"},
            {"key": "completed",        "label": "Completed",        "icon": "flag"},
        ]

    # ── UI metadata ───────────────────────────────────────────────────────────
    # Single Elimination: base defaults are correct — bracket is primary surface,
    # no standings tab, standard 'Match Lobby' label.  No overrides needed;
    # base class defaults apply.


# ─── Double Elimination ────────────────────────────────────────────────────────

@register_strategy
class DoubleEliminationStrategy(FormatStrategy):
    """
    Double Elimination.

    Phase 3 guarantee: ``generate_fixtures()`` creates Match rows for all
    Winner Bracket Round 1 non-bye nodes immediately.

    Match creation semantics
    ------------------------
    * WB Round 1 nodes: both participants assigned.
      ``create_matches_from_bracket`` creates Match rows for all non-bye
      WB-R1 nodes.
    * LB nodes (all rounds): created WITHOUT participants at generation
      time — they receive participants when WB results propagate via
      ``update_bracket_after_match``.  No LB matches are created here;
      this is correct and intentional.
    * GF / GFR nodes: TBD, populated at the end of LB.
    """

    key = "double_elimination"
    label = "Double Elimination"
    primary_surface = "bracket"

    @transaction.atomic
    def generate_fixtures(self, tournament: "Tournament", options: Dict) -> Dict:
        from apps.tournaments.services.bracket_service import BracketService
        from apps.brackets.models import Bracket, BracketNode

        bracket_format = (
            options.get("bracket_format")
            or options.get("format")
            or None
        )
        bracket = BracketService.generate_bracket_universal_safe(
            tournament_id=tournament.id,
            bracket_format=bracket_format,
            seeding_method=options.get("seeding_method"),
        )

        # Phase 3: create playable Match rows for WB Round 1 ready nodes.
        # LB nodes are intentionally empty at this stage — they receive
        # participants as WB results propagate; see class docstring.
        matches = BracketService.create_matches_from_bracket(bracket)

        wb_r1_matches = len(matches)
        bye_count = BracketNode.objects.filter(
            bracket=bracket, bracket_type=BracketNode.MAIN, is_bye=True
        ).count()
        lb_node_count = BracketNode.objects.filter(
            bracket=bracket, bracket_type=BracketNode.LOSERS
        ).count()

        logger.info(
            "DoubleEliminationStrategy.generate_fixtures tournament=%s "
            "bracket=%s wb_r1_matches=%d byes=%d lb_nodes=%d",
            tournament.id, bracket.id, wb_r1_matches, bye_count, lb_node_count,
        )

        return {
            "status": "bracket_generated",
            "bracket_id": bracket.id,
            "matches_created": wb_r1_matches,
            "byes": bye_count,
            "lb_nodes_pending": lb_node_count,
        }

    @transaction.atomic
    def reset_fixtures(self, tournament: "Tournament", *, force: bool = False, actor=None) -> None:
        SingleEliminationStrategy().reset_fixtures(tournament, force=force, actor=actor)

    def standings(self, tournament: "Tournament") -> Dict:
        return SingleEliminationStrategy().standings(tournament)

    def can_finalize(self, tournament: "Tournament") -> Tuple[bool, str]:
        return SingleEliminationStrategy().can_finalize(tournament)

    def toc_steps(self, tournament: "Tournament") -> List[Dict]:
        return SingleEliminationStrategy().toc_steps(tournament)

    # ── UI metadata ───────────────────────────────────────────────────────────

    def get_primary_surface_name(self) -> str:
        return "Double Elim Bracket"

    # show_bracket=True, show_standings=False, 'Match Lobby' — base defaults apply.


# ─── Swiss ─────────────────────────────────────────────────────────────────────

@register_strategy
class SwissStrategy(FormatStrategy):
    """
    Swiss System.

    Phase 3 guarantee: ``generate_fixtures()`` generates Round 1 pairings
    and creates Match rows for all non-bye pairs immediately.

    Bye handling
    ------------
    When the participant count is odd, the lowest-seeded participant
    receives a bye BracketNode (``is_bye=True``, ``participant2_id=None``).
    ``create_matches_from_bracket`` skips bye nodes, so the bye player
    gets no Match row but automatically receives credit for a win when
    ``SwissService.generate_next_round()`` is called.

    Subsequent rounds
    -----------------
    Round 2+ are triggered by the organizer via the existing
    ``POST /api/toc/<slug>/brackets/swiss/next-round/`` endpoint.
    """

    key = "swiss"
    label = "Swiss System"
    primary_surface = "standings"

    @transaction.atomic
    def generate_fixtures(self, tournament: "Tournament", options: Dict) -> Dict:
        from apps.tournaments.services.bracket_service import BracketService
        from apps.brackets.models import BracketNode

        # ``generate_bracket_universal_safe`` with format='swiss' routes to
        # ``SwissService.generate_round1()`` which creates Round 1 BracketNodes.
        bracket = BracketService.generate_bracket_universal_safe(
            tournament_id=tournament.id,
            bracket_format="swiss",
            seeding_method=options.get("seeding_method"),
        )

        # Phase 3: create playable Match rows for non-bye Round 1 nodes.
        matches = BracketService.create_matches_from_bracket(bracket)

        # Count byes — odd participant counts produce one bye node.
        bye_count = BracketNode.objects.filter(
            bracket=bracket, round_number=1, is_bye=True
        ).count()
        total_rounds = bracket.total_rounds

        logger.info(
            "SwissStrategy.generate_fixtures tournament=%s bracket=%s "
            "round1_matches=%d byes=%d total_rounds=%d",
            tournament.id, bracket.id, len(matches), bye_count, total_rounds,
        )

        return {
            "status": "round_generated",
            "round": 1,
            "total_rounds": total_rounds,
            "bracket_id": bracket.id,
            "matches_created": len(matches),
            "byes": bye_count,
        }

    def reset_fixtures(self, tournament: "Tournament", *, force: bool = False, actor=None) -> None:
        SingleEliminationStrategy().reset_fixtures(tournament, force=force, actor=actor)

    def standings(self, tournament: "Tournament") -> Dict:
        from apps.brackets.models import Bracket
        from apps.tournaments.services.swiss_service import SwissService
        bracket = Bracket.objects.filter(tournament=tournament).first()
        if not bracket:
            return {"error": "No Swiss bracket found."}
        return SwissService.get_standings(bracket)

    def can_finalize(self, tournament: "Tournament") -> Tuple[bool, str]:
        return SingleEliminationStrategy().can_finalize(tournament)

    def toc_steps(self, tournament: "Tournament") -> List[Dict]:
        return [
            {"key": "setup",            "label": "Setup",           "icon": "settings-2"},
            {"key": "registration",     "label": "Registration",    "icon": "users"},
            {"key": "generate_bracket", "label": "Generate Round 1","icon": "list-ordered"},
            {"key": "live",             "label": "Live",            "icon": "radio"},
            {"key": "completed",        "label": "Completed",       "icon": "flag"},
        ]

    # ── UI metadata ───────────────────────────────────────────────────────────

    def get_primary_surface_name(self) -> str:
        return "Swiss Rounds"

    def get_toc_tab_labels(self) -> Dict[str, str]:
        # The 'Brackets' tab is already hidden for Swiss (has_brackets=False).
        # Rename 'Matches' to 'Pairings' to reflect the Swiss per-round context.
        return {"matches": "Pairings"}

    def get_hub_ui(self) -> Dict:
        return {
            "show_bracket":   True,    # re-use bracket tab for Swiss rounds view
            "bracket_label":  "Swiss Rounds",
            "bracket_icon":   "list-ordered",
            "show_standings": True,    # Swiss has live standings
            "matches_label":  "Pairings",
            "matches_icon":   "swords",
            "primary_tab":    "bracket",   # 'bracket' tab = Swiss rounds panel
        }


# ─── Group + Playoff (thin delegate) ───────────────────────────────────────────

@register_strategy
class GroupPlayoffStrategy(FormatStrategy):
    """
    Thin delegate — group phase uses existing GroupStageService; playoff
    transition uses TournamentService.transition_to_knockout_stage().
    """

    key = "group_playoff"
    label = "Group Stage + Playoff"
    primary_surface = "standings"

    def generate_fixtures(self, tournament: "Tournament", options: Dict) -> Dict:
        # Group-playoff calls transition_to_knockout_stage for the playoff bracket;
        # group match generation is a separate action (TOC "Generate Matches" step).
        from apps.tournaments.services.tournament_service import TournamentService
        bracket = TournamentService.transition_to_knockout_stage(tournament.id)
        return {"status": "bracket_generated", "bracket_id": bracket.id}

    def reset_fixtures(self, tournament: "Tournament", *, force: bool = False, actor=None) -> None:
        SingleEliminationStrategy().reset_fixtures(tournament, force=force, actor=actor)

    def standings(self, tournament: "Tournament") -> Dict:
        from apps.tournaments.api.toc.standings_service import TOCStandingsService
        return TOCStandingsService.get_standings(tournament)

    def can_finalize(self, tournament: "Tournament") -> Tuple[bool, str]:
        return SingleEliminationStrategy().can_finalize(tournament)

    def toc_steps(self, tournament: "Tournament") -> List[Dict]:
        return [
            {"key": "setup",             "label": "Setup",            "icon": "settings-2"},
            {"key": "registration",      "label": "Registration",     "icon": "users"},
            {"key": "draw_groups",       "label": "Draw Groups",      "icon": "shuffle"},
            {"key": "generate_matches",  "label": "Generate Matches", "icon": "swords"},
            {"key": "group_stage_live",  "label": "Group Stage",      "icon": "users"},
            {"key": "generate_playoffs", "label": "Playoffs",         "icon": "trophy"},
            {"key": "knockout_live",     "label": "Knockout",         "icon": "swords"},
            {"key": "completed",         "label": "Completed",        "icon": "flag"},
        ]

    # ── UI metadata ───────────────────────────────────────────────────────────

    def get_primary_surface_name(self) -> str:
        return "Groups & Bracket"

    def get_hub_ui(self) -> Dict:
        return {
            "show_bracket":   True,
            "bracket_label":  "Bracket",
            "bracket_icon":   "git-merge",
            "show_standings": True,   # group standings are primary
            "matches_label":  "Match Lobby",
            "matches_icon":   "swords",
            "primary_tab":    "standings",
        }


# ─── Battle Royale / Lobby Leaderboard (stub) ──────────────────────────────────

@register_strategy
class BattleRoyaleStrategy(FormatStrategy):
    """
    Battle Royale / Lobby Leaderboard.

    Multiple lobby sessions each contribute placement + kill points to a single
    aggregated leaderboard.  There are no 1v1 brackets.

    This is a Phase 6 stub: the core leaderboard engine
    (``leaderboard.py``, ``BRScoringMatrix``) exists, but the full TOC
    lobby-room creation workflow and automatic score aggregation are not yet
    wired.  The stub keeps the registry complete so the format appears in the
    create form and routes correctly in the TOC lifecycle stepper.
    """

    key = "battle_royale"
    label = "Battle Royale / Lobby Leaderboard"
    primary_surface = "standings"

    def generate_fixtures(self, tournament: "Tournament", options: Dict) -> Dict:
        raise ValidationError(
            "Battle Royale lobby session management is not yet available in the "
            "self-serve flow. Use the TOC Lobbies tab to create and score sessions."
        )

    def reset_fixtures(self, tournament: "Tournament", *, force: bool = False, actor=None) -> None:
        # Battle Royale lobby/score data is not yet persisted in DB models;
        # the safety gate still applies once Phase 6 wires up Match rows.
        from apps.tournaments.api.toc.brackets_service import _ensure_reset_allowed
        _ensure_reset_allowed(tournament, force=force, actor=actor)

    def standings(self, tournament: "Tournament") -> Dict:
        from apps.tournaments.api.toc.standings_service import TOCStandingsService
        return TOCStandingsService.get_standings(tournament)

    def can_finalize(self, tournament: "Tournament") -> Tuple[bool, str]:
        return False, "Battle Royale finalization is not yet automated. Finalize manually via TOC."

    def toc_steps(self, tournament: "Tournament") -> List[Dict]:
        return [
            {"key": "setup",           "label": "Setup",            "icon": "settings-2"},
            {"key": "registration",    "label": "Registration",     "icon": "users"},
            {"key": "lobby_setup",     "label": "Lobby Setup",      "icon": "crosshair"},
            {"key": "live",            "label": "Live",             "icon": "radio"},
            {"key": "score_entry",     "label": "Score Entry",      "icon": "bar-chart-2"},
            {"key": "completed",       "label": "Completed",        "icon": "flag"},
        ]

    # ── UI metadata ───────────────────────────────────────────────────────────

    def get_primary_surface_name(self) -> str:
        return "Leaderboard"

    def get_toc_tab_labels(self) -> Dict[str, str]:
        return {
            "matches":  "Lobby Sessions",
            "schedule": "Lobby Schedule",
        }

    def get_hub_ui(self) -> Dict:
        return {
            "show_bracket":   False,   # no bracket tree
            "bracket_label":  None,
            "bracket_icon":   None,
            "show_standings": True,    # leaderboard is primary
            "matches_label":  "Lobby Sessions",
            "matches_icon":   "crosshair",
            "primary_tab":    "standings",
        }
