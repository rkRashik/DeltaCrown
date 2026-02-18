"""
Tournament Lifecycle Service — Formal State Machine for Tournament Status Transitions.

Centralizes all status transitions behind a guard-checked state machine.
Every transition validates preconditions, applies the change atomically,
records an audit trail via TournamentVersion, and emits events.

Transition Graph:
    DRAFT  ──→  PUBLISHED  ──→  REGISTRATION_OPEN  ──→  REGISTRATION_CLOSED  ──→  LIVE  ──→  COMPLETED  ──→  ARCHIVED
      │             │                  │                         │                   │              │
      └─────────────┴──────────────────┴─────────────────────────┴───────────────────┘              │
                                         (all) ──→ CANCELLED                                       │
                                                                                                   │
      PENDING_APPROVAL ──→ PUBLISHED  (future: moderation flow)                                    │
      CANCELLED ──→ ARCHIVED                                                                       ▼

Usage:
    from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

    # Manually trigger a transition
    tournament = TournamentLifecycleService.transition(
        tournament_id=42,
        to_status='registration_open',
        actor=request.user,
        reason='Manually opened registration',
    )

    # Auto-advance any tournament whose date thresholds have passed
    results = TournamentLifecycleService.auto_advance_all()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Dict, FrozenSet, List, Optional, Set, Tuple

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.tournaments.models.tournament import Tournament, TournamentVersion

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Transition definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Transition:
    """A single allowed status transition with optional guard and callback."""

    from_status: str
    to_status: str
    guard: Optional[Callable[[Tournament], Optional[str]]] = None
    """Return None to allow the transition, or a human-readable rejection reason."""
    on_enter: Optional[Callable[[Tournament], None]] = None
    """Side-effect executed after status is saved (inside the same txn)."""


# ---------------------------------------------------------------------------
# Guard functions
# ---------------------------------------------------------------------------

def _guard_publish(t: Tournament) -> Optional[str]:
    """Ensure the tournament passes full_clean before publishing."""
    try:
        t.full_clean()
    except ValidationError as e:
        return f"Tournament validation failed: {e}"
    return None


def _guard_open_registration(t: Tournament) -> Optional[str]:
    now = timezone.now()
    if t.registration_start and now < t.registration_start:
        return f"Registration start ({t.registration_start}) is in the future"
    return None


def _guard_close_registration(t: Tournament) -> Optional[str]:
    from apps.tournaments.models.registration import Registration

    count = Registration.objects.filter(
        tournament=t, status='confirmed', is_deleted=False,
    ).count()
    if count < t.min_participants:
        return (
            f"Only {count} confirmed participants — minimum is {t.min_participants}. "
            "Consider cancelling instead."
        )
    return None


def _guard_go_live(t: Tournament) -> Optional[str]:
    from apps.tournaments.models.registration import Registration

    confirmed = Registration.objects.filter(
        tournament=t, status='confirmed', is_deleted=False,
    ).count()
    if confirmed < t.min_participants:
        return (
            f"Only {confirmed} confirmed participants — minimum is {t.min_participants}"
        )
    now = timezone.now()
    if t.tournament_start and now < t.tournament_start:
        return f"Tournament start ({t.tournament_start}) is in the future"
    return None


def _guard_complete(t: Tournament) -> Optional[str]:
    from apps.tournaments.models.match import Match

    incomplete = Match.objects.filter(
        tournament=t, is_deleted=False,
    ).exclude(
        state__in=['completed', 'cancelled', 'no_show', 'bye'],
    )
    if incomplete.exists():
        return f"{incomplete.count()} match(es) are still incomplete"
    return None


def _guard_archive(t: Tournament) -> Optional[str]:
    # Completed at least 24 h ago (grace period for disputes)
    if t.tournament_end:
        if timezone.now() < t.tournament_end + timezone.timedelta(hours=24):
            return "Cannot archive until 24 hours after tournament end"
    return None


# ---------------------------------------------------------------------------
# On-enter callbacks
# ---------------------------------------------------------------------------

def _on_enter_published(t: Tournament) -> None:
    if not t.published_at:
        t.published_at = timezone.now()
        t.save(update_fields=['published_at'])


def _on_enter_live(t: Tournament) -> None:
    if not t.tournament_start or t.tournament_start > timezone.now():
        # Snap start time to now if it hasn't started yet
        pass  # We leave tournament_start as configured


def _on_enter_completed(t: Tournament) -> None:
    if not t.tournament_end:
        t.tournament_end = timezone.now()
        t.save(update_fields=['tournament_end'])


# ---------------------------------------------------------------------------
# Transition map
# ---------------------------------------------------------------------------

TRANSITIONS: List[Transition] = [
    # Happy path
    Transition(Tournament.DRAFT, Tournament.PUBLISHED, guard=_guard_publish, on_enter=_on_enter_published),
    Transition(Tournament.DRAFT, Tournament.PENDING_APPROVAL),
    Transition(Tournament.PENDING_APPROVAL, Tournament.PUBLISHED, on_enter=_on_enter_published),
    Transition(Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN, guard=_guard_open_registration),
    Transition(Tournament.REGISTRATION_OPEN, Tournament.REGISTRATION_CLOSED, guard=_guard_close_registration),
    Transition(Tournament.REGISTRATION_CLOSED, Tournament.LIVE, guard=_guard_go_live, on_enter=_on_enter_live),
    Transition(Tournament.LIVE, Tournament.COMPLETED, guard=_guard_complete, on_enter=_on_enter_completed),
    Transition(Tournament.COMPLETED, Tournament.ARCHIVED, guard=_guard_archive),

    # Cancellation (any pre-completion state)
    Transition(Tournament.DRAFT, Tournament.CANCELLED),
    Transition(Tournament.PENDING_APPROVAL, Tournament.CANCELLED),
    Transition(Tournament.PUBLISHED, Tournament.CANCELLED),
    Transition(Tournament.REGISTRATION_OPEN, Tournament.CANCELLED),
    Transition(Tournament.REGISTRATION_CLOSED, Tournament.CANCELLED),
    Transition(Tournament.LIVE, Tournament.CANCELLED),

    # Cancelled → archived
    Transition(Tournament.CANCELLED, Tournament.ARCHIVED),

    # Shortcut: DRAFT → REGISTRATION_OPEN (when publish + reg dates already passed)
    Transition(Tournament.DRAFT, Tournament.REGISTRATION_OPEN, guard=_guard_open_registration, on_enter=_on_enter_published),
]

# Build a fast lookup: (from, to) → Transition
_TRANSITION_MAP: Dict[Tuple[str, str], Transition] = {
    (tr.from_status, tr.to_status): tr for tr in TRANSITIONS
}

# Build adjacency for each status → set of reachable statuses
_REACHABLE: Dict[str, FrozenSet[str]] = {}
for _tr in TRANSITIONS:
    _REACHABLE.setdefault(_tr.from_status, set()).add(_tr.to_status)  # type: ignore[arg-type]
_REACHABLE = {k: frozenset(v) for k, v in _REACHABLE.items()}  # type: ignore[assignment]

# Ordered happy-path for auto-advance
HAPPY_PATH: List[str] = [
    Tournament.DRAFT,
    Tournament.PUBLISHED,
    Tournament.REGISTRATION_OPEN,
    Tournament.REGISTRATION_CLOSED,
    Tournament.LIVE,
    Tournament.COMPLETED,
    Tournament.ARCHIVED,
]


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class TournamentLifecycleService:
    """
    Centralised state-machine service for tournament lifecycle management.

    All status changes MUST go through ``transition()`` to guarantee:
    - The transition is in the allowed graph
    - Guard conditions are satisfied
    - An audit version is created
    - On-enter side-effects fire inside the same DB transaction
    """

    # ── public helpers ──────────────────────────────────────────────────

    @staticmethod
    def allowed_transitions(tournament: Tournament) -> FrozenSet[str]:
        """Return the set of statuses this tournament may transition to."""
        return _REACHABLE.get(tournament.status, frozenset())

    @staticmethod
    def can_transition(tournament: Tournament, to_status: str) -> Tuple[bool, Optional[str]]:
        """
        Check whether a transition is possible without applying it.

        Returns:
            (True, None) if the transition is valid and guards pass.
            (False, reason) otherwise.
        """
        key = (tournament.status, to_status)
        tr = _TRANSITION_MAP.get(key)
        if tr is None:
            return False, f"No transition from '{tournament.status}' → '{to_status}'"
        if tr.guard:
            reason = tr.guard(tournament)
            if reason:
                return False, reason
        return True, None

    # ── core transition ────────────────────────────────────────────────

    @classmethod
    @transaction.atomic
    def transition(
        cls,
        tournament_id: int,
        to_status: str,
        *,
        actor=None,
        reason: str = '',
        force: bool = False,
    ) -> Tournament:
        """
        Apply a status transition to a tournament.

        Args:
            tournament_id: PK of the tournament.
            to_status: Desired target status string.
            actor: User performing the action (None for system/Celery).
            reason: Human-readable note for the audit trail.
            force: If True, skip guard checks (staff emergency override).

        Returns:
            The tournament with its new status.

        Raises:
            Tournament.DoesNotExist: if no tournament with that PK.
            ValidationError: if the transition is not allowed or guard fails.
        """
        tournament = Tournament.objects.select_for_update().get(id=tournament_id)
        from_status = tournament.status

        # Lookup transition
        key = (from_status, to_status)
        tr = _TRANSITION_MAP.get(key)
        if tr is None:
            raise ValidationError(
                f"Invalid transition: '{from_status}' → '{to_status}'. "
                f"Allowed targets: {_REACHABLE.get(from_status, set())}"
            )

        # Guard check (skip if force)
        if not force and tr.guard:
            rejection = tr.guard(tournament)
            if rejection:
                raise ValidationError(
                    f"Transition blocked ({from_status} → {to_status}): {rejection}"
                )

        # Apply
        tournament.status = to_status
        tournament.save(update_fields=['status'])

        # On-enter side-effects
        if tr.on_enter:
            tr.on_enter(tournament)

        # Audit trail
        actor_label = getattr(actor, 'username', 'system')
        summary = f"Status: {from_status} → {to_status} (by {actor_label})"
        if reason:
            summary += f" — {reason}"
        cls._create_version(tournament, actor, summary)

        logger.info(
            "Tournament %s (%s) transitioned: %s → %s [actor=%s]",
            tournament.id, tournament.name, from_status, to_status, actor_label,
        )

        return tournament

    # ── auto-advance (date-driven) ─────────────────────────────────────

    @classmethod
    def auto_advance(cls, tournament: Tournament) -> Optional[str]:
        """
        Advance a single tournament along the happy path if its date
        thresholds have been reached.

        Returns:
            The new status string if a transition happened, else None.
        """
        now = timezone.now()
        status = tournament.status

        # PUBLISHED → REGISTRATION_OPEN  (when registration_start is past)
        if status == Tournament.PUBLISHED:
            if tournament.registration_start and now >= tournament.registration_start:
                try:
                    cls.transition(tournament.id, Tournament.REGISTRATION_OPEN, reason='Auto: registration window opened')
                    return Tournament.REGISTRATION_OPEN
                except ValidationError as e:
                    logger.warning("Auto-advance PUBLISHED→REG_OPEN failed for %s: %s", tournament.id, e)
            return None

        # REGISTRATION_OPEN → REGISTRATION_CLOSED  (when registration_end is past)
        if status == Tournament.REGISTRATION_OPEN:
            if tournament.registration_end and now >= tournament.registration_end:
                try:
                    cls.transition(tournament.id, Tournament.REGISTRATION_CLOSED, reason='Auto: registration window closed')
                    return Tournament.REGISTRATION_CLOSED
                except ValidationError as e:
                    logger.warning("Auto-advance REG_OPEN→REG_CLOSED failed for %s: %s", tournament.id, e)
            return None

        # REGISTRATION_CLOSED → LIVE  (when tournament_start is past)
        if status == Tournament.REGISTRATION_CLOSED:
            if tournament.tournament_start and now >= tournament.tournament_start:
                try:
                    cls.transition(tournament.id, Tournament.LIVE, reason='Auto: tournament started')
                    return Tournament.LIVE
                except ValidationError as e:
                    logger.warning("Auto-advance REG_CLOSED→LIVE failed for %s: %s", tournament.id, e)
            return None

        return None

    @classmethod
    def auto_advance_all(cls) -> Dict[str, int]:
        """
        Scan all active tournaments and auto-advance any whose date
        thresholds have passed.

        Intended to be called by a periodic Celery task.

        Returns:
            Dict with keys = new_status, values = count of tournaments advanced.
        """
        results: Dict[str, int] = {}
        advanceable_statuses = [
            Tournament.PUBLISHED,
            Tournament.REGISTRATION_OPEN,
            Tournament.REGISTRATION_CLOSED,
        ]
        qs = Tournament.objects.filter(
            status__in=advanceable_statuses,
            is_deleted=False,
        ).order_by('tournament_start')

        for t in qs.iterator():
            new_status = cls.auto_advance(t)
            if new_status:
                results[new_status] = results.get(new_status, 0) + 1

        if results:
            logger.info("Auto-advance results: %s", results)
        return results

    # ── internals ──────────────────────────────────────────────────────

    @staticmethod
    def _create_version(tournament: Tournament, actor, summary: str) -> TournamentVersion:
        latest = tournament.versions.order_by('-version_number').first()
        next_num = (latest.version_number + 1) if latest else 1
        return TournamentVersion.objects.create(
            tournament=tournament,
            version_number=next_num,
            version_data={
                'status': tournament.status,
                'timestamp': timezone.now().isoformat(),
            },
            change_summary=summary,
            changed_by=actor,
        )
