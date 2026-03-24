"""
TOC Disputes Service — Sprint 7.

Wraps DisputeRecord and DisputeEvidence for the TOC Disputes tab.
Supports queue listing, detail, resolution, escalation, staff assignment, evidence.

PRD: §7.1–§7.6
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from django.db.models import Q
from django.utils import timezone

from apps.tournaments.models.dispute import DisputeRecord, DisputeEvidence
from apps.tournaments.models.hub_support_ticket import HubSupportTicket
from apps.tournaments.models.tournament import Tournament

logger = logging.getLogger(__name__)


class TOCDisputesService:
    """Dispute operations for the TOC Disputes tab."""

    # ── S7-B1: Dispute queue ─────────────────────────────────

    @classmethod
    def get_disputes(
        cls,
        tournament: Tournament,
        *,
        status_filter: Optional[str] = None,
        source_filter: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get disputes for all matches in this tournament."""
        qs = DisputeRecord.objects.filter(
            submission__match__tournament=tournament,
        ).select_related('submission', 'opened_by_user', 'resolved_by_user').order_by('-opened_at')

        hub_qs = HubSupportTicket.objects.filter(
            tournament=tournament,
        ).select_related('created_by', 'resolved_by').order_by('-created_at')

        if status_filter:
            qs = qs.filter(status=status_filter)
            hub_qs = hub_qs.filter(status__in=cls._map_hub_filter_to_statuses(status_filter))

        if source_filter == 'match_dispute':
            hub_qs = hub_qs.none()
        elif source_filter == 'hub_support':
            qs = qs.none()

        if search:
            qs = qs.filter(
                Q(description__icontains=search)
                | Q(reason_code__icontains=search)
            )
            hub_qs = hub_qs.filter(
                Q(subject__icontains=search)
                | Q(message__icontains=search)
                | Q(match_ref__icontains=search)
            )

        disputes_slice = list(qs[:200])
        hub_slice = list(hub_qs[:200])
        team_name_map = cls._build_team_name_map([
            *(d.opened_by_team_id for d in disputes_slice),
            *(t.team_id for t in hub_slice),
        ])

        disputes = [cls._serialize_dispute(d, team_name_map=team_name_map) for d in disputes_slice]
        hub_disputes = [cls._serialize_hub_ticket(t, team_name_map=team_name_map) for t in hub_slice]
        merged = disputes + hub_disputes
        merged.sort(key=lambda item: item.get('opened_at') or '', reverse=True)
        return merged[:200]

    # ── S7-B2: Dispute detail ────────────────────────────────

    @classmethod
    def get_dispute_detail(cls, dispute_id: int, tournament: Tournament) -> Dict[str, Any]:
        dispute = DisputeRecord.objects.select_related('submission', 'opened_by_user', 'resolved_by_user').get(
            pk=dispute_id,
            submission__match__tournament=tournament,
        )
        team_name_map = cls._build_team_name_map([dispute.opened_by_team_id])
        data = cls._serialize_dispute(dispute, team_name_map=team_name_map)
        # Add evidence
        evidence = DisputeEvidence.objects.filter(dispute=dispute).order_by('created_at')
        data['evidence'] = [
            {
                'id': e.id,
                'evidence_type': e.evidence_type,
                'url': e.url,
                'notes': e.notes,
                'uploaded_by_id': e.uploaded_by_id,
                'created_at': e.created_at.isoformat(),
            }
            for e in evidence
        ]
        return data

    @classmethod
    def get_hub_ticket_detail(cls, ticket_id: int, tournament: Tournament) -> Dict[str, Any]:
        ticket = HubSupportTicket.objects.select_related('created_by', 'resolved_by').get(
            pk=ticket_id,
            tournament=tournament,
        )
        team_name_map = cls._build_team_name_map([ticket.team_id])
        data = cls._serialize_hub_ticket(ticket, team_name_map=team_name_map)
        data['evidence'] = []
        return data

    # ── S7-B3: Resolve dispute ───────────────────────────────

    @classmethod
    def resolve_dispute(
        cls,
        dispute_id: int,
        tournament: Tournament,
        *,
        ruling: str,
        resolution_notes: str = '',
        user_id: int,
        source_type: str = 'match_dispute',
    ) -> Dict[str, Any]:
        if source_type == 'hub_support':
            ticket = HubSupportTicket.objects.get(pk=dispute_id, tournament=tournament)
            ticket.status = HubSupportTicket.STATUS_RESOLVED
            if resolution_notes:
                ticket.organizer_notes = resolution_notes
            ticket.resolved_by_id = user_id
            ticket.resolved_at = timezone.now()
            ticket.save(update_fields=['status', 'organizer_notes', 'resolved_by_id', 'resolved_at', 'updated_at'])
            team_name_map = cls._build_team_name_map([ticket.team_id])
            return cls._serialize_hub_ticket(ticket, team_name_map=team_name_map)

        dispute = DisputeRecord.objects.get(
            pk=dispute_id,
            submission__match__tournament=tournament,
        )
        # Map ruling to status
        status_map = {
            'submitter_wins': DisputeRecord.RESOLVED_FOR_SUBMITTER,
            'opponent_wins': DisputeRecord.RESOLVED_FOR_OPPONENT,
            'cancelled': DisputeRecord.CANCELLED,
        }
        dispute.status = status_map.get(ruling, DisputeRecord.RESOLVED_FOR_SUBMITTER)
        dispute.resolution_notes = resolution_notes
        dispute.resolved_by_user_id = user_id
        dispute.resolved_at = timezone.now()
        dispute.save(update_fields=['status', 'resolution_notes', 'resolved_by_user_id', 'resolved_at'])
        return cls._serialize_dispute(dispute)

    # ── S7-B4: Escalate dispute ──────────────────────────────

    @classmethod
    def escalate_dispute(
        cls,
        dispute_id: int,
        tournament: Tournament,
        *,
        reason: str = '',
        user_id: int,
        source_type: str = 'match_dispute',
    ) -> Dict[str, Any]:
        if source_type == 'hub_support':
            ticket = HubSupportTicket.objects.get(pk=dispute_id, tournament=tournament)
            ticket.status = HubSupportTicket.STATUS_IN_REVIEW
            ticket.resolved_by_id = user_id
            if reason:
                existing_notes = ticket.organizer_notes or ''
                ticket.organizer_notes = f"[ESCALATED] {reason}" + (f"\n{existing_notes}" if existing_notes else '')
            ticket.save(update_fields=['status', 'resolved_by_id', 'organizer_notes', 'updated_at'])
            team_name_map = cls._build_team_name_map([ticket.team_id])
            return cls._serialize_hub_ticket(ticket, team_name_map=team_name_map)

        dispute = DisputeRecord.objects.get(
            pk=dispute_id,
            submission__match__tournament=tournament,
        )
        dispute.status = DisputeRecord.ESCALATED
        dispute.escalated_at = timezone.now()
        if reason:
            dispute.resolution_notes = f"[ESCALATED] {reason}\n{dispute.resolution_notes}"
        dispute.save(update_fields=['status', 'escalated_at', 'resolution_notes'])
        return cls._serialize_dispute(dispute)

    # ── S7-B5: Assign to staff ───────────────────────────────

    @classmethod
    def assign_dispute(
        cls,
        dispute_id: int,
        tournament: Tournament,
        *,
        staff_user_id: int,
        source_type: str = 'match_dispute',
    ) -> Dict[str, Any]:
        if source_type == 'hub_support':
            ticket = HubSupportTicket.objects.get(pk=dispute_id, tournament=tournament)
            ticket.resolved_by_id = staff_user_id
            if ticket.status == HubSupportTicket.STATUS_OPEN:
                ticket.status = HubSupportTicket.STATUS_IN_REVIEW
            ticket.save(update_fields=['resolved_by_id', 'status', 'updated_at'])
            team_name_map = cls._build_team_name_map([ticket.team_id])
            return cls._serialize_hub_ticket(ticket, team_name_map=team_name_map)

        dispute = DisputeRecord.objects.get(
            pk=dispute_id,
            submission__match__tournament=tournament,
        )
        dispute.resolved_by_user_id = staff_user_id
        if dispute.status == DisputeRecord.OPEN:
            dispute.status = DisputeRecord.UNDER_REVIEW
        dispute.save(update_fields=['resolved_by_user_id', 'status'])
        return cls._serialize_dispute(dispute)

    # ── S7-B6: Add evidence ──────────────────────────────────

    @classmethod
    def add_evidence(
        cls,
        dispute_id: int,
        tournament: Tournament,
        *,
        evidence_type: str = 'screenshot',
        url: str = '',
        evidence_file=None,
        notes: str = '',
        user_id: int,
    ) -> Dict[str, Any]:
        dispute = DisputeRecord.objects.get(
            pk=dispute_id,
            submission__match__tournament=tournament,
        )
        ev = DisputeEvidence.objects.create(
            dispute=dispute,
            uploaded_by_id=user_id,
            evidence_type=evidence_type,
            url=url,
            evidence_file=evidence_file,
            notes=notes,
        )
        return {
            'id': ev.id,
            'evidence_type': ev.evidence_type,
            'url': ev.url or (ev.evidence_file.url if ev.evidence_file else ''),
            'file_url': ev.evidence_file.url if ev.evidence_file else None,
            'notes': ev.notes,
            'created_at': ev.created_at.isoformat(),
        }

    # ── S7-B7: Update status ────────────────────────────────

    @classmethod
    def update_status(
        cls,
        dispute_id: int,
        tournament: Tournament,
        *,
        new_status: str,
        source_type: str = 'match_dispute',
    ) -> Dict[str, Any]:
        if source_type == 'hub_support':
            ticket = HubSupportTicket.objects.get(pk=dispute_id, tournament=tournament)
            hub_status = cls._map_dispute_status_to_hub_status(new_status)
            ticket.status = hub_status
            if hub_status == HubSupportTicket.STATUS_RESOLVED and not ticket.resolved_at:
                ticket.resolved_at = timezone.now()
            if hub_status in (HubSupportTicket.STATUS_OPEN, HubSupportTicket.STATUS_IN_REVIEW):
                ticket.resolved_at = None
            ticket.save(update_fields=['status', 'resolved_at', 'updated_at'])
            team_name_map = cls._build_team_name_map([ticket.team_id])
            return cls._serialize_hub_ticket(ticket, team_name_map=team_name_map)

        dispute = DisputeRecord.objects.get(
            pk=dispute_id,
            submission__match__tournament=tournament,
        )
        dispute.status = new_status
        dispute.save(update_fields=['status'])
        return cls._serialize_dispute(dispute)

    # ── Stats for badge (S7-F6) ──────────────────────────────

    @classmethod
    def get_open_count(cls, tournament: Tournament, source_filter: Optional[str] = None) -> int:
        dispute_qs = DisputeRecord.objects.filter(
            submission__match__tournament=tournament,
            status__in=[DisputeRecord.OPEN, DisputeRecord.UNDER_REVIEW, DisputeRecord.ESCALATED],
        )
        hub_qs = HubSupportTicket.objects.filter(
            tournament=tournament,
            status__in=[HubSupportTicket.STATUS_OPEN, HubSupportTicket.STATUS_IN_REVIEW],
        )

        if source_filter == 'match_dispute':
            return dispute_qs.count()
        if source_filter == 'hub_support':
            return hub_qs.count()

        return dispute_qs.count() + hub_qs.count()

    # ── Private serializer ───────────────────────────────────

    @classmethod
    def _serialize_dispute(
        cls,
        d: DisputeRecord,
        *,
        team_name_map: Optional[Dict[int, str]] = None,
    ) -> Dict[str, Any]:
        # Derive severity from reason_code
        severity_map = {
            'cheating_suspicion': 'critical',
            'wrong_winner': 'high',
            'score_mismatch': 'medium',
            'match_not_played': 'medium',
            'incorrect_map': 'low',
            'other': 'low',
        }
        return {
            'id': d.id,
            'ui_id': f'dispute-{d.id}',
            'source_type': 'match_dispute',
            'is_actionable': True,
            'match_id': d.submission.match_id if d.submission_id else None,
            'submission_id': d.submission_id,
            'status': d.status,
            'status_display': d.get_status_display(),
            'reason_code': d.reason_code,
            'reason_display': d.get_reason_code_display(),
            'severity': severity_map.get(d.reason_code, 'low'),
            'description': d.description,
            'resolution_notes': d.resolution_notes,
            'opened_by_user_id': d.opened_by_user_id,
            'opened_by_name': cls._display_name(getattr(d, 'opened_by_user', None)),
            'opened_by_team_id': d.opened_by_team_id,
            'opened_by_team_name': cls._team_name_for_id(d.opened_by_team_id, team_name_map),
            'resolved_by_user_id': d.resolved_by_user_id,
            'resolved_by_name': cls._display_name(getattr(d, 'resolved_by_user', None)),
            'opened_at': d.opened_at.isoformat() if d.opened_at else None,
            'resolved_at': d.resolved_at.isoformat() if d.resolved_at else None,
            'escalated_at': d.escalated_at.isoformat() if d.escalated_at else None,
        }

    @classmethod
    def _serialize_hub_ticket(
        cls,
        t: HubSupportTicket,
        *,
        team_name_map: Optional[Dict[int, str]] = None,
    ) -> Dict[str, Any]:
        mapped_status = cls._map_hub_status_to_dispute_status(t.status)
        severity_map = {
            HubSupportTicket.CATEGORY_DISPUTE: 'high',
            HubSupportTicket.CATEGORY_PAYMENT: 'medium',
            HubSupportTicket.CATEGORY_TECHNICAL: 'medium',
            HubSupportTicket.CATEGORY_GENERAL: 'low',
        }
        return {
            'id': t.id,
            'ui_id': f'hub-{t.id}',
            'source_type': 'hub_support',
            'is_actionable': True,
            'match_id': cls._extract_match_id(t.match_ref),
            'submission_id': None,
            'status': mapped_status,
            'status_display': t.get_status_display(),
            'reason_code': t.category,
            'reason_display': t.get_category_display(),
            'severity': severity_map.get(t.category, 'low'),
            'description': t.message,
            'resolution_notes': t.organizer_notes,
            'opened_by_user_id': t.created_by_id,
            'opened_by_name': cls._display_name(t.created_by),
            'opened_by_team_id': t.team_id,
            'opened_by_team_name': cls._team_name_for_id(t.team_id, team_name_map),
            'resolved_by_user_id': t.resolved_by_id,
            'resolved_by_name': cls._display_name(t.resolved_by),
            'opened_at': t.created_at.isoformat() if t.created_at else None,
            'resolved_at': t.resolved_at.isoformat() if t.resolved_at else None,
            'escalated_at': None,
            'match_ref': t.match_ref,
        }

    @staticmethod
    def _build_team_name_map(team_ids: List[Optional[int]]) -> Dict[int, str]:
        valid_ids = sorted({team_id for team_id in team_ids if team_id})
        if not valid_ids:
            return {}
        try:
            from apps.organizations.models import Team
        except Exception:
            return {}
        return {
            row['id']: row['name']
            for row in Team.objects.filter(id__in=valid_ids).values('id', 'name')
        }

    @staticmethod
    def _team_name_for_id(team_id: Optional[int], team_name_map: Optional[Dict[int, str]]) -> str:
        if not team_id:
            return ''
        if team_name_map and team_id in team_name_map:
            return team_name_map[team_id]
        return f'Team #{team_id}'

    @staticmethod
    def _display_name(user) -> str:
        if not user:
            return ''
        full_name = (user.get_full_name() or '').strip()
        if full_name:
            return full_name
        return getattr(user, 'username', '') or ''

    @staticmethod
    def _extract_match_id(match_ref: str) -> Optional[int]:
        if not match_ref:
            return None
        found = re.search(r'(\d+)', str(match_ref))
        if not found:
            return None
        try:
            return int(found.group(1))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _map_hub_status_to_dispute_status(status: str) -> str:
        mapping = {
            HubSupportTicket.STATUS_OPEN: DisputeRecord.OPEN,
            HubSupportTicket.STATUS_IN_REVIEW: DisputeRecord.UNDER_REVIEW,
            HubSupportTicket.STATUS_RESOLVED: DisputeRecord.RESOLVED_FOR_SUBMITTER,
            HubSupportTicket.STATUS_CLOSED: DisputeRecord.CANCELLED,
        }
        return mapping.get(status, DisputeRecord.OPEN)

    @staticmethod
    def _map_dispute_status_to_hub_status(status: str) -> str:
        mapping = {
            DisputeRecord.OPEN: HubSupportTicket.STATUS_OPEN,
            DisputeRecord.UNDER_REVIEW: HubSupportTicket.STATUS_IN_REVIEW,
            DisputeRecord.ESCALATED: HubSupportTicket.STATUS_IN_REVIEW,
            DisputeRecord.RESOLVED_FOR_SUBMITTER: HubSupportTicket.STATUS_RESOLVED,
            DisputeRecord.RESOLVED_FOR_OPPONENT: HubSupportTicket.STATUS_RESOLVED,
            DisputeRecord.CANCELLED: HubSupportTicket.STATUS_CLOSED,
            DisputeRecord.DISMISSED: HubSupportTicket.STATUS_CLOSED,
        }
        return mapping.get(status, HubSupportTicket.STATUS_OPEN)

    @classmethod
    def _map_hub_filter_to_statuses(cls, status_filter: str) -> List[str]:
        # Keep UI filters backward-compatible while including hub ticket statuses.
        lookup = {
            DisputeRecord.OPEN: [HubSupportTicket.STATUS_OPEN],
            DisputeRecord.UNDER_REVIEW: [HubSupportTicket.STATUS_IN_REVIEW],
            DisputeRecord.ESCALATED: [],
            DisputeRecord.RESOLVED_FOR_SUBMITTER: [HubSupportTicket.STATUS_RESOLVED],
            DisputeRecord.RESOLVED_FOR_OPPONENT: [HubSupportTicket.STATUS_RESOLVED],
            DisputeRecord.CANCELLED: [HubSupportTicket.STATUS_CLOSED],
            DisputeRecord.DISMISSED: [HubSupportTicket.STATUS_CLOSED],
        }
        return lookup.get(status_filter, [
            HubSupportTicket.STATUS_OPEN,
            HubSupportTicket.STATUS_IN_REVIEW,
            HubSupportTicket.STATUS_RESOLVED,
            HubSupportTicket.STATUS_CLOSED,
        ])
