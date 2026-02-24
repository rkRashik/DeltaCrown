"""
TOC Disputes Service — Sprint 7.

Wraps DisputeRecord and DisputeEvidence for the TOC Disputes tab.
Supports queue listing, detail, resolution, escalation, staff assignment, evidence.

PRD: §7.1–§7.6
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from django.db.models import Q
from django.utils import timezone

from apps.tournaments.models.dispute import DisputeRecord, DisputeEvidence
from apps.tournaments.models.match import Match
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
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get disputes for all matches in this tournament."""
        match_ids = Match.objects.filter(tournament=tournament).values_list('id', flat=True)
        qs = DisputeRecord.objects.filter(
            submission__match_id__in=match_ids,
        ).select_related('submission').order_by('-opened_at')

        if status_filter:
            qs = qs.filter(status=status_filter)
        if search:
            qs = qs.filter(
                Q(description__icontains=search)
                | Q(reason_code__icontains=search)
            )

        return [cls._serialize_dispute(d) for d in qs[:200]]

    # ── S7-B2: Dispute detail ────────────────────────────────

    @classmethod
    def get_dispute_detail(cls, dispute_id: int, tournament: Tournament) -> Dict[str, Any]:
        match_ids = Match.objects.filter(tournament=tournament).values_list('id', flat=True)
        dispute = DisputeRecord.objects.select_related('submission').get(
            pk=dispute_id,
            submission__match_id__in=match_ids,
        )
        data = cls._serialize_dispute(dispute)
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
    ) -> Dict[str, Any]:
        match_ids = Match.objects.filter(tournament=tournament).values_list('id', flat=True)
        dispute = DisputeRecord.objects.get(
            pk=dispute_id,
            submission__match_id__in=match_ids,
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
    ) -> Dict[str, Any]:
        match_ids = Match.objects.filter(tournament=tournament).values_list('id', flat=True)
        dispute = DisputeRecord.objects.get(
            pk=dispute_id,
            submission__match_id__in=match_ids,
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
    ) -> Dict[str, Any]:
        match_ids = Match.objects.filter(tournament=tournament).values_list('id', flat=True)
        dispute = DisputeRecord.objects.get(
            pk=dispute_id,
            submission__match_id__in=match_ids,
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
        url: str,
        notes: str = '',
        user_id: int,
    ) -> Dict[str, Any]:
        match_ids = Match.objects.filter(tournament=tournament).values_list('id', flat=True)
        dispute = DisputeRecord.objects.get(
            pk=dispute_id,
            submission__match_id__in=match_ids,
        )
        ev = DisputeEvidence.objects.create(
            dispute=dispute,
            uploaded_by_id=user_id,
            evidence_type=evidence_type,
            url=url,
            notes=notes,
        )
        return {
            'id': ev.id,
            'evidence_type': ev.evidence_type,
            'url': ev.url,
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
    ) -> Dict[str, Any]:
        match_ids = Match.objects.filter(tournament=tournament).values_list('id', flat=True)
        dispute = DisputeRecord.objects.get(
            pk=dispute_id,
            submission__match_id__in=match_ids,
        )
        dispute.status = new_status
        dispute.save(update_fields=['status'])
        return cls._serialize_dispute(dispute)

    # ── Stats for badge (S7-F6) ──────────────────────────────

    @classmethod
    def get_open_count(cls, tournament: Tournament) -> int:
        match_ids = Match.objects.filter(tournament=tournament).values_list('id', flat=True)
        return DisputeRecord.objects.filter(
            submission__match_id__in=match_ids,
            status__in=[DisputeRecord.OPEN, DisputeRecord.UNDER_REVIEW, DisputeRecord.ESCALATED],
        ).count()

    # ── Private serializer ───────────────────────────────────

    @classmethod
    def _serialize_dispute(cls, d: DisputeRecord) -> Dict[str, Any]:
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
            'opened_by_team_id': d.opened_by_team_id,
            'resolved_by_user_id': d.resolved_by_user_id,
            'opened_at': d.opened_at.isoformat() if d.opened_at else None,
            'resolved_at': d.resolved_at.isoformat() if d.resolved_at else None,
            'escalated_at': d.escalated_at.isoformat() if d.escalated_at else None,
        }
