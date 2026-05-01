"""
TOC Brackets & Competition Engine Service — Sprint 5

Wraps BracketService, GroupStageService, and BracketEditorService
to provide TOC-level bracket operations.
"""

import logging
from typing import Any, Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from apps.tournaments.models import (
    Bracket,
    BracketNode,
    Group,
    GroupStage,
    GroupStanding,
    Match,
    Registration,
    Tournament,
    TournamentStage,
)
from apps.tournaments.models.qualifier_pipeline import (
    PipelineStage,
    PromotionRule,
    QualifierPipeline,
)
from apps.tournaments.services.bracket_service import BracketService
from apps.tournaments.services.group_stage_service import GroupStageService
from apps.tournaments.services.match_lobby_service import hydrate_match_lobby_info

logger = logging.getLogger(__name__)


class GroupMatchGenerationError(ValueError):
    """Structured validation failure for group match generation requests."""

    def __init__(self, message: str, *, details: Optional[Dict[str, Any]] = None, code: str = "group_generation_blocked"):
        super().__init__(message)
        self.details = details or {}
        self.code = code


class FixtureResetBlockedError(ValueError):
    """
    Raised when an organizer attempts to reset / regenerate fixtures while
    matches are already in progress, completed, or under dispute.

    The error carries a structured ``code`` and ``details`` payload so the TOC
    frontend can show the correct UI:

    * ``code='fixtures_in_progress'`` — matches are dirty, organizer needs an
      admin force-override to proceed.
    * ``code='tournament_finalized'`` — tournament is COMPLETED / ARCHIVED;
      no reset is possible. Organizer must clone-and-archive instead.
    """

    def __init__(self, message: str, *, code: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def _classify_fixture_state(tournament) -> Dict[str, Any]:
    """
    Classify the current state of a tournament's fixtures for reset-safety checks.

    Returns a dict with:
        is_finalized:    bool   tournament.status in {completed, archived}
        dirty:           bool   any match is past pre-game state (live/completed/forfeit/etc)
        dirty_count:     int    number of dirty matches
        total_matches:   int    total non-deleted matches
        sample_states:   list   up to 3 sample (state, count) tuples for diagnostics

    Pre-game match states (``scheduled``, ``check_in``, ``ready``) are considered
    safe to discard. Anything past that — ``live``, ``pending_result``, ``completed``,
    ``forfeit``, ``cancelled``, ``disputed`` — represents user-entered data and
    should require an admin override before being destroyed.

    This helper is format-agnostic. It's used by every strategy's reset path
    and by the TOCBracketsService.reset_bracket() entry point.
    """
    PRE_GAME = {Match.SCHEDULED, Match.CHECK_IN, Match.READY}

    status = (getattr(tournament, "status", "") or "").lower()
    is_finalized = status in {"completed", "archived"}

    matches = Match.objects.filter(
        tournament=tournament,
        is_deleted=False,
    ).only("state")
    total_matches = matches.count()

    dirty_qs = matches.exclude(state__in=PRE_GAME)
    dirty_count = dirty_qs.count()

    sample_states: List[tuple] = []
    if dirty_count:
        from collections import Counter
        state_counter = Counter(dirty_qs.values_list("state", flat=True))
        sample_states = state_counter.most_common(3)

    return {
        "is_finalized":  is_finalized,
        "dirty":         dirty_count > 0,
        "dirty_count":   dirty_count,
        "total_matches": total_matches,
        "sample_states": sample_states,
    }


def _ensure_reset_allowed(tournament, *, force: bool = False, actor=None) -> None:
    """
    Gate-keeper for fixture/bracket reset operations.

    Rules:
    * If ``tournament.status`` is COMPLETED / ARCHIVED → always block.
      Organizer must archive-and-clone instead.
    * If any matches are dirty (past pre-game state) AND ``force`` is False
      → block with ``code='fixtures_in_progress'``.
    * If dirty AND ``force=True`` AND actor is staff/superuser → allow.
    * If dirty AND ``force=True`` AND actor is organizer-only → block.
      Force overrides require platform-admin level credentials.

    Raises ``FixtureResetBlockedError`` on violation.
    """
    state = _classify_fixture_state(tournament)

    if state["is_finalized"]:
        raise FixtureResetBlockedError(
            "This tournament has been finalized. To re-run, archive it and "
            "clone a fresh tournament.",
            code="tournament_finalized",
            details={"status": tournament.status},
        )

    if not state["dirty"]:
        return  # clean reset — allowed

    # Dirty but force flag set → check actor permission level
    if force:
        is_admin = bool(
            actor and (getattr(actor, "is_staff", False) or getattr(actor, "is_superuser", False))
        )
        if not is_admin:
            raise FixtureResetBlockedError(
                "Force reset requires a platform admin. Tournament organizers "
                "cannot override this safeguard once matches have been played.",
                code="force_requires_admin",
                details={
                    "dirty_count":    state["dirty_count"],
                    "total_matches":  state["total_matches"],
                },
            )
        logger.warning(
            "FORCE RESET tournament=%s actor=%s dirty=%d/%d states=%s",
            tournament.id, getattr(actor, "username", "?"),
            state["dirty_count"], state["total_matches"], state["sample_states"],
        )
        return  # admin override — allowed (caller proceeds to delete)

    # Dirty + no force → blocked, prompt frontend for admin override
    raise FixtureResetBlockedError(
        f"{state['dirty_count']} of {state['total_matches']} matches have already "
        f"been played or are in progress. Resetting will destroy match results. "
        f"A platform admin can force this through if absolutely necessary.",
        code="fixtures_in_progress",
        details={
            "dirty_count":    state["dirty_count"],
            "total_matches":  state["total_matches"],
            "sample_states":  state["sample_states"],
        },
    )


class TOCBracketsService:
    """TOC-level bracket, group-stage, and qualifier operations."""

    @staticmethod
    def _is_placeholder_name(value: Any) -> bool:
        text = str(value or '').strip().lower()
        return not text or text in {'tba', 'tbd', 'pending', 'to be decided', 'to be announced'}

    @staticmethod
    def _coerce_group_id(raw_group_id: Any) -> Optional[int]:
        """Normalize group_id from JSON payloads to int when possible."""
        if raw_group_id is None:
            return None
        try:
            return int(raw_group_id)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _group_stage_match_stats(tournament, group_ids: set[int]) -> Dict[int, Dict[str, int]]:
        """Return per-group totals for bracket-less matches that are tagged with lobby_info.group_id."""
        stats = {
            gid: {"total": 0, "completed": 0}
            for gid in group_ids
        }
        if not group_ids:
            return stats

        matches = Match.objects.filter(
            tournament=tournament,
            bracket__isnull=True,
            is_deleted=False,
        ).only("id", "state", "lobby_info")

        for match in matches.iterator():
            group_id = TOCBracketsService._coerce_group_id((match.lobby_info or {}).get("group_id"))
            if group_id not in stats:
                continue
            stats[group_id]["total"] += 1
            if match.state in (Match.COMPLETED, Match.FORFEIT):
                stats[group_id]["completed"] += 1

        return stats

    @staticmethod
    def _group_stage_match_ids(tournament, group_ids: set[int]) -> List[int]:
        """Collect IDs of bracket-less matches that belong to the given groups via lobby_info.group_id."""
        if not group_ids:
            return []

        ids: List[int] = []
        matches = Match.objects.filter(
            tournament=tournament,
            bracket__isnull=True,
            is_deleted=False,
        ).only("id", "lobby_info")

        for match in matches.iterator():
            group_id = TOCBracketsService._coerce_group_id((match.lobby_info or {}).get("group_id"))
            if group_id in group_ids:
                ids.append(match.id)

        return ids

    @staticmethod
    def _group_generation_diagnostics(groups: List[Dict[str, Any]], rounds: int) -> Dict[str, Any]:
        """Summarize group readiness and expected output for match generation."""
        blocked_groups: List[Dict[str, Any]] = []
        ready_groups: List[Dict[str, Any]] = []
        expected_matches = 0

        for group in groups:
            standings = group.get("standings") or []
            participant_keys = set()
            orphan_entries = 0

            for standing in standings:
                team_id = (standing or {}).get("team_id")
                user_id = (standing or {}).get("user_id")
                if team_id not in (None, "", 0):
                    participant_keys.add(f"team:{team_id}")
                elif user_id not in (None, "", 0):
                    participant_keys.add(f"user:{user_id}")
                else:
                    orphan_entries += 1

            participant_count = len(participant_keys)
            group_name = group.get("name") or f"Group {group.get('id')}"

            if participant_count < 2:
                reason = (
                    f"{group_name} has only {participant_count} active participant"
                    f"{'s' if participant_count != 1 else ''}."
                )
                if orphan_entries > 0:
                    reason += (
                        f" {orphan_entries} roster entr"
                        f"{'ies are' if orphan_entries != 1 else 'y is'} missing linked team/user IDs."
                    )
                blocked_groups.append({
                    "group_id": group.get("id"),
                    "group_name": group_name,
                    "participant_count": participant_count,
                    "orphan_entries": orphan_entries,
                    "reason": reason,
                })
                continue

            group_expected = ((participant_count * (participant_count - 1)) // 2) * rounds
            expected_matches += group_expected
            ready_groups.append({
                "group_id": group.get("id"),
                "group_name": group_name,
                "participant_count": participant_count,
                "expected_matches": group_expected,
            })

        return {
            "rounds": rounds,
            "group_count": len(groups),
            "ready_group_count": len(ready_groups),
            "blocked_group_count": len(blocked_groups),
            "expected_matches": expected_matches,
            "ready_groups": ready_groups,
            "blocked_groups": blocked_groups,
        }

    @staticmethod
    def _registered_user_ids_for_participant_ids(tournament, participant_ids: List[int]) -> List[int]:
        """Resolve registration user IDs for participant IDs (user IDs for solo, team IDs for team events)."""
        ids = [int(pid) for pid in participant_ids if pid]
        if not ids:
            return []

        regs = Registration.objects.filter(
            tournament=tournament,
            status__in=["confirmed", "auto_approved"],
            is_deleted=False,
            user__isnull=False,
        ).filter(
            Q(user_id__in=ids) | Q(team_id__in=ids)
        )
        return list(regs.values_list("user_id", flat=True).distinct())

    @staticmethod
    def _match_participant_user_ids(tournament, match: Match) -> List[int]:
        """Resolve participant user IDs for a match from registered users."""
        participant_ids = [match.participant1_id, match.participant2_id]
        return TOCBracketsService._registered_user_ids_for_participant_ids(
            tournament,
            [pid for pid in participant_ids if pid],
        )

    @staticmethod
    def _participant_reschedule_settings(tournament) -> Dict[str, Any]:
        """Read participant-driven rescheduling policy from tournament config."""
        config = tournament.config if isinstance(tournament.config, dict) else {}
        policy = config.get("participant_rescheduling")
        if not isinstance(policy, dict):
            policy = {}

        allow = bool(policy.get("allow_participant_rescheduling", False))

        raw_deadline_minutes = policy.get("deadline_minutes_before")
        if raw_deadline_minutes is None:
            raw_deadline_hours = policy.get("deadline_hours_before")
            if raw_deadline_hours is None:
                deadline_minutes = 120
            else:
                try:
                    deadline_minutes = int(float(raw_deadline_hours) * 60)
                except (TypeError, ValueError):
                    deadline_minutes = 120
        else:
            try:
                deadline_minutes = int(raw_deadline_minutes)
            except (TypeError, ValueError):
                deadline_minutes = 120

        deadline_minutes = max(5, min(deadline_minutes, 10080))

        return {
            "allow_participant_rescheduling": allow,
            "deadline_minutes_before": deadline_minutes,
        }

    @staticmethod
    def get_participant_reschedule_settings(tournament) -> Dict[str, Any]:
        """Public settings payload for TOC schedule controls."""
        settings = TOCBracketsService._participant_reschedule_settings(tournament)
        settings["deadline_hours_before"] = round(settings["deadline_minutes_before"] / 60, 2)
        return settings

    @staticmethod
    def update_participant_reschedule_settings(tournament, data: Dict[str, Any], user) -> Dict[str, Any]:
        """Persist participant rescheduling policy under tournament.config."""
        current = TOCBracketsService._participant_reschedule_settings(tournament)
        allow = current["allow_participant_rescheduling"]
        deadline_minutes = current["deadline_minutes_before"]

        if "allow_participant_rescheduling" in data:
            allow = bool(data.get("allow_participant_rescheduling"))

        if "deadline_minutes_before" in data:
            try:
                deadline_minutes = int(data.get("deadline_minutes_before"))
            except (TypeError, ValueError):
                raise ValueError("deadline_minutes_before must be a number.")
        elif "deadline_hours_before" in data:
            try:
                deadline_minutes = int(float(data.get("deadline_hours_before")) * 60)
            except (TypeError, ValueError):
                raise ValueError("deadline_hours_before must be a number.")

        deadline_minutes = max(5, min(deadline_minutes, 10080))

        config = tournament.config if isinstance(tournament.config, dict) else {}
        policy = config.get("participant_rescheduling") if isinstance(config.get("participant_rescheduling"), dict) else {}
        policy["allow_participant_rescheduling"] = allow
        policy["deadline_minutes_before"] = deadline_minutes
        policy["updated_at"] = timezone.now().isoformat()
        policy["updated_by"] = getattr(user, "id", None)

        config["participant_rescheduling"] = policy
        tournament.config = config
        tournament.save(update_fields=["config"])

        payload = TOCBracketsService.get_participant_reschedule_settings(tournament)
        payload["updated_by"] = getattr(user, "id", None)
        return payload

    @staticmethod
    def _fire_schedule_generated_event(
        tournament,
        *,
        scheduled_count: int,
        round_count: int,
        force_email: bool = False,
        target_user_ids: Optional[List[int]] = None,
        reason: str = "",
    ) -> None:
        """Fire a normalized schedule_generated notification payload."""
        try:
            from apps.tournaments.api.toc.notifications_service import TOCNotificationsService

            context: Dict[str, Any] = {
                "scheduled_count": max(0, int(scheduled_count or 0)),
                "round_count": max(0, int(round_count or 0)),
                "force_email": bool(force_email),
                "dedupe": False,
                "url": f"/tournaments/{tournament.slug}/hub/",
            }

            if reason:
                context["reason"] = str(reason)

            if isinstance(target_user_ids, list):
                normalized_ids = []
                for raw_id in target_user_ids:
                    try:
                        parsed = int(raw_id)
                    except (TypeError, ValueError):
                        continue
                    if parsed > 0:
                        normalized_ids.append(parsed)
                if normalized_ids:
                    # Keep recipient list stable and duplicate-free.
                    context["target_user_ids"] = sorted(set(normalized_ids))

            TOCNotificationsService.fire_auto_event(tournament, "schedule_generated", context)
        except Exception:
            pass

    # ── Bracket generation / management ────────────────────────

    @staticmethod
    def generate_bracket(tournament, user, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate bracket from confirmed registrations + seeding.

        Sprint 29: Added re-generation guard — prevents accidental
        destruction of an existing bracket. Must reset first.
        """
        data = data or {}
        if (
            "third_place_match_enabled" in data or
            "bronze_match_enabled" in data
        ):
            config = dict(getattr(tournament, "config", None) or {})
            bracket_settings = dict(config.get("bracket_settings") or {})
            enabled = bool(
                data.get("third_place_match_enabled") or
                data.get("bronze_match_enabled")
            )
            bracket_settings["third_place_match_enabled"] = enabled
            bracket_settings["bronze_match_enabled"] = enabled
            config["bracket_settings"] = bracket_settings
            tournament.config = config
            tournament.save(update_fields=["config"])

        # ── Non-bracket formats route BEFORE the Bracket existence check ────────
        # Round Robin and Battle Royale never create a Bracket object — they use
        # GroupStage / leaderboard infrastructure instead.  An existing Bracket
        # (e.g. from a previous SE generation before the format was changed)
        # must NOT block them.  Each strategy owns its own idempotency guard.
        _NON_BRACKET_FORMATS = {Tournament.ROUND_ROBIN, Tournament.BATTLE_ROYALE}
        if tournament.format in _NON_BRACKET_FORMATS:
            from apps.tournaments.services.format_strategy import (
                get_strategy,
                format_has_strategy,
            )
            fmt = tournament.format
            if not format_has_strategy(fmt):
                raise ValueError(
                    f"No format strategy registered for '{fmt}'."
                )
            try:
                result = get_strategy(fmt).generate_fixtures(tournament, data)
            except Exception as exc:
                raise ValueError(str(exc))
            try:
                from apps.tournaments.api.toc.notifications_service import TOCNotificationsService
                TOCNotificationsService.fire_auto_event(tournament, "bracket_generated")
            except Exception:
                pass
            try:
                from apps.tournaments.api.toc.cache_utils import bump_toc_scopes
                bump_toc_scopes(tournament.id, "brackets", "matches", "overview", "standings", "analytics")
            except Exception:
                pass
            return result

        # ── Bracket existence guard (bracket-based formats only) ────────────
        existing = Bracket.objects.filter(tournament=tournament).first()
        if existing:
            raise ValueError(
                "A bracket already exists. Reset the current bracket "
                "before generating a new one."
            )

        if tournament.format == Tournament.GROUP_PLAYOFF:
            from apps.tournaments.services.tournament_service import TournamentService

            requested_format = data.get("bracket_format") or data.get("format")
            requested_seeding = data.get("seeding_method")

            if requested_format or requested_seeding:
                config = tournament.config or {}
                knockout_config = dict(config.get("knockout_config") or {})
                if requested_format:
                    knockout_config["format"] = str(requested_format).replace("_", "-")
                if requested_seeding:
                    knockout_config["seeding_method"] = str(requested_seeding)
                config["knockout_config"] = knockout_config
                tournament.config = config
                tournament.save(update_fields=["config"])

            try:
                bracket = TournamentService.transition_to_knockout_stage(tournament.id)
            except Exception as exc:
                raise ValueError(str(exc))
        else:
            # Phase 3: route all remaining formats (SE, DE, Swiss, and any
            # future registered format) through the strategy layer so that
            # create_matches_from_bracket() is guaranteed to run after node
            # generation.  Unknown / unregistered formats fall through to the
            # bare generate_bracket_universal_safe() as a safe fallback.
            from apps.tournaments.services.format_strategy import (
                get_strategy,
                format_has_strategy,
            )
            fmt = tournament.format
            if format_has_strategy(fmt):
                try:
                    get_strategy(fmt).generate_fixtures(tournament, data)
                except Exception as exc:
                    raise ValueError(str(exc))
                # Fetch the bracket the strategy just created for serialization.
                bracket = (
                    Bracket.objects.filter(tournament=tournament)
                    .order_by("-id")
                    .first()
                )
                if bracket is None:
                    raise ValueError(
                        f"Strategy for '{fmt}' produced no Bracket row."
                    )
            else:
                # Unknown format — best-effort bare generation (no Match rows).
                bracket = BracketService.generate_bracket_universal_safe(
                    tournament_id=tournament.id,
                    bracket_format=data.get("bracket_format") or data.get("format"),
                    seeding_method=data.get("seeding_method"),
                )

        # Fire auto-notification for bracket generation
        try:
            from apps.tournaments.api.toc.notifications_service import TOCNotificationsService
            TOCNotificationsService.fire_auto_event(tournament, "bracket_generated")
        except Exception:
            pass
        return TOCBracketsService._serialize_bracket(bracket)

    @staticmethod
    def reset_bracket(tournament, user, *, force: bool = False) -> Dict[str, Any]:
        """
        Reset bracket / fixtures — routes to the format strategy for clean teardown.

        Safety gate (enforced by ``_ensure_reset_allowed``):
        * COMPLETED / ARCHIVED tournaments — reset is always blocked.
        * Tournaments with played matches — require ``force=True`` AND a
          staff/superuser ``user``. Organizers cannot override this.

        Raises ``FixtureResetBlockedError`` (subclass of ``ValueError``) when
        the safety gate refuses. The view layer catches and translates these
        into structured 409/403 responses with ``code`` and ``details`` so
        the frontend can show the right confirmation flow.
        """
        if tournament.format == Tournament.ROUND_ROBIN:
            # Round Robin uses Group/GroupStage data, not Bracket rows.
            from apps.tournaments.services.format_strategy import get_strategy
            get_strategy(Tournament.ROUND_ROBIN).reset_fixtures(
                tournament, force=force, actor=user
            )
            return {"status": "reset", "message": "Fixtures reset. Generate new ones."}

        # All other formats: enforce safety gate at the service layer too,
        # then delete Bracket + bracket-linked Matches.
        _ensure_reset_allowed(tournament, force=force, actor=user)
        Bracket.objects.filter(tournament=tournament).delete()
        Match.objects.filter(
            tournament=tournament, bracket__isnull=False
        ).delete()

        # For GROUP_PLAYOFF tournaments, also reset stage back to group_stage
        # so the admin can re-run "Generate Playoffs" without hitting the
        # "already in knockout stage" guard.
        if tournament.format == Tournament.GROUP_PLAYOFF:
            current_stage = tournament.get_current_stage()
            if current_stage == Tournament.STAGE_KNOCKOUT:
                tournament.set_current_stage(Tournament.STAGE_GROUP, save=True)
                logger.info(
                    f"Reset tournament '{tournament.name}' stage from knockout back to group."
                )

        return {"status": "reset", "message": "Bracket reset. Generate a new one."}

    @staticmethod
    def create_bronze_match(tournament, user) -> Dict[str, Any]:
        """Repair action: create a third-place match from known semifinal losers."""
        try:
            match = BracketService.create_bronze_match_from_semifinal_losers(
                tournament.id,
                actor=user,
            )
        except ValidationError as exc:
            raise ValueError(str(exc))
        from apps.tournaments.services.match_read_model import MatchReadModel
        return {
            "status": "created",
            "message": "Bronze match created from semifinal losers.",
            "match": MatchReadModel.for_tournament(tournament).by_id(match.id),
        }

    @staticmethod
    def publish_bracket(tournament, user) -> Dict[str, Any]:
        """Finalize and publish bracket to participants."""
        bracket = Bracket.objects.filter(tournament=tournament).first()
        if not bracket:
            raise ValueError("No bracket to publish.")
        if bracket.is_finalized:
            raise ValueError("Bracket already published.")
        bracket = BracketService.finalize_bracket(
            bracket_id=bracket.id, finalized_by=user
        )
        # Fire auto-notification for bracket publication
        try:
            from apps.tournaments.api.toc.notifications_service import TOCNotificationsService
            TOCNotificationsService.fire_auto_event(tournament, "bracket_published")
        except Exception:
            pass
        return TOCBracketsService._serialize_bracket(bracket)

    @staticmethod
    def get_bracket(tournament) -> Dict[str, Any]:
        """Current bracket state as tree structure.

        For Round Robin tournaments, there is no Bracket tree — the competition
        runs through Group/GroupStage/GroupStanding infrastructure.  We return a
        bracket-compatible envelope with ``is_round_robin=True`` and the full
        group payload embedded so the TOC brackets tab can render the league
        table and so button state management (Generate / Reset) works correctly.
        """
        if tournament.format == Tournament.ROUND_ROBIN:
            groups_payload = TOCBracketsService.get_groups(tournament)
            fixtures_exist = bool(
                groups_payload.get("exists")
                and groups_payload.get("groups")
                and groups_payload.get("matches_total", 0) > 0
            )
            return {
                "exists": fixtures_exist,
                "is_round_robin": True,
                "bracket": None,
                "nodes": [],
                "groups_data": groups_payload,
                "current_stage": None,
            }

        bracket = Bracket.objects.filter(tournament=tournament).first()
        if not bracket:
            return {"exists": False, "bracket": None, "nodes": []}

        try:
            viz = BracketService.get_bracket_visualization_data(bracket.id)
        except Exception:
            viz = {}

        nodes = list(BracketNode.objects.filter(bracket=bracket).select_related(
            "match"
        ).order_by("round_number", "match_number_in_round"))

        # Batch-resolve team names & logos for all participant IDs in nodes
        is_team = tournament.participation_type != 'solo'
        participant_ids = set()
        for n in nodes:
            match_obj = getattr(n, 'match', None)
            for raw_id in (
                n.participant1_id,
                n.participant2_id,
                getattr(match_obj, 'participant1_id', None),
                getattr(match_obj, 'participant2_id', None),
                getattr(match_obj, 'winner_id', None),
                getattr(match_obj, 'loser_id', None),
            ):
                if raw_id:
                    participant_ids.add(raw_id)
        from apps.tournaments.services.participant_identity import ParticipantIdentityService
        identity_map = ParticipantIdentityService.for_match_participants(
            tournament,
            participant_ids,
        )
        team_map = {}
        if is_team:
            if participant_ids:
                try:
                    from apps.organizations.models.team import Team as OrgTeam
                    teams = OrgTeam.objects.filter(
                        id__in=participant_ids
                    ).select_related('organization')
                    for t in teams:
                        logo_url = ''
                        try:
                            if t.logo:
                                logo_url = t.logo.url
                            elif t.organization and getattr(t.organization, 'enforce_brand', False) and getattr(t.organization, 'logo', None):
                                logo_url = t.organization.logo.url
                        except (ValueError, Exception):
                            pass
                        team_map[t.id] = {
                            'name': t.name,
                            'tag': t.tag or '',
                            'logo_url': logo_url,
                        }
                except Exception:
                    pass

        # For double elimination, annotate GF / GFR nodes so the frontend
        # can render them with special labels and visual treatment.
        is_double_elim = (bracket.format == Bracket.DOUBLE_ELIMINATION)
        gf_round = gfr_round = None
        if is_double_elim:
            bstruct = bracket.bracket_structure or {}
            wb_rounds = bstruct.get("wb_rounds", 0)
            if wb_rounds:
                gf_round = wb_rounds + 1
                gfr_round = wb_rounds + 2

        def _annotate(n):
            data = TOCBracketsService._serialize_node(
                n,
                team_map=team_map,
                is_team=is_team,
                identity_map=identity_map,
            )
            if gf_round and n.bracket_type == BracketNode.MAIN:
                data["is_gf"] = n.round_number == gf_round
                data["is_gf_reset"] = n.round_number == gfr_round
            else:
                data["is_gf"] = False
                data["is_gf_reset"] = False
            return data

        current_stage = None
        if hasattr(tournament, 'get_current_stage'):
            current_stage = tournament.get_current_stage()

        return {
            "exists": True,
            "bracket": TOCBracketsService._serialize_bracket(bracket),
            "visualization": viz,
            "nodes": [_annotate(n) for n in nodes],
            "current_stage": current_stage,
        }

    @staticmethod
    def reorder_seeds(tournament, seeds: List[Dict], user) -> Dict[str, Any]:
        """Reorder seeding — expects [{registration_id, seed}] list."""
        bracket = Bracket.objects.filter(tournament=tournament).first()
        if not bracket:
            raise ValueError("No bracket exists. Generate first.")
        if bracket.is_finalized:
            raise ValueError("Cannot reorder seeds on a published bracket.")

        seed_map = {s["registration_id"]: s["seed"] for s in seeds}
        BracketService.apply_seeding(
            tournament_id=tournament.id,
            seeding_map=seed_map,
        )
        return {"status": "reordered", "count": len(seeds)}

    # ── Group Stage ────────────────────────────────────────────

    @staticmethod
    def get_groups(tournament) -> Dict[str, Any]:
        """Get group stage configuration and groups."""
        stage = GroupStage.objects.filter(tournament=tournament).first()
        if not stage:
            return {"exists": False, "stage": None, "groups": []}

        groups = list(Group.objects.filter(
            tournament=tournament, is_deleted=False
        ).order_by("display_order"))
        group_ids = {g.id for g in groups}
        match_stats = TOCBracketsService._group_stage_match_stats(tournament, group_ids)

        standings_qs = GroupStanding.objects.filter(
            group__in=groups,
            is_deleted=False,
        ).select_related('group', 'user').order_by('group_id', 'rank')
        standings = list(standings_qs)

        team_ids = {s.team_id for s in standings if s.team_id}
        team_name_map: Dict[int, str] = {}
        if team_ids:
            try:
                from apps.organizations.models.team import Team as OrgTeam

                teams = OrgTeam.objects.filter(id__in=team_ids).only('id', 'name')
                for team in teams:
                    team_name_map[team.id] = team.name
            except Exception:
                pass

        registration_name_map: Dict[int, str] = {}
        missing_team_ids = team_ids - set(team_name_map.keys())
        if missing_team_ids:
            try:
                name_rows = (
                    Registration.objects.filter(
                        tournament=tournament,
                        team_id__in=missing_team_ids,
                        is_deleted=False,
                    )
                    .exclude(display_name_override='')
                    .values_list('team_id', 'display_name_override')
                )
                for team_id, display_name in name_rows:
                    if team_id and display_name:
                        registration_name_map[int(team_id)] = display_name
            except Exception:
                pass

        standings_by_group: Dict[int, List[Dict[str, Any]]] = {}
        has_drawn_assignments = False
        for standing in standings:
            has_drawn_assignments = True

            display_name = '—'
            if standing.team_id:
                display_name = (
                    team_name_map.get(standing.team_id)
                    or registration_name_map.get(standing.team_id)
                    or f'Team {standing.team_id}'
                )
            elif getattr(standing, 'user', None):
                user = standing.user
                display_name = getattr(user, 'username', '') or str(standing.user_id)
            elif standing.user_id:
                display_name = str(standing.user_id)

            standings_by_group.setdefault(standing.group_id, []).append({
                "id": standing.id,
                "rank": standing.rank,
                "team_id": standing.team_id,
                "team_name": display_name,
                "user_id": standing.user_id,
                "matches_played": standing.matches_played,
                "wins": standing.matches_won,
                "draws": standing.matches_drawn,
                "losses": standing.matches_lost,
                "points": float(standing.points) if standing.points else 0,
                "goals_for": standing.goals_for,
                "goals_against": standing.goals_against,
                "goal_difference": standing.goal_difference,
                "is_advancing": standing.is_advancing,
                "is_eliminated": standing.is_eliminated,
            })

        result_groups = []
        total_matches = 0
        total_completed = 0
        for g in groups:
            group_standings = standings_by_group.get(g.id, [])

            g_stats = match_stats.get(g.id, {"total": 0, "completed": 0})
            g_total = int(g_stats.get("total") or 0)
            g_completed = int(g_stats.get("completed") or 0)
            is_completed = g_total > 0 and g_completed == g_total
            total_matches += g_total
            total_completed += g_completed

            result_groups.append({
                "id": str(g.id),
                "name": g.name,
                "display_order": g.display_order,
                "max_participants": g.max_participants,
                "advancement_count": g.advancement_count,
                "is_finalized": is_completed,
                "is_drawn": g.is_finalized,
                "matches_total": g_total,
                "matches_completed": g_completed,
                "standings": group_standings,
            })

        stage_state = stage.state
        # Backfill draw state if standings exist but stage flag is stale (e.g. legacy/live-draw flows).
        if stage_state not in ("active", "completed") and has_drawn_assignments:
            stage_state = "active"

        return {
            "exists": True,
            "stage": {
                "id": str(stage.id),
                "name": stage.name,
                "num_groups": stage.num_groups,
                "group_size": stage.group_size,
                "format": stage.format,
                "state": stage_state,
                "advancement_count_per_group": stage.advancement_count_per_group,
                "draw_audit": (stage.config or {}).get("draw_audit"),
                "matches_total": total_matches,
                "matches_completed": total_completed,
            },
            "matches_total": total_matches,
            "matches_completed": total_completed,
            "groups": result_groups,
        }

    @staticmethod
    def configure_groups(tournament, data: Dict, user) -> Dict[str, Any]:
        """Configure group stage settings."""
        num_groups = data.get("num_groups", 4)
        group_size = data.get("group_size", 4)
        match_format = data.get("format", "round_robin")
        advancement_count = data.get("advancement_count", 2)

        groups = GroupStageService.configure_groups(
            tournament_id=tournament.id,
            num_groups=num_groups,
            match_format=match_format,
            advancement_count=advancement_count,
        )

        # Create or update GroupStage record (the TOC UI queries this)
        stage, _ = GroupStage.objects.update_or_create(
            tournament=tournament,
            defaults={
                'name': 'Group Stage',
                'num_groups': num_groups,
                'group_size': group_size,
                'format': match_format,
                'state': 'pending',
                'advancement_count_per_group': advancement_count,
            }
        )
        return TOCBracketsService.get_groups(tournament)

    @staticmethod
    def draw_groups(tournament, data: Dict, user) -> Dict[str, Any]:
        """Execute group draw.

        Sprint 29: Added re-draw guard — prevents accidental
        destruction of already-drawn groups.
        """
        draw_method = data.get("method", "random")
        stage = GroupStage.objects.filter(tournament=tournament).first()
        if not stage:
            raise ValueError("Configure groups first.")
        if stage.state in ('active', 'completed'):
            raise ValueError(
                "Groups have already been drawn (stage is "
                f"'{stage.state}'). Reset the group stage before "
                "re-drawing."
            )

        GroupStageService.draw_groups(
            tournament_id=tournament.id,
            draw_method=draw_method,
        )
        # Update stage state
        stage.state = 'active'
        stage.save(update_fields=['state'])

        notify_participants = bool(data.get("notify_participants", True))
        force_email = bool(data.get("force_email", notify_participants))

        # Fire auto-notification for group draw completion
        if notify_participants:
            try:
                from apps.tournaments.api.toc.notifications_service import TOCNotificationsService
                TOCNotificationsService.fire_auto_event(
                    tournament,
                    "group_draw_completed",
                    {
                        "force_email": force_email,
                        "dedupe": False,
                        "url": f"/tournaments/{tournament.slug}/hub/",
                    },
                )
            except Exception:
                pass
        return TOCBracketsService.get_groups(tournament)

    @staticmethod
    def generate_group_matches(tournament, data: Dict, user) -> Dict[str, Any]:
        """Generate round-robin matches for drawn groups."""
        stage = GroupStage.objects.filter(tournament=tournament).first()
        if not stage:
            raise ValueError("Configure groups first.")

        groups_snapshot = TOCBracketsService.get_groups(tournament)
        groups = groups_snapshot.get("groups", [])
        if not groups:
            raise ValueError("No groups configured.")

        stage_snapshot = groups_snapshot.get("stage") or {}
        stage_state = str(stage_snapshot.get("state") or stage.state or "").lower()
        has_drawn_assignments = any(bool(g.get("standings")) for g in groups)
        if stage_state not in ("active", "completed") and not has_drawn_assignments:
            raise ValueError("Draw groups first, then generate matches.")

        stage_group_ids = {
            TOCBracketsService._coerce_group_id(g.get("id"))
            for g in groups
            if g.get("id") is not None
        }
        stage_group_ids.discard(None)
        existing_group_match_ids = TOCBracketsService._group_stage_match_ids(tournament, stage_group_ids)
        existing_total = len(existing_group_match_ids)

        allow_regenerate = bool(data.get("allow_regenerate", False))
        if existing_total > 0:
            if not allow_regenerate:
                raise ValueError(
                    "Group matches already exist. Use Re-Generate Matches to replace the current schedule."
                )
            Match.objects.filter(id__in=existing_group_match_ids).delete()

        default_rounds = 2 if (stage.format or "").lower() == "double_round_robin" else 1
        rounds = int(data.get("rounds") or default_rounds)
        if rounds not in (1, 2):
            raise ValueError("rounds must be 1 or 2.")

        diagnostics = TOCBracketsService._group_generation_diagnostics(groups, rounds)
        if diagnostics["ready_group_count"] <= 0:
            blocked = diagnostics.get("blocked_groups") or []
            if blocked:
                raise GroupMatchGenerationError(
                    blocked[0].get("reason") or "No groups are eligible for match generation.",
                    details=diagnostics,
                    code="group_generation_blocked",
                )
            raise GroupMatchGenerationError(
                "No active groups with at least 2 participants were found.",
                details=diagnostics,
                code="group_generation_blocked",
            )

        generated = GroupStageService.generate_group_matches(stage.id, rounds=rounds)
        if generated <= 0:
            blocked = diagnostics.get("blocked_groups") or []
            if blocked:
                raise GroupMatchGenerationError(
                    blocked[0].get("reason") or "No matches were generated due to invalid group rosters.",
                    details=diagnostics,
                    code="group_generation_zero_output",
                )
            raise GroupMatchGenerationError(
                "No matches were generated even though groups appear eligible. Reset and draw groups again, then retry.",
                details=diagnostics,
                code="group_generation_zero_output",
            )

        if stage.state != "active":
            stage.state = "active"
            stage.save(update_fields=["state"])

        return {
            "status": "generated",
            "generated_matches": generated,
            "rounds": rounds,
            "generation_summary": diagnostics,
            "groups": TOCBracketsService.get_groups(tournament).get("groups", []),
        }

    @staticmethod
    def reset_groups(tournament, user) -> Dict[str, Any]:
        """Reset group draw — clears standings and returns stage to pending.

        Sprint 29: Allows re-drawing groups after reset.
        """
        stage = GroupStage.objects.filter(tournament=tournament).first()
        if not stage:
            raise ValueError("No group stage configured.")

        # Clear all standings
        GroupStanding.objects.filter(
            group__tournament=tournament,
        ).delete()

        # Reset group draw markers on active groups.
        Group.objects.filter(tournament=tournament, is_deleted=False).update(is_finalized=False)

        # Clear only generated group-stage matches tied to current groups.
        group_ids = set(
            Group.objects.filter(tournament=tournament, is_deleted=False).values_list("id", flat=True)
        )
        group_match_ids = TOCBracketsService._group_stage_match_ids(tournament, group_ids)
        if group_match_ids:
            Match.objects.filter(id__in=group_match_ids).delete()

        # Reset stage state
        stage.state = 'pending'
        stage.config = {
            k: v for k, v in (stage.config or {}).items()
            if k != 'draw_audit'
        }
        stage.save(update_fields=['state', 'config'])

        return {
            "status": "reset",
            "message": "Group draw reset. You can now re-draw.",
        }

    @staticmethod
    def get_group_standings(tournament) -> Dict[str, Any]:
        """Get all group standings."""
        stage = GroupStage.objects.filter(tournament=tournament).first()
        if not stage:
            return {"groups": []}
        try:
            standings = GroupStageService.calculate_group_standings(stage.id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"calculate_group_standings failed for stage {stage.id}: {e}"
            )
            standings = {}
        return {"groups": standings}

    # ── Schedule ──────────────────────────────────────────────

    @staticmethod
    def get_schedule(tournament) -> Dict[str, Any]:
        """
        Full schedule: all matches with times, stations, status,
        group names, conflict detection, and summary statistics.

        Sprint 27: Enhanced with conflict detection, group info,
        per-day breakdown, and estimated completion time.
        """
        matches_qs = Match.objects.filter(
            tournament=tournament,
            is_deleted=False,
        ).exclude(
            state=Match.CANCELLED,
        ).only(
            'id',
            'round_number',
            'match_number',
            'participant1_id',
            'participant1_name',
            'participant2_id',
            'participant2_name',
            'participant1_score',
            'participant2_score',
            'state',
            'winner_id',
            'scheduled_time',
            'started_at',
            'completed_at',
            'stream_url',
            'best_of',
            'game_scores',
            'bracket_id',
        ).order_by("scheduled_time", "round_number", "match_number")
        matches = list(matches_qs)

        participant_ids = set()
        for match in matches:
            if match.participant1_id:
                participant_ids.add(match.participant1_id)
            if match.participant2_id:
                participant_ids.add(match.participant2_id)

        # ── Build group lookup (match → group name) ──
        group_lookup = {}
        if participant_ids:
            try:
                standings = GroupStanding.objects.filter(
                    group__tournament=tournament,
                ).filter(
                    Q(team_id__in=participant_ids) | Q(user_id__in=participant_ids)
                ).select_related('group').only('team_id', 'user_id', 'group__name')
                for standing in standings:
                    if standing.team_id:
                        group_lookup[standing.team_id] = standing.group.name
                    if standing.user_id:
                        group_lookup.setdefault(standing.user_id, standing.group.name)
            except Exception:
                pass

        # ── Batch-resolve team names & logos ──
        is_team = tournament.participation_type != 'solo'
        team_map = {}
        if is_team:
            if participant_ids:
                try:
                    from apps.organizations.models.team import Team as OrgTeam
                    teams = OrgTeam.objects.filter(
                        id__in=participant_ids
                    ).select_related('organization')
                    for t in teams:
                        logo_url = ''
                        try:
                            if t.logo:
                                logo_url = t.logo.url
                            elif t.organization and getattr(t.organization, 'enforce_brand', False) and getattr(t.organization, 'logo', None):
                                logo_url = t.organization.logo.url
                        except (ValueError, Exception):
                            pass
                        team_map[t.id] = {
                            'name': t.name,
                            'tag': t.tag or '',
                            'logo_url': logo_url,
                        }
                except Exception:
                    pass

        # ── Serialize matches by round ──
        # Pre-load bracket for round name resolution
        bracket_obj = None
        bracket_ids = {m.bracket_id for m in matches if m.bracket_id}
        if bracket_ids:
            try:
                bracket_obj = Bracket.objects.filter(id__in=bracket_ids).first()
            except Exception:
                pass

        # Canonical knockout labels: route ALL via match_classification so the
        # schedule, TOC matches, HUB schedule, and public detail Matches stay
        # in lockstep.
        from apps.tournaments.services.round_naming import knockout_round_label
        from apps.tournaments.services.match_classification import (
            compute_round_label as _canonical_round_label,
            classify_stage as _canonical_classify_stage,
            tournament_total_rounds as _canonical_total_rounds,
            is_pure_knockout as _is_pure_knockout,
        )
        fmt = (getattr(tournament, 'format', '') or '').lower()
        is_pure_knockout = _is_pure_knockout(fmt)
        bracket_total_rounds = _canonical_total_rounds(tournament, bracket=bracket_obj)

        # Canonical read model — stage/round_number sourced from BracketNode
        # when linked, so knockout semifinal/final matches never leak as
        # group_stage rows.
        from apps.tournaments.services.match_read_model import MatchReadModel
        schedule_read_model = MatchReadModel.for_tournament(tournament)
        schedule_view_by_id = {v['match_id']: v for v in schedule_read_model.list()}

        rounds = {}
        all_serialized = []
        for m in matches:
            canonical_view = schedule_view_by_id.get(m.id) or {}
            rn = canonical_view.get('round_number') or m.round_number or 0
            if rn not in rounds:
                rounds[rn] = []
            serialized = TOCBracketsService._serialize_match_schedule(
                m, team_map=team_map, is_team=is_team
            )
            # Overlay canonical values so schedule/TOC matches/HUB agree.
            serialized["round_number"] = rn
            if canonical_view.get('match_number') is not None:
                serialized["match_number"] = canonical_view['match_number']
            # Canonical participants — node-first. Preserve any team_map
            # display-name enrichment that already ran in _serialize_match_schedule
            # by only overriding when the canonical id differs from the raw id.
            if canonical_view:
                c_p1_id = canonical_view.get('participant1_id')
                c_p2_id = canonical_view.get('participant2_id')
                c_p1_name = canonical_view.get('participant1_name') or ''
                c_p2_name = canonical_view.get('participant2_name') or ''
                c_p1_logo = (
                    canonical_view.get('participant1_logo_url')
                    or canonical_view.get('participant1_avatar_url')
                    or ''
                )
                c_p2_logo = (
                    canonical_view.get('participant2_logo_url')
                    or canonical_view.get('participant2_avatar_url')
                    or ''
                )
                # Only overlay when canonical differs from raw — keeps team_map
                # enrichment (logos/display_name_override) intact.
                if (
                    c_p1_id != m.participant1_id or
                    TOCBracketsService._is_placeholder_name(serialized.get('participant1_name'))
                ):
                    serialized["participant1_id"] = c_p1_id
                    if c_p1_name:
                        serialized["participant1_name"] = c_p1_name
                    if c_p1_logo:
                        serialized["participant1_logo"] = c_p1_logo
                        serialized["participant1_logo_url"] = c_p1_logo
                    # Refresh logo for new id
                    if is_team and team_map and c_p1_id in team_map:
                        serialized["participant1_logo"] = team_map[c_p1_id]['logo_url'] or c_p1_logo
                        serialized["participant1_logo_url"] = team_map[c_p1_id]['logo_url'] or c_p1_logo
                        serialized["participant1_name"] = team_map[c_p1_id]['name']
                if (
                    c_p2_id != m.participant2_id or
                    TOCBracketsService._is_placeholder_name(serialized.get('participant2_name'))
                ):
                    serialized["participant2_id"] = c_p2_id
                    if c_p2_name:
                        serialized["participant2_name"] = c_p2_name
                    if c_p2_logo:
                        serialized["participant2_logo"] = c_p2_logo
                        serialized["participant2_logo_url"] = c_p2_logo
                    if is_team and team_map and c_p2_id in team_map:
                        serialized["participant2_logo"] = team_map[c_p2_id]['logo_url'] or c_p2_logo
                        serialized["participant2_logo_url"] = team_map[c_p2_id]['logo_url'] or c_p2_logo
                        serialized["participant2_name"] = team_map[c_p2_id]['name']
                if c_p1_logo and not serialized.get("participant1_logo"):
                    serialized["participant1_logo"] = c_p1_logo
                    serialized["participant1_logo_url"] = c_p1_logo
                if c_p2_logo and not serialized.get("participant2_logo"):
                    serialized["participant2_logo"] = c_p2_logo
                    serialized["participant2_logo_url"] = c_p2_logo
                if canonical_view.get('winner_id'):
                    serialized["winner_id"] = canonical_view['winner_id']
            gname = group_lookup.get(serialized.get('participant1_id')) or group_lookup.get(serialized.get('participant2_id')) or ""
            serialized["group_name"] = gname
            serialized["stage"] = canonical_view.get('stage') or _canonical_classify_stage(tournament, m)
            serialized["bracket_round_label"] = (
                canonical_view.get('round_label')
                or _canonical_round_label(
                    tournament, m, bracket=bracket_obj,
                    total_rounds=bracket_total_rounds,
                )
                or ''
            )
            serialized["bracket_node_id"] = canonical_view.get('bracket_node_id')
            serialized["source"] = canonical_view.get('source', 'match')
            rounds[rn].append(serialized)
            all_serialized.append(serialized)

        # ── Conflict detection ──
        conflicts = TOCBracketsService._detect_schedule_conflicts(matches)

        # ── Summary statistics ──
        total = len(matches)
        scheduled = sum(1 for m in matches if m.state in ("scheduled", "check_in", "ready"))
        live = sum(1 for m in matches if m.state == "live")
        completed = sum(1 for m in matches if m.state in ("completed", "forfeit"))
        pending = sum(1 for m in matches if m.state == "pending_result")
        disputed = sum(1 for m in matches if m.state == "disputed")

        # Estimated end time (latest scheduled + 1h buffer)
        scheduled_times = [m.scheduled_time for m in matches if m.scheduled_time]
        est_end = None
        if scheduled_times:
            from datetime import timedelta
            est_end = (max(scheduled_times) + timedelta(hours=1)).isoformat()

        # Per-day breakdown
        day_counts = {}
        for m in matches:
            if m.scheduled_time:
                day_key = m.scheduled_time.strftime("%Y-%m-%d")
                day_counts[day_key] = day_counts.get(day_key, 0) + 1

        # Context flags so the frontend can show smarter empty states
        has_bracket = Bracket.objects.filter(tournament=tournament).exists()
        has_groups = Group.objects.filter(tournament=tournament, is_deleted=False).exists()
        current_stage = None
        if hasattr(tournament, 'get_current_stage'):
            current_stage = tournament.get_current_stage()

        # Compute one canonical label per round so the frontend dropdown +
        # timeline header stay in lockstep with TOC matches/cards.
        def _round_label_for(rn: int, sample_matches) -> str:
            if not rn:
                return ""
            if is_pure_knockout:
                return knockout_round_label(rn, bracket_total_rounds) or f"Round {rn}"
            sample = sample_matches[0] if sample_matches else None
            if sample and getattr(sample, 'bracket_id', None) and bracket_obj is not None:
                try:
                    name = bracket_obj.get_round_name(rn) or ""
                    if name:
                        return name
                except Exception:
                    pass
            return f"Round {rn}"

        rounds_payload = []
        for rn, ms in sorted(rounds.items()):
            # Prefer the canonical label/stage already attached to the
            # serialized matches — falls back to _round_label_for only if the
            # bucket is empty (shouldn't happen, but safe).
            if ms:
                round_label = ms[0].get('bracket_round_label') or _round_label_for(rn, [])
                stage_value = ms[0].get('stage') or 'knockout'
            else:
                round_label = _round_label_for(rn, [])
                stage_value = 'knockout' if is_pure_knockout else (
                    'swiss' if fmt == 'swiss' else 'group_stage'
                )
            rounds_payload.append({
                "round": rn,
                "round_label": round_label,
                "stage": stage_value,
                "matches": ms,
            })

        return {
            "total_matches": total,
            "matches": all_serialized,
            "rounds": rounds_payload,
            "summary": {
                "total": total,
                "total_matches": total,
                "scheduled": scheduled,
                "live": live,
                "completed": completed,
                "pending": pending,
                "disputed": disputed,
                "estimated_end": est_end,
                "conflicts": len(conflicts),
                "per_day": [
                    {"date": d, "count": c}
                    for d, c in sorted(day_counts.items())
                ],
            },
            "conflicts": conflicts,
            "current_stage": current_stage,
            "context": {
                "has_bracket": has_bracket,
                "has_groups": has_groups,
            },
        }

    @staticmethod
    def auto_schedule(tournament, data: Dict, user) -> Dict[str, Any]:
        """
        Auto-schedule matches with smart defaults and round-aware boundaries.

        Parameters:
            start_time           — ISO datetime string
            match_duration_minutes — minutes per match (default 60)
            break_minutes        — break between matches (default 15)
            max_concurrent       — parallel matches per slot (default 1)
            round_break_minutes  — extra break between rounds (default 30)
            round_number         — only schedule this round (optional)
            reschedule_existing  — if True, reschedule already-scheduled matches too
        """
        from datetime import timedelta
        from django.utils.dateparse import parse_datetime

        start_time_str = data.get("start_time")
        match_duration = int(data.get("match_duration_minutes", 60))
        break_between = int(data.get("break_minutes", 15))
        max_concurrent = max(1, int(data.get("max_concurrent", 1)))
        round_break = int(data.get("round_break_minutes", 30))
        round_filter = data.get("round_number")
        reschedule_existing = data.get("reschedule_existing", False)
        notify_participants = bool(data.get("notify_participants", True))
        force_email = bool(data.get("force_email", notify_participants))

        # Parse start time with validation
        if start_time_str:
            current_time = parse_datetime(start_time_str)
            if not current_time:
                raise ValueError(f"Invalid start_time format: {start_time_str}. Use ISO 8601 (e.g., 2026-03-15T10:00:00Z).")
            if timezone.is_naive(current_time):
                from django.utils.timezone import make_aware
                current_time = make_aware(current_time)
        else:
            # Default: next full hour from now
            now = timezone.now()
            current_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        # Query matches
        states = ["scheduled"]
        if reschedule_existing:
            states.extend(["check_in", "ready"])

        matches = Match.objects.filter(
            tournament=tournament, state__in=states
        ).order_by("round_number", "match_number")

        if round_filter is not None:
            matches = matches.filter(round_number=round_filter)

        if not matches.exists():
            return {"scheduled": 0, "message": "No matches to schedule. Generate brackets first."}

        match_delta = timedelta(minutes=match_duration + break_between)
        round_delta = timedelta(minutes=round_break)

        matches = list(matches)
        matches_by_round = {}
        for match in matches:
            round_number = match.round_number or 0
            matches_by_round.setdefault(round_number, []).append(match)

        scheduled = 0
        round_starts = {}

        def _match_participant_ids(match_obj):
            ids = set()
            if match_obj.participant1_id:
                ids.add(match_obj.participant1_id)
            if match_obj.participant2_id:
                ids.add(match_obj.participant2_id)
            return ids

        ordered_rounds = sorted(matches_by_round.keys())
        for idx, round_number in enumerate(ordered_rounds):
            round_matches = matches_by_round[round_number]
            round_start = current_time
            round_starts[round_number] = round_start.isoformat()

            # Each slot tracks assigned participants so a participant cannot be
            # scheduled in two concurrent matches.
            slots = []

            for match in round_matches:
                participant_ids = _match_participant_ids(match)
                target_slot = None

                for slot in slots:
                    if slot['count'] >= max_concurrent:
                        continue
                    if participant_ids and slot['participants'].intersection(participant_ids):
                        continue
                    target_slot = slot
                    break

                if target_slot is None:
                    slot_start = round_start + (match_delta * len(slots))
                    target_slot = {
                        'start': slot_start,
                        'count': 0,
                        'participants': set(),
                    }
                    slots.append(target_slot)

                match.scheduled_time = target_slot['start']
                lobby_info, lobby_changed = hydrate_match_lobby_info(
                    match,
                    create_if_missing=True,
                    reset_reminder_marks=True,
                )

                update_fields = ["scheduled_time"]
                if lobby_changed:
                    match.lobby_info = lobby_info
                    update_fields.append("lobby_info")

                match.save(update_fields=update_fields)
                scheduled += 1

                target_slot['count'] += 1
                if participant_ids:
                    target_slot['participants'].update(participant_ids)

            current_time = round_start + (match_delta * len(slots))
            if idx < len(ordered_rounds) - 1:
                current_time += round_delta

        latest_start = max(
            (match.scheduled_time for match in matches if match.scheduled_time),
            default=None,
        )
        est_end = (
            latest_start + timedelta(minutes=match_duration)
            if latest_start
            else current_time
        )

        if scheduled > 0 and notify_participants:
            TOCBracketsService._fire_schedule_generated_event(
                tournament,
                scheduled_count=scheduled,
                round_count=len(round_starts),
                force_email=force_email,
                reason="auto_schedule",
            )

        return {
            "scheduled": scheduled,
            "start_time": round_starts.get(min(round_starts.keys())) if round_starts else None,
            "estimated_end": est_end.isoformat(),
            "round_starts": round_starts,
            "notified_participants": bool(scheduled > 0 and notify_participants),
            "message": f"{scheduled} matches scheduled across {len(round_starts)} round(s).",
        }

    @staticmethod
    def send_match_reminders(tournament, data: Dict, user) -> Dict[str, Any]:
        """Send reminders for upcoming scheduled matches."""
        from datetime import timedelta

        minutes_ahead = int(data.get("minutes_ahead", 30))
        if minutes_ahead < 1 or minutes_ahead > 240:
            raise ValueError("minutes_ahead must be between 1 and 240.")

        include_live = bool(data.get("include_live", False))
        force_email = bool(data.get("force_email", True))

        now = timezone.now()
        window_end = now + timedelta(minutes=minutes_ahead)

        states = [Match.SCHEDULED, Match.CHECK_IN, Match.READY]
        if include_live:
            states.append(Match.LIVE)

        upcoming_matches = Match.objects.filter(
            tournament=tournament,
            is_deleted=False,
            scheduled_time__isnull=False,
            scheduled_time__gte=now,
            scheduled_time__lte=window_end,
            state__in=states,
        ).order_by("scheduled_time", "round_number", "match_number")

        from apps.tournaments.api.toc.notifications_service import TOCNotificationsService

        reminders_sent = 0
        recipients_notified = 0

        for match in upcoming_matches:
            target_user_ids = TOCBracketsService._match_participant_user_ids(tournament, match)
            if not target_user_ids:
                continue

            try:
                scheduled_display = timezone.localtime(match.scheduled_time).strftime("%b %d, %Y %I:%M %p")
            except Exception:
                scheduled_display = str(match.scheduled_time)

            TOCNotificationsService.fire_auto_event(
                tournament,
                "match_ready",
                {
                    "target_user_ids": target_user_ids,
                    "participant1": match.participant1_name or "Participant 1",
                    "participant2": match.participant2_name or "Participant 2",
                    "round_number": match.round_number or 0,
                    "match_number": match.match_number or 0,
                    "scheduled_time": scheduled_display,
                    "minutes_until": minutes_ahead,
                    "force_email": force_email,
                    "dedupe": False,
                    "url": f"/tournaments/{tournament.slug}/hub/",
                },
            )
            reminders_sent += 1
            recipients_notified += len(target_user_ids)

        return {
            "reminders_sent": reminders_sent,
            "recipients_notified": recipients_notified,
            "minutes_ahead": minutes_ahead,
            "message": (
                f"Sent reminders for {reminders_sent} upcoming match(es)."
                if reminders_sent
                else "No upcoming matches found in the selected window."
            ),
        }

    @staticmethod
    def manual_schedule_match(tournament, match_id: int, data: Dict, user) -> Dict[str, Any]:
        """
        Manually schedule a single match — sets time + optional check-in deadline.
        Sprint 27: Distinct from reschedule (no state restriction for unscheduled matches).
        """
        from datetime import timedelta
        from django.utils.dateparse import parse_datetime

        try:
            match = Match.objects.get(id=match_id, tournament=tournament)
        except Match.DoesNotExist:
            raise ValueError("Match not found.")

        new_time_str = data.get("scheduled_time")
        if not new_time_str:
            raise ValueError("scheduled_time is required.")

        new_time = parse_datetime(new_time_str)
        if not new_time:
            raise ValueError("Invalid datetime format.")

        if timezone.is_naive(new_time):
            from django.utils.timezone import make_aware
            new_time = make_aware(new_time)

        match.scheduled_time = new_time

        # Optionally set check-in deadline (e.g., 15 min before)
        check_in_minutes = data.get("check_in_minutes")
        if check_in_minutes and int(check_in_minutes) > 0:
            match.check_in_deadline = new_time - timedelta(minutes=int(check_in_minutes))

        lobby_info, lobby_changed = hydrate_match_lobby_info(
            match,
            create_if_missing=True,
            reset_reminder_marks=True,
        )

        update_fields = ["scheduled_time", "check_in_deadline"]
        if lobby_changed:
            match.lobby_info = lobby_info
            update_fields.append("lobby_info")

        match.save(update_fields=update_fields)

        TOCBracketsService._fire_schedule_generated_event(
            tournament,
            scheduled_count=1,
            round_count=1,
            force_email=False,
            target_user_ids=TOCBracketsService._match_participant_user_ids(tournament, match),
            reason="manual_schedule",
        )

        return {
            "match_id": match.id,
            "scheduled_time": new_time.isoformat(),
            "check_in_deadline": match.check_in_deadline.isoformat() if match.check_in_deadline else None,
            "message": f"Match #{match.match_number} (R{match.round_number}) scheduled.",
        }

    @staticmethod
    def bulk_shift(tournament, data: Dict, user) -> Dict[str, Any]:
        """Bulk shift match times by a delta. Uses single SQL UPDATE."""
        from datetime import timedelta
        from django.db.models import F

        shift_minutes = int(data.get("shift_minutes", 0))
        round_number = data.get("round_number")

        if shift_minutes == 0:
            raise ValueError("shift_minutes must be non-zero.")

        qs = Match.objects.filter(
            tournament=tournament,
            scheduled_time__isnull=False,
        )
        if round_number is not None:
            qs = qs.filter(round_number=round_number)

        delta = timedelta(minutes=shift_minutes)
        count = qs.update(scheduled_time=F('scheduled_time') + delta)

        if count > 0:
            TOCBracketsService._fire_schedule_generated_event(
                tournament,
                scheduled_count=count,
                round_count=1,
                force_email=False,
                reason="bulk_shift",
            )

        return {"shifted": count, "delta_minutes": shift_minutes}

    @staticmethod
    def add_break(tournament, data: Dict, user) -> Dict[str, Any]:
        """Insert a break after a specific round — shifts subsequent matches. Single SQL UPDATE."""
        from datetime import timedelta
        from django.db.models import F

        after_round = int(data.get("after_round", 1))
        break_minutes = int(data.get("break_minutes", 15))
        label = data.get("label", "Break")

        delta = timedelta(minutes=break_minutes)
        count = Match.objects.filter(
            tournament=tournament,
            round_number__gt=after_round,
            scheduled_time__isnull=False,
        ).update(scheduled_time=F('scheduled_time') + delta)

        if count > 0:
            TOCBracketsService._fire_schedule_generated_event(
                tournament,
                scheduled_count=count,
                round_count=1,
                force_email=False,
                reason="add_break",
            )

        return {
            "label": label,
            "after_round": after_round,
            "break_minutes": break_minutes,
            "matches_shifted": count,
        }

    # ── Per-match reschedule ──────────────────────────────────

    @staticmethod
    def reschedule_match(tournament, match_id: int, data: Dict, user) -> Dict[str, Any]:
        """Reschedule a single match to a new time. Sprint 27."""
        from django.utils.dateparse import parse_datetime

        try:
            match = Match.objects.get(id=match_id, tournament=tournament)
        except Match.DoesNotExist:
            raise ValueError("Match not found.")

        if match.state in ("completed", "forfeit", "cancelled"):
            raise ValueError(f"Cannot reschedule a match in '{match.state}' state.")

        new_time_str = data.get("scheduled_time")
        if not new_time_str:
            raise ValueError("scheduled_time is required.")

        new_time = parse_datetime(new_time_str)
        if not new_time:
            raise ValueError("Invalid datetime format.")

        if timezone.is_naive(new_time):
            from django.utils.timezone import make_aware
            new_time = make_aware(new_time)

        old_time = match.scheduled_time
        match.scheduled_time = new_time
        lobby_info, lobby_changed = hydrate_match_lobby_info(
            match,
            create_if_missing=True,
            reset_reminder_marks=True,
        )

        update_fields = ["scheduled_time"]
        if lobby_changed:
            match.lobby_info = lobby_info
            update_fields.append("lobby_info")

        match.save(update_fields=update_fields)

        TOCBracketsService._fire_schedule_generated_event(
            tournament,
            scheduled_count=1,
            round_count=1,
            force_email=False,
            target_user_ids=TOCBracketsService._match_participant_user_ids(tournament, match),
            reason="match_rescheduled",
        )

        return {
            "match_id": match.id,
            "old_time": old_time.isoformat() if old_time else None,
            "new_time": new_time.isoformat(),
            "message": f"Match #{match.match_number} rescheduled.",
        }

    # ── Conflict detection helper ──────────────────────────────

    @staticmethod
    def _detect_schedule_conflicts(matches) -> List[Dict]:
        """
        Detect schedule conflicts where the same team appears in
        two overlapping time slots. Assumes ~60 min match duration.
        Sprint 27.
        """
        from datetime import timedelta

        DEFAULT_DURATION = timedelta(minutes=60)
        conflicts = []
        by_participant = {}

        for m in matches:
            if not m.scheduled_time:
                continue
            start = m.scheduled_time
            end = start + DEFAULT_DURATION
            for pid in [m.participant1_id, m.participant2_id]:
                if pid:
                    by_participant.setdefault(pid, []).append({
                        "match_id": m.id,
                        "match_number": m.match_number,
                        "round_number": m.round_number,
                        "start": start,
                        "end": end,
                    })

        seen_pairs = set()
        for participant_id, slots in by_participant.items():
            slots.sort(key=lambda s: s["start"])
            prev = None
            for current in slots:
                if prev is None:
                    prev = current
                    continue

                if prev["match_id"] != current["match_id"] and prev["end"] > current["start"]:
                    pair_key = tuple(sorted([prev["match_id"], current["match_id"]]))
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        conflicts.append({
                            "match_a": prev["match_id"],
                            "match_b": current["match_id"],
                            "participant_id": participant_id,
                            "overlap_start": max(prev["start"], current["start"]).isoformat(),
                            "overlap_end": min(prev["end"], current["end"]).isoformat(),
                        })

                # Keep the interval that extends furthest right for next overlap checks.
                if current["end"] > prev["end"]:
                    prev = current

        return conflicts

    # ── Qualifier Pipelines ────────────────────────────────────

    @staticmethod
    def list_pipelines(tournament) -> List[Dict]:
        """List qualifier pipelines for a tournament."""
        pipelines = QualifierPipeline.objects.filter(
            tournament=tournament
        ).prefetch_related("stages", "stages__promotion_rules_out")

        return [TOCBracketsService._serialize_pipeline(p) for p in pipelines]

    @staticmethod
    def create_pipeline(tournament, data: Dict, user) -> Dict:
        pipeline = QualifierPipeline.objects.create(
            tournament=tournament,
            name=data["name"],
            description=data.get("description", ""),
        )
        return TOCBracketsService._serialize_pipeline(pipeline)

    @staticmethod
    def update_pipeline(tournament, pipeline_id: str, data: Dict) -> Dict:
        pipeline = QualifierPipeline.objects.get(
            id=pipeline_id, tournament=tournament
        )
        for field in ("name", "description", "status"):
            if field in data:
                setattr(pipeline, field, data[field])
        pipeline.save()
        return TOCBracketsService._serialize_pipeline(pipeline)

    @staticmethod
    def delete_pipeline(tournament, pipeline_id: str):
        QualifierPipeline.objects.filter(
            id=pipeline_id, tournament=tournament
        ).delete()

    # ── Serializers ───────────────────────────────────────────

    @staticmethod
    def _serialize_bracket(bracket) -> Dict:
        return {
            "id": str(bracket.id) if hasattr(bracket.id, "hex") else bracket.id,
            "format": bracket.format,
            "total_rounds": bracket.total_rounds,
            "total_matches": bracket.total_matches,
            "seeding_method": bracket.seeding_method,
            "is_finalized": bracket.is_finalized,
            "generated_at": (
                bracket.generated_at.isoformat() if bracket.generated_at else None
            ),
        }

    @staticmethod
    def _serialize_node(node, team_map=None, is_team=False, identity_map=None) -> Dict:
        # Canonical Match resolution: prefer the linked node.match, then fall
        # back to a coordinate lookup so older data where the FK was never
        # set still surfaces real scores/state. Order: (bracket, round, mNo)
        # → (tournament, round, mNo).
        match_obj = getattr(node, 'match', None)
        if not match_obj and node.bracket_id and node.match_number_in_round:
            try:
                from apps.tournaments.models.match import Match as _Match
                match_obj = _Match.objects.filter(
                    bracket_id=node.bracket_id,
                    round_number=node.round_number,
                    match_number=node.match_number_in_round,
                    is_deleted=False,
                ).first()
                if not match_obj:
                    bracket = getattr(node, 'bracket', None)
                    tournament_id = getattr(bracket, 'tournament_id', None) if bracket else None
                    if tournament_id:
                        match_obj = _Match.objects.filter(
                            tournament_id=tournament_id,
                            round_number=node.round_number,
                            match_number=node.match_number_in_round,
                            is_deleted=False,
                        ).first()
            except Exception:
                match_obj = None

        match_data = None
        if match_obj:
            match_data = {
                "id": match_obj.id,
                "state": match_obj.state,
                "participant1_score": match_obj.participant1_score,
                "participant2_score": match_obj.participant2_score,
                "winner_id": match_obj.winner_id,
                "scheduled_time": (
                    match_obj.scheduled_time.isoformat()
                    if match_obj.scheduled_time
                    else None
                ),
                "best_of": getattr(match_obj, "best_of", 1) or 1,
                "game_scores": TOCBracketsService._safe_game_scores(match_obj),
            }

        # Resolve participant names & logos from team_map (overrides denormalized names)
        p1_id = node.participant1_id or (match_obj.participant1_id if match_obj else None)
        p2_id = node.participant2_id or (match_obj.participant2_id if match_obj else None)
        p1_name = node.participant1_name
        p2_name = node.participant2_name
        if match_obj and TOCBracketsService._is_placeholder_name(p1_name):
            p1_name = match_obj.participant1_name
        if match_obj and TOCBracketsService._is_placeholder_name(p2_name):
            p2_name = match_obj.participant2_name
        p1_logo = ''
        p2_logo = ''
        p1_identity = (identity_map or {}).get(int(p1_id)) if p1_id else None
        p2_identity = (identity_map or {}).get(int(p2_id)) if p2_id else None
        if p1_identity and TOCBracketsService._is_placeholder_name(p1_name):
            p1_name = p1_identity.get('name') or p1_name
        if p2_identity and TOCBracketsService._is_placeholder_name(p2_name):
            p2_name = p2_identity.get('name') or p2_name
        if p1_identity:
            p1_logo = (
                p1_identity.get('logo_url')
                or p1_identity.get('avatar_url')
                or p1_identity.get('image_url')
                or ''
            )
        if p2_identity:
            p2_logo = (
                p2_identity.get('logo_url')
                or p2_identity.get('avatar_url')
                or p2_identity.get('image_url')
                or ''
            )
        p1_tag = ''
        p2_tag = ''
        if is_team and team_map:
            if p1_id and p1_id in team_map:
                info = team_map[p1_id]
                p1_name = info['name']
                p1_logo = info['logo_url'] or p1_logo
                p1_tag = info['tag']
            if p2_id and p2_id in team_map:
                info = team_map[p2_id]
                p2_name = info['name']
                p2_logo = info['logo_url'] or p2_logo
                p2_tag = info['tag']

        return {
            "id": node.id,
            "position": node.position,
            "round_number": node.round_number,
            "match_number": node.match_number_in_round,
            "bracket_type": node.bracket_type,
            "participant1_id": p1_id,
            "participant1_name": p1_name,
            "participant1_logo": p1_logo,
            "participant1_logo_url": p1_logo,
            "participant1_avatar_url": (p1_identity or {}).get('avatar_url') or p1_logo,
            "participant1_tag": p1_tag,
            "participant2_id": p2_id,
            "participant2_name": p2_name,
            "participant2_logo": p2_logo,
            "participant2_logo_url": p2_logo,
            "participant2_avatar_url": (p2_identity or {}).get('avatar_url') or p2_logo,
            "participant2_tag": p2_tag,
            "winner_id": node.winner_id,
            "is_bye": node.is_bye,
            "match": match_data,
        }

    @staticmethod
    def _serialize_standing(s) -> Dict:
        # Sprint 29: Resolve team or user name via OrgTeam (not legacy Team stub)
        display_name = None
        if s.team_id:
            try:
                from apps.organizations.models.team import Team as OrgTeam
                team = OrgTeam.objects.filter(id=s.team_id).values_list('name', flat=True).first()
                display_name = team
            except Exception:
                pass
            if not display_name:
                # Fallback: check Registration for display_name_override
                try:
                    reg = Registration.objects.filter(
                        team_id=s.team_id,
                        tournament=s.group.tournament
                    ).values_list('display_name_override', flat=True).first()
                    display_name = reg
                except Exception:
                    pass
            if not display_name:
                display_name = f'Team {s.team_id}'
        elif hasattr(s, 'user') and s.user:
            display_name = s.user.get_display_name() if hasattr(s.user, 'get_display_name') else str(s.user)
        else:
            display_name = '—'

        return {
            "id": s.id,
            "rank": s.rank,
            "team_id": s.team_id,
            "team_name": display_name,
            "user_id": s.user_id if hasattr(s, "user_id") else None,
            "matches_played": s.matches_played,
            "wins": s.matches_won,
            "draws": s.matches_drawn,
            "losses": s.matches_lost,
            "points": float(s.points) if s.points else 0,
            "goals_for": s.goals_for,
            "goals_against": s.goals_against,
            "goal_difference": s.goal_difference,
            "is_advancing": s.is_advancing,
            "is_eliminated": s.is_eliminated,
        }

    @staticmethod
    def _safe_game_scores(m):
        """
        Always return a normalised list of game-score dicts for the frontend.
        The DB can store either:
          - A list of dicts: [{p1_score, p2_score, ...}]     (canonical)
          - A Valorant-style dict: {"maps": [{team1_rounds, team2_rounds, ...}]}
          - A JSON string of either shape
          - None
        Frontend expects:  [{p1_score: int, p2_score: int, map_name: str, ...}, ...]
        """
        import json as _json
        raw = getattr(m, 'game_scores', None)
        if raw is None:
            return []
        if isinstance(raw, str):
            try:
                raw = _json.loads(raw)
            except (ValueError, TypeError):
                return []
        # Dict with "maps" key → normalise to list
        if isinstance(raw, dict):
            maps = raw.get('maps', [])
            if not isinstance(maps, list):
                return []
            result = []
            for i, mp in enumerate(maps):
                result.append({
                    'game': i + 1,
                    'map_name': mp.get('map_name', ''),
                    'p1_score': mp.get('team1_rounds', 0),
                    'p2_score': mp.get('team2_rounds', 0),
                    'winner_side': mp.get('winner_side', 0),
                })
            return result
        if isinstance(raw, list):
            return raw
        return []

    @staticmethod
    def _serialize_match_schedule(m, team_map=None, is_team=False) -> Dict:
        p1_name = m.participant1_name
        p2_name = m.participant2_name
        p1_logo = ''
        p2_logo = ''
        if is_team and team_map:
            if m.participant1_id and m.participant1_id in team_map:
                p1_name = team_map[m.participant1_id]['name']
                p1_logo = team_map[m.participant1_id]['logo_url']
            if m.participant2_id and m.participant2_id in team_map:
                p2_name = team_map[m.participant2_id]['name']
                p2_logo = team_map[m.participant2_id]['logo_url']
        return {
            "id": m.id,
            "round_number": m.round_number,
            "match_number": m.match_number,
            "participant1_id": m.participant1_id,
            "participant1_name": p1_name,
            "participant1_logo": p1_logo,
            "participant1_logo_url": p1_logo,
            "participant2_id": m.participant2_id,
            "participant2_name": p2_name,
            "participant2_logo": p2_logo,
            "participant2_logo_url": p2_logo,
            "participant1_score": m.participant1_score,
            "participant2_score": m.participant2_score,
            "state": m.state,
            "winner_id": m.winner_id,
            "scheduled_time": (
                m.scheduled_time.isoformat() if m.scheduled_time else None
            ),
            "started_at": m.started_at.isoformat() if m.started_at else None,
            "completed_at": (
                m.completed_at.isoformat() if m.completed_at else None
            ),
            "stream_url": m.stream_url or "",
            "best_of": getattr(m, 'best_of', 1) or 1,
            "game_scores": TOCBracketsService._safe_game_scores(m),
        }

    @staticmethod
    def _serialize_pipeline(pipeline) -> Dict:
        stages = []
        for s in pipeline.stages.all().order_by("order"):
            rules_out = []
            for r in s.promotion_rules_out.all():
                rules_out.append({
                    "id": str(r.id),
                    "to_stage_id": str(r.to_stage_id),
                    "criteria": r.criteria,
                    "value": r.value,
                    "auto_promote": r.auto_promote,
                })
            stages.append({
                "id": str(s.id),
                "name": s.name,
                "format": s.format,
                "max_teams": s.max_teams,
                "order": s.order,
                "tournament_stage_id": (
                    str(s.tournament_stage_id) if s.tournament_stage_id else None
                ),
                "promotion_rules": rules_out,
            })

        return {
            "id": str(pipeline.id),
            "name": pipeline.name,
            "description": pipeline.description,
            "status": pipeline.status,
            "stages": stages,
            "created_at": pipeline.created_at.isoformat(),
        }
