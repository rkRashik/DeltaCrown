"""
Command Center Alert Service for Tournament Operations Center.

Generates actionable alerts for organizers based on tournament state:
- Pending payments awaiting verification
- Pending registrations (guest teams) needing review
- Open disputes requiring resolution
- Registration deadline approaching
- Check-in window events
- Lifecycle progress tracking

Source: Documents/Registration_system/02_REGISTRATION_SYSTEM_PLAN.md v3.0
Task: P1-T02
"""

from datetime import timedelta
from django.utils import timezone


class CommandCenterService:
    """Generate priority-ordered alerts for the TOC Command Center."""

    # Alert severity levels
    CRITICAL = 'critical'   # Red — immediate action required
    WARNING = 'warning'     # Amber — action recommended
    INFO = 'info'           # Blue — informational

    @classmethod
    def get_alerts(cls, tournament, reg_stats, payment_stats, dispute_stats, match_stats):
        """
        Generate all alerts for a tournament.

        Returns list of dicts:
          {severity, icon, title, description, count, link_tab, link_label}
        Sorted by severity (critical first).
        """
        alerts = []

        # ── Critical: Open disputes ──
        open_disputes = dispute_stats.get('open', 0)
        if open_disputes > 0:
            alerts.append({
                'severity': cls.CRITICAL,
                'icon': 'shield-alert',
                'title': f'{open_disputes} Open Dispute{"s" if open_disputes != 1 else ""}',
                'description': 'Disputes require your immediate attention to keep the tournament fair.',
                'count': open_disputes,
                'link_tab': 'disputes',
                'link_label': 'Resolve Disputes',
            })

        # ── Warning: Pending payments ──
        pending_payments = payment_stats.get('pending', 0)
        if pending_payments > 0:
            alerts.append({
                'severity': cls.WARNING,
                'icon': 'wallet',
                'title': f'{pending_payments} Payment{"s" if pending_payments != 1 else ""} Awaiting Verification',
                'description': 'Review submitted payment proofs and verify or reject them.',
                'count': pending_payments,
                'link_tab': 'payments',
                'link_label': 'Verify Payments',
            })

        # ── Warning: Pending registrations ──
        pending_regs = reg_stats.get('pending', 0)
        if pending_regs > 0:
            alerts.append({
                'severity': cls.WARNING,
                'icon': 'user-check',
                'title': f'{pending_regs} Registration{"s" if pending_regs != 1 else ""} Pending Review',
                'description': 'New registrations (including guest teams) need your approval.',
                'count': pending_regs,
                'link_tab': 'participants',
                'link_label': 'Review Registrations',
            })

        # ── Warning: Registration deadline approaching ──
        if tournament.registration_end:
            now = timezone.now()
            time_until_close = tournament.registration_end - now
            if timedelta(0) < time_until_close <= timedelta(hours=24):
                hours_left = int(time_until_close.total_seconds() / 3600)
                alerts.append({
                    'severity': cls.WARNING,
                    'icon': 'clock',
                    'title': f'Registration Closes in {hours_left}h',
                    'description': f'Registration deadline is {tournament.registration_end.strftime("%b %d at %I:%M %p")}.',
                    'count': None,
                    'link_tab': None,
                    'link_label': None,
                })

        # ── Info: Disputes under review ──
        under_review = dispute_stats.get('under_review', 0)
        if under_review > 0:
            alerts.append({
                'severity': cls.INFO,
                'icon': 'search',
                'title': f'{under_review} Dispute{"s" if under_review != 1 else ""} Under Review',
                'description': 'These disputes are being investigated.',
                'count': under_review,
                'link_tab': 'disputes',
                'link_label': 'View Disputes',
            })

        # ── Info: Live matches ──
        live_matches = match_stats.get('live', 0)
        if live_matches > 0:
            alerts.append({
                'severity': cls.INFO,
                'icon': 'radio',
                'title': f'{live_matches} Match{"es" if live_matches != 1 else ""} Live Now',
                'description': 'Active matches are in progress.',
                'count': live_matches,
                'link_tab': 'matches',
                'link_label': 'View Matches',
            })

        # ── Info: Check-in coming soon ──
        if hasattr(tournament, 'enable_check_in') and tournament.enable_check_in:
            if tournament.tournament_start:
                now = timezone.now()
                checkin_minutes = getattr(tournament, 'check_in_minutes_before', 30) or 30
                checkin_opens = tournament.tournament_start - timedelta(minutes=checkin_minutes)
                time_until_checkin = checkin_opens - now

                if timedelta(0) < time_until_checkin <= timedelta(hours=2):
                    alerts.append({
                        'severity': cls.INFO,
                        'icon': 'scan',
                        'title': 'Check-In Window Opening Soon',
                        'description': f'Check-in opens {checkin_opens.strftime("%I:%M %p")} ({checkin_minutes} min before start).',
                        'count': None,
                        'link_tab': 'schedule',
                        'link_label': 'View Schedule',
                    })

        return alerts

    @classmethod
    def get_lifecycle_progress(cls, tournament):
        """
        Compute tournament lifecycle stage and progress percentage.

        Stages: draft → registration → brackets → live → completed
        Returns: {stage, progress_pct, stages: [{name, status, icon}]}
        """
        status = getattr(tournament, 'status', 'draft')

        stage_map = {
            'draft': 0,
            'registration_open': 1,
            'registration_closed': 2,
            'brackets_generated': 3,
            'live': 4,
            'completed': 5,
            'cancelled': -1,
        }

        current_idx = stage_map.get(status, 0)

        stages = [
            {'name': 'Draft', 'icon': 'file-edit', 'status': 'done' if current_idx > 0 else ('active' if current_idx == 0 else 'pending')},
            {'name': 'Registration', 'icon': 'user-plus', 'status': 'done' if current_idx > 1 else ('active' if current_idx == 1 else 'pending')},
            {'name': 'Brackets', 'icon': 'git-merge', 'status': 'done' if current_idx > 3 else ('active' if current_idx in (2, 3) else 'pending')},
            {'name': 'Live', 'icon': 'radio', 'status': 'done' if current_idx > 4 else ('active' if current_idx == 4 else 'pending')},
            {'name': 'Completed', 'icon': 'trophy', 'status': 'done' if current_idx >= 5 else 'pending'},
        ]

        if current_idx == -1:
            # Cancelled
            progress_pct = 0
            for s in stages:
                s['status'] = 'cancelled'
        else:
            progress_pct = min(100, int((current_idx / 5) * 100))

        return {
            'stage': status,
            'progress_pct': progress_pct,
            'stages': stages,
        }

    @classmethod
    def get_upcoming_events(cls, tournament):
        """
        Generate list of upcoming events for the tournament.

        Returns: list of {label, datetime, icon, relative}
        """
        events = []
        now = timezone.now()

        if tournament.registration_end and tournament.registration_end > now:
            events.append({
                'label': 'Registration Closes',
                'datetime': tournament.registration_end,
                'icon': 'clock',
            })

        if tournament.tournament_start and tournament.tournament_start > now:
            if hasattr(tournament, 'enable_check_in') and tournament.enable_check_in:
                checkin_minutes = getattr(tournament, 'check_in_minutes_before', 30) or 30
                checkin_time = tournament.tournament_start - timedelta(minutes=checkin_minutes)
                if checkin_time > now:
                    events.append({
                        'label': 'Check-In Opens',
                        'datetime': checkin_time,
                        'icon': 'scan',
                    })

            events.append({
                'label': 'Tournament Starts',
                'datetime': tournament.tournament_start,
                'icon': 'play',
            })

        if hasattr(tournament, 'tournament_end') and tournament.tournament_end and tournament.tournament_end > now:
            events.append({
                'label': 'Tournament Ends',
                'datetime': tournament.tournament_end,
                'icon': 'flag',
            })

        # Sort by datetime
        events.sort(key=lambda e: e['datetime'])
        return events
