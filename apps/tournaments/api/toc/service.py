"""
TOC Service Layer — Command Center Wrapper.

Wraps existing CommandCenterService, TournamentLifecycleService, and model
queries into structured DTOs consumable by the TOC API. This is the ONLY layer
the TOC API views call — never touch models directly from views.

Sprint 1: S1-S1 (overview assembly), S1-S2 (transition validation), S1-S3 (killswitch)
PRD: §2.1–§2.7
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.tournaments.models.tournament import Tournament, TournamentVersion
from apps.tournaments.models.registration import Registration
from apps.tournaments.models.match import Match
from apps.tournaments.models.dispute import DisputeRecord
from apps.tournaments.models.payment_verification import PaymentVerification
from apps.tournaments.services.command_center_service import CommandCenterService
from apps.tournaments.services.lifecycle_service import TournamentLifecycleService

logger = logging.getLogger(__name__)


class TOCService:
    """
    High-level service for the Tournament Operations Center.

    All public methods are @classmethod and return plain dicts/lists
    (no model instances leak into the API layer).
    """

    # ── S1-S1: Overview Assembly ──────────────────────────────────────

    @classmethod
    def get_overview(cls, tournament: Tournament) -> Dict[str, Any]:
        """
        Assemble the full overview payload for the Command Center tab.

        Returns a dict matching OverviewSerializer shape:
        {status, status_display, is_frozen, freeze_reason, lifecycle, stats, alerts, events, transitions}
        """
        # Gather raw stats from DB
        reg_stats = cls._get_registration_stats(tournament)
        payment_stats = cls._get_payment_stats(tournament)
        dispute_stats = cls._get_dispute_stats(tournament)
        match_stats = cls._get_match_stats(tournament)

        # Lifecycle progress from existing service
        lifecycle = CommandCenterService.get_lifecycle_progress(tournament)

        # Alerts from existing service (inject synthetic IDs)
        raw_alerts = CommandCenterService.get_alerts(
            tournament, reg_stats, payment_stats, dispute_stats, match_stats,
        )
        alerts = [
            {**alert, 'id': idx}
            for idx, alert in enumerate(raw_alerts)
        ]

        # Upcoming events from existing service
        events = CommandCenterService.get_upcoming_events(tournament)

        # Stat cards for 4-column grid
        stats = cls._build_stat_cards(tournament, reg_stats, payment_stats, match_stats, dispute_stats)

        # Valid transitions from current state
        transitions = cls._get_transitions(tournament)

        # Frozen state (via config JSONB — proper check)
        is_frozen = cls.is_frozen(tournament)
        freeze_reason = ''
        if is_frozen:
            config = tournament.config or {}
            freeze_data = config.get('frozen', {})
            freeze_reason = freeze_data.get('reason', '') if isinstance(freeze_data, dict) else ''

        return {
            'status': tournament.status,
            'status_display': tournament.get_status_display(),
            'is_frozen': is_frozen,
            'freeze_reason': freeze_reason,
            'lifecycle': lifecycle,
            'stats': stats,
            'alerts': alerts,
            'events': events,
            'transitions': transitions,
        }

    # ── S1-S2: Transition Validation & Execution ──────────────────────

    @classmethod
    def get_transitions(cls, tournament: Tournament) -> List[Dict[str, Any]]:
        """Public alias for view-level access."""
        return cls._get_transitions(tournament)

    @classmethod
    def execute_transition(
        cls,
        tournament: Tournament,
        to_status: str,
        actor,
        reason: str = '',
        force: bool = False,
    ) -> Tournament:
        """
        Execute a lifecycle transition via the formal state machine.

        Delegates to TournamentLifecycleService.transition() which handles:
        - Transition graph validation
        - Guard condition checks
        - Atomic status update + version audit

        Returns the updated tournament.
        Raises ValidationError if transition is not allowed.
        """
        return TournamentLifecycleService.transition(
            tournament_id=tournament.id,
            to_status=to_status,
            actor=actor,
            reason=reason,
            force=force,
        )

    # ── S1-S3: Killswitch (Freeze / Unfreeze) ────────────────────────

    @classmethod
    @transaction.atomic
    def freeze_tournament(cls, tournament: Tournament, actor, reason: str) -> Tournament:
        """
        Execute a Global Killswitch freeze.

        PRD §2.7: Immediately freeze tournament, pause all timers,
        broadcast emergency.

        NOTE: The Tournament model doesn't yet have a FROZEN status or
        frozen_at/frozen_by fields (PRD §2.7 DATA MODEL ADDITIONS).
        For Sprint 1, we simulate freeze by storing data in config JSONB
        and emit a version audit. Model migration will come in Sprint 10+.
        """
        t = Tournament.objects.select_for_update().get(id=tournament.id)

        if t.status not in ('live', 'registration_open', 'registration_closed'):
            raise ValidationError(
                f"Cannot freeze tournament in '{t.status}' state. "
                "Freeze is only available for live/registration phases."
            )

        now = timezone.now()
        config = t.config or {}
        config['frozen'] = {
            'frozen_at': now.isoformat(),
            'frozen_by_id': actor.id,
            'frozen_by_username': actor.username,
            'reason': reason,
            'previous_status': t.status,
        }
        t.config = config
        t.save(update_fields=['config'])

        # Audit trail
        cls._create_version(
            t, actor,
            f"FREEZE: {t.status} → FROZEN (by {actor.username}) — {reason}"
        )

        logger.warning(
            "Tournament %s (%s) FROZEN by %s: %s",
            t.id, t.name, actor.username, reason,
        )

        return t

    @classmethod
    @transaction.atomic
    def unfreeze_tournament(cls, tournament: Tournament, actor, reason: str = '') -> Tournament:
        """
        Lift a Global Killswitch freeze.

        PRD §2.7: Resume timers, clear freeze state, recalculate deadlines.
        """
        t = Tournament.objects.select_for_update().get(id=tournament.id)
        config = t.config or {}
        freeze_data = config.get('frozen')

        if not freeze_data:
            raise ValidationError("Tournament is not currently frozen.")

        # Calculate duration
        frozen_at_str = freeze_data.get('frozen_at', '')
        if frozen_at_str:
            from django.utils.dateparse import parse_datetime
            frozen_at = parse_datetime(frozen_at_str)
            if frozen_at:
                duration = (timezone.now() - frozen_at).total_seconds()
                # Accumulate freeze duration
                config['total_freeze_seconds'] = config.get('total_freeze_seconds', 0) + duration

        # Clear freeze
        del config['frozen']
        t.config = config
        t.save(update_fields=['config'])

        summary = f"UNFREEZE (by {actor.username})"
        if reason:
            summary += f" — {reason}"
        cls._create_version(t, actor, summary)

        logger.info(
            "Tournament %s (%s) UNFROZEN by %s",
            t.id, t.name, actor.username,
        )

        return t

    @classmethod
    def is_frozen(cls, tournament: Tournament) -> bool:
        """Check if tournament is currently frozen (via config JSONB)."""
        config = tournament.config or {}
        return bool(config.get('frozen'))

    # ── Private Helpers ───────────────────────────────────────────────

    @classmethod
    def _get_registration_stats(cls, tournament: Tournament) -> Dict[str, int]:
        qs = Registration.objects.filter(tournament=tournament, is_deleted=False)
        return {
            'total': qs.count(),
            'confirmed': qs.filter(status=Registration.CONFIRMED).count(),
            'pending': qs.filter(
                status__in=[
                    Registration.PENDING,
                    Registration.NEEDS_REVIEW,
                    Registration.SUBMITTED,
                ]
            ).count(),
            'waitlisted': qs.filter(status=Registration.WAITLISTED).count(),
        }

    @classmethod
    def _get_payment_stats(cls, tournament: Tournament) -> Dict[str, int]:
        qs = PaymentVerification.objects.filter(
            registration__tournament=tournament,
        )
        return {
            'total': qs.count(),
            'verified': qs.filter(status=PaymentVerification.Status.VERIFIED).count(),
            'pending': qs.filter(status=PaymentVerification.Status.PENDING).count(),
        }

    @classmethod
    def _get_dispute_stats(cls, tournament: Tournament) -> Dict[str, int]:
        qs = DisputeRecord.objects.filter(
            submission__match__tournament=tournament,
        )
        return {
            'total': qs.count(),
            'open': qs.filter(status=DisputeRecord.OPEN).count(),
            'under_review': qs.filter(status=DisputeRecord.UNDER_REVIEW).count(),
            'resolved': qs.filter(
                status__in=[
                    DisputeRecord.RESOLVED_FOR_SUBMITTER,
                    DisputeRecord.RESOLVED_FOR_OPPONENT,
                ]
            ).count(),
        }

    @classmethod
    def _get_match_stats(cls, tournament: Tournament) -> Dict[str, int]:
        qs = Match.objects.filter(tournament=tournament, is_deleted=False)
        return {
            'total': qs.count(),
            'live': qs.filter(state=Match.LIVE).count(),
            'completed': qs.filter(state=Match.COMPLETED).count(),
            'scheduled': qs.filter(state=Match.SCHEDULED).count(),
        }

    @classmethod
    def _build_stat_cards(
        cls,
        tournament: Tournament,
        reg_stats: Dict[str, int],
        payment_stats: Dict[str, int],
        match_stats: Dict[str, int],
        dispute_stats: Dict[str, int],
    ) -> List[Dict[str, Any]]:
        """Build the 4-column stat card grid for the overview."""
        cap = tournament.max_participants or 0
        cap_label = f"/ {cap} Cap" if cap else ""

        return [
            {
                'key': 'registrations',
                'label': 'Active Roster',
                'value': reg_stats['confirmed'],
                'detail': cap_label,
                'color': 'theme',
            },
            {
                'key': 'payments',
                'label': 'Payments Verified',
                'value': payment_stats['verified'],
                'detail': f"/ {payment_stats['total']} Total" if payment_stats['total'] else '',
                'color': 'success',
            },
            {
                'key': 'matches',
                'label': 'Matches Played',
                'value': match_stats['completed'],
                'detail': f"/ {match_stats['total']} Total" if match_stats['total'] else '',
                'color': 'theme',
            },
            {
                'key': 'disputes',
                'label': 'Active Disputes',
                'value': dispute_stats['open'] + dispute_stats['under_review'],
                'detail': '',
                'color': 'danger' if (dispute_stats['open'] + dispute_stats['under_review']) > 0 else 'theme',
            },
        ]

    @classmethod
    def _get_transitions(cls, tournament: Tournament) -> List[Dict[str, Any]]:
        """Get valid transition targets with guard-check results."""
        allowed = TournamentLifecycleService.allowed_transitions(tournament)
        transitions = []

        # Human-readable labels
        labels = {
            'draft': 'Draft',
            'pending_approval': 'Pending Approval',
            'published': 'Published',
            'registration_open': 'Open Registration',
            'registration_closed': 'Close Registration',
            'live': 'Go Live',
            'completed': 'Mark Completed',
            'cancelled': 'Cancel Tournament',
            'archived': 'Archive',
        }

        for target in sorted(allowed):
            can, reason = TournamentLifecycleService.can_transition(tournament, target)
            transitions.append({
                'to_status': target,
                'label': labels.get(target, target.replace('_', ' ').title()),
                'can_transition': can,
                'reason': reason,
            })

        return transitions

    @staticmethod
    def _create_version(tournament: Tournament, actor, summary: str) -> TournamentVersion:
        latest = tournament.versions.order_by('-version_number').first()
        next_num = (latest.version_number + 1) if latest else 1
        return TournamentVersion.objects.create(
            tournament=tournament,
            version_number=next_num,
            version_data={
                'status': tournament.status,
                'config': tournament.config,
                'timestamp': timezone.now().isoformat(),
            },
            change_summary=summary,
            changed_by=actor,
        )
