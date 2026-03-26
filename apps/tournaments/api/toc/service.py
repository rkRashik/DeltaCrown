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
import time
from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from apps.tournaments.models.tournament import Tournament, TournamentVersion
from apps.tournaments.models.registration import Registration
from apps.tournaments.models.match import Match
from apps.tournaments.models.dispute import DisputeRecord
from apps.tournaments.models.payment_verification import PaymentVerification
from apps.tournaments.models import AuditLog
from apps.tournaments.api.toc.announcements_service import TOCAnnouncementsService
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
        {status, status_display, is_frozen, freeze_reason, lifecycle, stats, alerts, events, transitions,
         health_score, upcoming_matches, group_progress}

        Sprint 27: Added health_score, upcoming_matches, group_progress.
        """
        t0 = time.perf_counter()

        # Gather raw stats from DB
        reg_stats = cls._get_registration_stats(tournament)
        payment_stats = cls._get_payment_stats(tournament)
        dispute_stats = cls._get_dispute_stats(tournament)
        match_stats = cls._get_match_stats(tournament)
        t_stats = time.perf_counter()

        # Lifecycle progress from existing service
        lifecycle = CommandCenterService.get_lifecycle_progress(tournament)
        t_lifecycle = time.perf_counter()

        # Alerts from existing service (inject synthetic IDs)
        raw_alerts = CommandCenterService.get_alerts(
            tournament, reg_stats, payment_stats, dispute_stats, match_stats,
        )
        alerts = [
            {**alert, 'id': idx}
            for idx, alert in enumerate(raw_alerts)
        ]
        t_alerts = time.perf_counter()

        # Upcoming events from existing service
        events = CommandCenterService.get_upcoming_events(tournament)
        t_events = time.perf_counter()

        # Stat cards for 4-column grid
        stats = cls._build_stat_cards(tournament, reg_stats, payment_stats, match_stats, dispute_stats)
        t_cards = time.perf_counter()

        # Valid transitions from current state
        transitions = cls._get_transitions(tournament)
        t_transitions = time.perf_counter()

        # Frozen state (via config JSONB — proper check)
        is_frozen = cls.is_frozen(tournament)
        freeze_reason = ''
        if is_frozen:
            config = tournament.config or {}
            freeze_data = config.get('frozen', {})
            freeze_reason = freeze_data.get('reason', '') if isinstance(freeze_data, dict) else ''

        # S27: Health score — composite 0-100 indicator
        health_score = cls._compute_health_score(
            tournament, reg_stats, payment_stats, match_stats, dispute_stats, alerts,
        )
        t_health = time.perf_counter()

        # S27: Upcoming matches — next 5 scheduled matches
        upcoming_matches = cls._get_upcoming_matches(tournament)
        t_upcoming = time.perf_counter()

        # S27: Group stage progress (if applicable)
        group_progress = cls._get_group_progress(tournament)
        t_group = time.perf_counter()

        # S28: Countdown timers for key milestones
        countdowns = cls._get_countdowns(tournament, upcoming_matches=upcoming_matches)
        t_countdowns = time.perf_counter()

        # S28: Quick-launch actions based on tournament state
        quick_actions = cls._get_quick_actions(tournament)
        t_actions = time.perf_counter()

        # S30: Inline quick stats + recent activity to avoid overview fan-out calls
        quick_stats = cls._build_quick_stats(tournament, reg_stats, match_stats)
        activity_log = cls._get_recent_activity(tournament, limit=25)
        tournament_feed = TOCAnnouncementsService.list_announcements(tournament=tournament)[:12]
        t_final = time.perf_counter()

        elapsed_ms = (t_final - t0) * 1000.0
        if elapsed_ms >= 250:
            logger.info(
                "TOC overview timings tournament_id=%s elapsed_ms=%.2f stats_ms=%.2f lifecycle_ms=%.2f alerts_ms=%.2f events_ms=%.2f cards_ms=%.2f transitions_ms=%.2f health_ms=%.2f upcoming_ms=%.2f group_ms=%.2f countdowns_ms=%.2f actions_ms=%.2f tail_ms=%.2f",
                tournament.id,
                elapsed_ms,
                (t_stats - t0) * 1000.0,
                (t_lifecycle - t_stats) * 1000.0,
                (t_alerts - t_lifecycle) * 1000.0,
                (t_events - t_alerts) * 1000.0,
                (t_cards - t_events) * 1000.0,
                (t_transitions - t_cards) * 1000.0,
                (t_health - t_transitions) * 1000.0,
                (t_upcoming - t_health) * 1000.0,
                (t_group - t_upcoming) * 1000.0,
                (t_countdowns - t_group) * 1000.0,
                (t_actions - t_countdowns) * 1000.0,
                (t_final - t_actions) * 1000.0,
            )

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
            'health_score': health_score,
            'upcoming_matches': upcoming_matches,
            'group_progress': group_progress,
            'countdowns': countdowns,
            'quick_actions': quick_actions,
            'quick_stats': quick_stats,
            'activity_log': activity_log,
            'tournament_feed': tournament_feed,
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

    # ── S27: Health Score ─────────────────────────────────────────────

    @classmethod
    def _compute_health_score(
        cls,
        tournament: Tournament,
        reg_stats: Dict[str, int],
        payment_stats: Dict[str, int],
        match_stats: Dict[str, int],
        dispute_stats: Dict[str, int],
        alerts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Compute a composite 0–100 health score for the tournament.

        Components (weighted):
        - Registration fill rate: 25%
        - Payment verification rate: 20%
        - Match completion rate: 25%
        - Dispute health (inverse of open dispute %): 15%
        - Alert health (fewer critical alerts = better): 15%

        Returns: {score, grade, label, breakdown}
        """
        breakdown = {}
        total_weight = 0

        # 1. Registration fill
        cap = tournament.max_participants or 0
        if cap > 0:
            fill = min(100, round((reg_stats.get('confirmed', 0) / cap) * 100))
        else:
            fill = 100 if reg_stats.get('total', 0) > 0 else 50
        breakdown['registration'] = fill
        total_weight += fill * 25

        # 2. Payment verification
        pay_total = payment_stats.get('total', 0)
        if pay_total > 0:
            pay_score = round((payment_stats.get('verified', 0) / pay_total) * 100)
        else:
            pay_score = 100  # No payments required = perfect
        breakdown['payments'] = pay_score
        total_weight += pay_score * 20

        # 3. Match completion
        match_total = match_stats.get('total', 0)
        if match_total > 0:
            completed = match_stats.get('completed', 0)
            match_score = round((completed / match_total) * 100)
        else:
            match_score = 50  # No matches yet = neutral
        breakdown['matches'] = match_score
        total_weight += match_score * 25

        # 4. Dispute health (inverse)
        dispute_total = dispute_stats.get('total', 0)
        if dispute_total > 0:
            open_disputes = dispute_stats.get('open', 0) + dispute_stats.get('under_review', 0)
            dispute_score = max(0, round(100 - (open_disputes / dispute_total) * 100))
        else:
            dispute_score = 100
        breakdown['disputes'] = dispute_score
        total_weight += dispute_score * 15

        # 5. Alert health
        critical_alerts = sum(1 for a in alerts if a.get('severity') == 'critical')
        warning_alerts = sum(1 for a in alerts if a.get('severity') == 'warning')
        alert_penalty = critical_alerts * 20 + warning_alerts * 5
        alert_score = max(0, 100 - alert_penalty)
        breakdown['alerts'] = alert_score
        total_weight += alert_score * 15

        # Weighted average
        score = round(total_weight / 100)

        # Grade assignment
        if score >= 90:
            grade, label = 'A', 'Excellent'
        elif score >= 75:
            grade, label = 'B', 'Good'
        elif score >= 60:
            grade, label = 'C', 'Fair'
        elif score >= 40:
            grade, label = 'D', 'Needs Attention'
        else:
            grade, label = 'F', 'Critical'

        return {
            'score': score,
            'grade': grade,
            'label': label,
            'breakdown': breakdown,
        }

    # ── S27: Upcoming Matches ─────────────────────────────────────────

    @classmethod
    def _get_upcoming_matches(cls, tournament: Tournament) -> List[Dict[str, Any]]:
        """Return next 5 upcoming scheduled matches for the overview."""
        now = timezone.now()
        upcoming = (
            Match.objects
            .filter(
                tournament=tournament,
                is_deleted=False,
                state__in=[Match.SCHEDULED, 'check_in', 'ready'],
                scheduled_time__gte=now,
            )
            .order_by('scheduled_time')[:5]
        )
        result = []
        for m in upcoming:
            result.append({
                'id': m.id,
                'match_number': m.match_number,
                'round_number': m.round_number,
                'participant1_name': m.participant1_name or 'TBD',
                'participant2_name': m.participant2_name or 'TBD',
                'scheduled_time': m.scheduled_time.isoformat() if m.scheduled_time else None,
                'state': m.state,
            })
        return result

    # ── S27: Group Stage Progress ─────────────────────────────────────

    @classmethod
    def _get_group_progress(cls, tournament: Tournament) -> Optional[Dict[str, Any]]:
        """
        Return a summary of group stage progress if the tournament has groups.
        Returns None if no group stage exists.
        """
        from apps.tournaments.models.group import GroupStage, Group, GroupStanding
        try:
            gs = GroupStage.objects.filter(tournament=tournament).first()
            if not gs:
                return None

            groups = list(
                Group.objects.filter(tournament=tournament)
                .prefetch_related('standings')
                .order_by('name')
            )
            total_groups = len(groups)
            if total_groups == 0:
                return None

            group_matches = list(
                Match.objects.filter(
                    tournament=tournament,
                    is_deleted=False,
                    bracket__isnull=True,
                ).values('participant1_id', 'participant2_id', 'state')
            )

            total_matches = len(group_matches)
            completed_matches = sum(
                1 for m in group_matches
                if m.get('state') in [Match.COMPLETED, 'forfeit']
            )

            # If bracket-based group matches exist, fall back to all tournament matches.
            if total_matches == 0:
                all_matches = list(
                    Match.objects.filter(
                        tournament=tournament,
                        is_deleted=False,
                    ).values('state')
                )
                total_matches = len(all_matches)
                completed_matches = sum(
                    1 for m in all_matches
                    if m.get('state') in [Match.COMPLETED, 'forfeit']
                )

            pct = round((completed_matches / total_matches) * 100) if total_matches > 0 else 0

            group_list = []
            for g in groups[:8]:  # Max 8 groups in overview
                g_standings = [s for s in g.standings.all() if not getattr(s, 'is_deleted', False)]
                g_team_ids = {
                    s.team_id for s in g_standings
                    if getattr(s, 'team_id', None) not in (None, 0)
                }
                g_user_ids = {
                    s.user_id for s in g_standings
                    if getattr(s, 'user_id', None)
                }

                g_total = 0
                g_completed = 0
                for m in group_matches:
                    p1 = m.get('participant1_id')
                    p2 = m.get('participant2_id')

                    if g_team_ids:
                        in_group = p1 in g_team_ids and p2 in g_team_ids
                    elif g_user_ids:
                        in_group = p1 in g_user_ids and p2 in g_user_ids
                    else:
                        in_group = False

                    if in_group:
                        g_total += 1
                        if m.get('state') in [Match.COMPLETED, 'forfeit']:
                            g_completed += 1

                group_list.append({
                    'name': g.name or f'Group {g.id}',
                    'teams': len(g_standings),
                    'matches_total': g_total,
                    'matches_completed': g_completed,
                })

            return {
                'state': gs.state,
                'total_groups': total_groups,
                'total_matches': total_matches,
                'completed_matches': completed_matches,
                'completion_pct': pct,
                'groups': group_list,
            }
        except Exception as e:
            logger.warning("Failed to compute group progress: %s", e)
            return None

    @classmethod
    def _get_registration_stats(cls, tournament: Tournament) -> Dict[str, int]:
        qs = Registration.objects.filter(tournament=tournament, is_deleted=False)
        agg = qs.aggregate(
            total=models.Count('id'),
            confirmed=models.Count('id', filter=models.Q(status=Registration.CONFIRMED)),
            pending=models.Count(
                'id',
                filter=models.Q(
                    status__in=[
                        Registration.PENDING,
                        Registration.NEEDS_REVIEW,
                        Registration.SUBMITTED,
                    ]
                ),
            ),
            waitlisted=models.Count('id', filter=models.Q(status=Registration.WAITLISTED)),
            checked_in=models.Count('id', filter=models.Q(checked_in=True)),
            disqualified=models.Count('id', filter=models.Q(status__in=['rejected', 'no_show'])),
        )
        return {
            'total': agg.get('total') or 0,
            'confirmed': agg.get('confirmed') or 0,
            'pending': agg.get('pending') or 0,
            'waitlisted': agg.get('waitlisted') or 0,
            'checked_in': agg.get('checked_in') or 0,
            'disqualified': agg.get('disqualified') or 0,
        }

    @classmethod
    def _get_payment_stats(cls, tournament: Tournament) -> Dict[str, int]:
        qs = PaymentVerification.objects.filter(
            registration__tournament=tournament,
        )
        agg = qs.aggregate(
            total=models.Count('id'),
            verified=models.Count('id', filter=models.Q(status=PaymentVerification.Status.VERIFIED)),
            pending=models.Count('id', filter=models.Q(status=PaymentVerification.Status.PENDING)),
        )
        return {
            'total': agg.get('total') or 0,
            'verified': agg.get('verified') or 0,
            'pending': agg.get('pending') or 0,
        }

    @classmethod
    def _get_dispute_stats(cls, tournament: Tournament) -> Dict[str, int]:
        qs = DisputeRecord.objects.filter(
            submission__match__tournament=tournament,
        )
        agg = qs.aggregate(
            total=models.Count('id'),
            open=models.Count('id', filter=models.Q(status=DisputeRecord.OPEN)),
            under_review=models.Count('id', filter=models.Q(status=DisputeRecord.UNDER_REVIEW)),
            resolved=models.Count(
                'id',
                filter=models.Q(
                    status__in=[
                        DisputeRecord.RESOLVED_FOR_SUBMITTER,
                        DisputeRecord.RESOLVED_FOR_OPPONENT,
                    ]
                ),
            ),
        )
        return {
            'total': agg.get('total') or 0,
            'open': agg.get('open') or 0,
            'under_review': agg.get('under_review') or 0,
            'resolved': agg.get('resolved') or 0,
        }

    @classmethod
    def _get_match_stats(cls, tournament: Tournament) -> Dict[str, int]:
        qs = Match.objects.filter(tournament=tournament, is_deleted=False)
        agg = qs.aggregate(
            total=models.Count('id'),
            live=models.Count('id', filter=models.Q(state=Match.LIVE)),
            completed=models.Count('id', filter=models.Q(state=Match.COMPLETED)),
            scheduled=models.Count('id', filter=models.Q(state=Match.SCHEDULED)),
            forfeits=models.Count('id', filter=models.Q(state='forfeit')),
            avg_dur=models.Avg(
                models.F('completed_at') - models.F('started_at'),
                filter=models.Q(
                    state=Match.COMPLETED,
                    completed_at__isnull=False,
                    started_at__isnull=False,
                ),
            ),
        )
        return {
            'total': agg.get('total') or 0,
            'live': agg.get('live') or 0,
            'completed': agg.get('completed') or 0,
            'scheduled': agg.get('scheduled') or 0,
            'forfeits': agg.get('forfeits') or 0,
            'avg_dur': agg.get('avg_dur'),
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

    # ── S28: Countdown Timers ─────────────────────────────────────────

    @classmethod
    def _get_countdowns(
        cls,
        tournament: Tournament,
        *,
        upcoming_matches: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Return countdown timers for key tournament milestones."""
        now = timezone.now()
        countdowns = []

        # Registration close countdown
        if hasattr(tournament, 'registration_end') and tournament.registration_end:
            if tournament.registration_end > now:
                delta = tournament.registration_end - now
                countdowns.append({
                    'label': 'Registration Closes',
                    'target': tournament.registration_end.isoformat(),
                    'seconds_remaining': int(delta.total_seconds()),
                    'type': 'registration',
                })

        # Tournament start countdown
        if hasattr(tournament, 'tournament_start') and tournament.tournament_start:
            if tournament.tournament_start > now:
                delta = tournament.tournament_start - now
                countdowns.append({
                    'label': 'Tournament Starts',
                    'target': tournament.tournament_start.isoformat(),
                    'seconds_remaining': int(delta.total_seconds()),
                    'type': 'start',
                })

        # Next match countdown (reuse already-fetched upcoming match when available)
        next_scheduled = None
        if upcoming_matches:
            for item in upcoming_matches:
                raw = item.get('scheduled_time')
                if not raw:
                    continue
                try:
                    from django.utils.dateparse import parse_datetime
                    dt = parse_datetime(raw)
                except Exception:
                    dt = None
                if dt and dt > now:
                    next_scheduled = dt
                    break

        if not next_scheduled:
            next_match = Match.objects.filter(
                tournament=tournament,
                state__in=['scheduled', 'check_in', 'ready'],
                scheduled_time__gt=now,
            ).order_by('scheduled_time').only('scheduled_time').first()
            if next_match and next_match.scheduled_time:
                next_scheduled = next_match.scheduled_time

        if next_scheduled:
            delta = next_scheduled - now
            countdowns.append({
                'label': 'Next Match',
                'target': next_scheduled.isoformat(),
                'seconds_remaining': int(delta.total_seconds()),
                'type': 'match',
            })

        # Check-in window
        config = tournament.config or {}
        checkin_cfg = config.get('checkin', {})
        if isinstance(checkin_cfg, dict) and checkin_cfg.get('open'):
            deadline = checkin_cfg.get('deadline')
            if deadline:
                try:
                    from django.utils.dateparse import parse_datetime
                    dt = parse_datetime(deadline)
                    if dt and dt > now:
                        delta = dt - now
                        countdowns.append({
                            'label': 'Check-in Closes',
                            'target': dt.isoformat(),
                            'seconds_remaining': int(delta.total_seconds()),
                            'type': 'checkin',
                        })
                except (ValueError, TypeError):
                    pass

        return countdowns

    # ── S28: Quick Actions ────────────────────────────────────────────

    @classmethod
    def _get_quick_actions(cls, tournament: Tournament) -> List[Dict[str, Any]]:
        """
        Return context-sensitive quick-launch actions based on current state.
        Actions are buttons shown in the overview for common one-click operations.
        """
        actions = []
        status = tournament.status

        if status == 'draft':
            actions.append({
                'id': 'open_registration',
                'label': 'Open Registration',
                'icon': 'user-plus',
                'action': 'transition',
                'target': 'registration_open',
            })

        elif status == 'registration_open':
            actions.append({
                'id': 'close_registration',
                'label': 'Close Registration',
                'icon': 'user-x',
                'action': 'transition',
                'target': 'registration_closed',
            })
            actions.append({
                'id': 'open_checkin',
                'label': 'Open Check-in',
                'icon': 'check-square',
                'action': 'api',
                'endpoint': 'checkin/open/',
                'method': 'POST',
            })

        elif status == 'registration_closed':
            actions.append({
                'id': 'open_checkin',
                'label': 'Open Check-in',
                'icon': 'check-square',
                'action': 'api',
                'endpoint': 'checkin/open/',
                'method': 'POST',
            })
            # Draw Director if group stage exists
            if tournament.format in ('group_playoff', 'group_stage', 'round_robin'):
                actions.append({
                    'id': 'draw_director',
                    'label': 'Live Draw Ceremony',
                    'icon': 'radio',
                    'action': 'link',
                    'target': f'/tournaments/{tournament.slug}/draw/director/',
                })
            actions.append({
                'id': 'start_tournament',
                'label': 'Start Tournament',
                'icon': 'play',
                'action': 'transition',
                'target': 'in_progress',
            })

        elif status == 'in_progress':
            actions.append({
                'id': 'broadcast_update',
                'label': 'Broadcast Update',
                'icon': 'megaphone',
                'action': 'tab',
                'target': 'announcements',
            })
            # Draw Director if group stage exists and is active
            if tournament.format in ('group_playoff', 'group_stage', 'round_robin'):
                actions.append({
                    'id': 'draw_director',
                    'label': 'Live Draw Ceremony',
                    'icon': 'radio',
                    'action': 'link',
                    'target': f'/tournaments/{tournament.slug}/draw/director/',
                })
            actions.append({
                'id': 'view_brackets',
                'label': 'View Brackets',
                'icon': 'git-branch',
                'action': 'tab',
                'target': 'brackets',
            })
            actions.append({
                'id': 'manage_disputes',
                'label': 'Manage Disputes',
                'icon': 'shield-alert',
                'action': 'tab',
                'target': 'disputes',
            })

        elif status in ('completed', 'finalized'):
            actions.append({
                'id': 'export_results',
                'label': 'Export Results',
                'icon': 'download',
                'action': 'api',
                'endpoint': 'standings/export/',
                'method': 'GET',
            })

        return actions

    # ── S30: Overview Inline Stats & Activity ───────────────────────

    @classmethod
    def _build_quick_stats(
        cls,
        tournament: Tournament,
        reg_stats: Dict[str, int],
        match_stats: Dict[str, int],
    ) -> Dict[str, Any]:
        """Build quick stats payload expected by overview sidebar cards."""
        total_matches = match_stats.get('total', 0)
        completed_matches = match_stats.get('completed', 0)
        completion_pct = round((completed_matches / total_matches) * 100, 1) if total_matches else 0

        total_regs = reg_stats.get('total', 0)
        checked_in = reg_stats.get('checked_in', 0)
        disqualified = reg_stats.get('disqualified', 0)
        dq_rate = round((disqualified / total_regs) * 100, 1) if total_regs else 0

        avg_duration_minutes = None
        avg_dur = match_stats.get('avg_dur')
        if avg_dur:
            avg_duration_minutes = int(avg_dur.total_seconds() // 60)

        return {
            'matches': {
                'completion_pct': completion_pct,
                'avg_duration_minutes': avg_duration_minutes,
                'in_progress': match_stats.get('live', 0),
                'forfeits': match_stats.get('forfeits', 0) or 0,
            },
            'participants': {
                'checked_in': checked_in,
                'dq_rate_pct': dq_rate,
            },
        }

    @classmethod
    def _get_recent_activity(cls, tournament: Tournament, limit: int = 25) -> List[Dict[str, Any]]:
        """Return lightweight activity log entries for overview without extra API request."""
        rows = list(
            AuditLog.objects
            .filter(tournament_id=tournament.id)
            .values('id', 'action', 'metadata', 'timestamp', 'user__username')
            .order_by('-timestamp')[:limit]
        )

        items: List[Dict[str, Any]] = []
        for row in rows:
            metadata = row.get('metadata') if isinstance(row.get('metadata'), dict) else {}
            items.append({
                'id': row.get('id'),
                'action': row.get('action'),
                'username': row.get('user__username') or 'system',
                'detail': metadata.get('detail') if isinstance(metadata.get('detail'), dict) else {},
                'created_at': row.get('timestamp').isoformat() if row.get('timestamp') else '',
            })
        return items
