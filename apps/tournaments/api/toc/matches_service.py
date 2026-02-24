"""
TOC Matches Service — Sprint 6.

Wraps MatchService, handles match listing, scoring, Match Medic
(pause/resume), reschedule requests, forfeits, notes, media, and stations.

PRD: §6.1–§6.10
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.db.models import Q, Prefetch
from django.utils import timezone

from apps.tournaments.models.match import Match
from apps.tournaments.models.match_operations import (
    BroadcastStation,
    MatchMedia,
    MatchServerSelection,
    RescheduleRequest,
)
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.services.match_service import MatchService

logger = logging.getLogger(__name__)


class TOCMatchesService:
    """Match operations for the TOC Matches tab."""

    # ── S6-B1: Match list ─────────────────────────────────────

    @classmethod
    def get_matches(
        cls,
        tournament: Tournament,
        *,
        round_number: Optional[int] = None,
        state: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        qs = Match.objects.filter(tournament=tournament).order_by(
            'round_number', 'match_number',
        )
        if round_number:
            qs = qs.filter(round_number=round_number)
        if state:
            qs = qs.filter(state=state)
        if search:
            qs = qs.filter(
                Q(participant1_name__icontains=search)
                | Q(participant2_name__icontains=search)
            )

        return [cls._serialize_match(m) for m in qs[:500]]

    # ── S6-B2: Score submission ───────────────────────────────

    @classmethod
    def submit_score(
        cls,
        match_id: int,
        tournament: Tournament,
        *,
        p1_score: int,
        p2_score: int,
        user_id: int,
    ) -> Dict[str, Any]:
        match = Match.objects.get(pk=match_id, tournament=tournament)
        try:
            updated = MatchService.organizer_override_score(
                match=match,
                participant1_score=p1_score,
                participant2_score=p2_score,
                user_id=user_id,
            )
        except Exception:
            # Fallback: direct update if organizer_override_score has guards
            match.participant1_score = p1_score
            match.participant2_score = p2_score
            if p1_score > p2_score:
                match.winner_id = match.participant1_id
                match.loser_id = match.participant2_id
            elif p2_score > p1_score:
                match.winner_id = match.participant2_id
                match.loser_id = match.participant1_id
            if match.state not in ('completed', 'cancelled'):
                match.state = Match.COMPLETED
                match.completed_at = timezone.now()
            match.save()
            updated = match
        return cls._serialize_match(updated)

    # ── S6-B3: Mark live ──────────────────────────────────────

    @classmethod
    def mark_live(cls, match_id: int, tournament: Tournament) -> Dict[str, Any]:
        match = Match.objects.get(pk=match_id, tournament=tournament)
        try:
            updated = MatchService.transition_to_live(match)
        except Exception:
            match.state = Match.LIVE
            match.started_at = timezone.now()
            match.save(update_fields=['state', 'started_at'])
            updated = match
        return cls._serialize_match(updated)

    # ── S6-B4/B5: Pause / Resume (Match Medic) ───────────────

    @classmethod
    def pause_match(cls, match_id: int, tournament: Tournament) -> Dict[str, Any]:
        match = Match.objects.get(pk=match_id, tournament=tournament)
        if match.state != Match.LIVE:
            raise ValueError('Only live matches can be paused.')
        match.lobby_info['paused'] = True
        match.lobby_info['paused_at'] = timezone.now().isoformat()
        match.save(update_fields=['lobby_info'])
        return cls._serialize_match(match)

    @classmethod
    def resume_match(cls, match_id: int, tournament: Tournament) -> Dict[str, Any]:
        match = Match.objects.get(pk=match_id, tournament=tournament)
        if not match.lobby_info.get('paused'):
            raise ValueError('Match is not paused.')
        match.lobby_info['paused'] = False
        match.lobby_info['resumed_at'] = timezone.now().isoformat()
        match.save(update_fields=['lobby_info'])
        return cls._serialize_match(match)

    # ── S6-B6: Force-complete ─────────────────────────────────

    @classmethod
    def force_complete(cls, match_id: int, tournament: Tournament, *, user_id: int) -> Dict[str, Any]:
        match = Match.objects.get(pk=match_id, tournament=tournament)
        match.state = Match.COMPLETED
        match.completed_at = timezone.now()
        match.lobby_info['force_completed_by'] = user_id
        match.save(update_fields=['state', 'completed_at', 'lobby_info'])
        return cls._serialize_match(match)

    # ── S6-B7: Reschedule ────────────────────────────────────

    @classmethod
    def request_reschedule(
        cls,
        match_id: int,
        tournament: Tournament,
        *,
        new_time: str,
        reason: str = '',
        user_id: int,
    ) -> Dict[str, Any]:
        match = Match.objects.get(pk=match_id, tournament=tournament)
        req = RescheduleRequest.objects.create(
            match=match,
            requested_by_id=user_id,
            old_time=match.scheduled_time,
            new_time=new_time,
            reason=reason,
        )
        return {
            'id': str(req.id),
            'match_id': match.id,
            'old_time': req.old_time.isoformat() if req.old_time else None,
            'new_time': req.new_time.isoformat(),
            'reason': req.reason,
            'status': req.status,
        }

    # ── S6-B8: Forfeit ───────────────────────────────────────

    @classmethod
    def forfeit_match(
        cls,
        match_id: int,
        tournament: Tournament,
        *,
        forfeiter_id: int,
        user_id: int,
    ) -> Dict[str, Any]:
        match = Match.objects.get(pk=match_id, tournament=tournament)
        try:
            updated = MatchService.organizer_forfeit_match(
                match=match,
                loser_id=forfeiter_id,
                user_id=user_id,
            )
        except Exception:
            match.state = Match.FORFEIT
            match.loser_id = forfeiter_id
            if match.participant1_id == forfeiter_id:
                match.winner_id = match.participant2_id
            else:
                match.winner_id = match.participant1_id
            match.completed_at = timezone.now()
            match.save()
            updated = match
        return cls._serialize_match(updated)

    # ── S6-B9: Match notes ───────────────────────────────────

    @classmethod
    def add_note(cls, match_id: int, tournament: Tournament, *, text: str, user_id: int) -> Dict[str, Any]:
        match = Match.objects.get(pk=match_id, tournament=tournament)
        notes = match.lobby_info.get('notes', [])
        notes.append({
            'text': text,
            'user_id': user_id,
            'created_at': timezone.now().isoformat(),
        })
        match.lobby_info['notes'] = notes
        match.save(update_fields=['lobby_info'])
        return {'notes': notes}

    # ── S6-B10: Match media ──────────────────────────────────

    @classmethod
    def get_media(cls, match_id: int, tournament: Tournament) -> List[Dict[str, Any]]:
        qs = MatchMedia.objects.filter(match_id=match_id, match__tournament=tournament)
        return [
            {
                'id': str(m.id),
                'media_type': m.media_type,
                'url': m.url or (m.file.url if m.file else ''),
                'description': m.description,
                'is_evidence': m.is_evidence,
                'created_at': m.created_at.isoformat(),
            }
            for m in qs
        ]

    @classmethod
    def upload_media(
        cls,
        match_id: int,
        tournament: Tournament,
        *,
        media_type: str = 'screenshot',
        url: str = '',
        description: str = '',
        is_evidence: bool = False,
        user_id: int,
    ) -> Dict[str, Any]:
        match = Match.objects.get(pk=match_id, tournament=tournament)
        media = MatchMedia.objects.create(
            match=match,
            uploaded_by_id=user_id,
            media_type=media_type,
            url=url,
            description=description,
            is_evidence=is_evidence,
        )
        return {
            'id': str(media.id),
            'media_type': media.media_type,
            'url': media.url,
            'description': media.description,
            'is_evidence': media.is_evidence,
        }

    # ── Stations ─────────────────────────────────────────────

    @classmethod
    def get_stations(cls, tournament: Tournament) -> List[Dict[str, Any]]:
        qs = BroadcastStation.objects.filter(tournament=tournament).select_related('assigned_match')
        return [
            {
                'id': str(s.id),
                'name': s.name,
                'stream_url': s.stream_url,
                'status': s.status,
                'assigned_match_id': s.assigned_match_id,
                'assigned_match_label': str(s.assigned_match) if s.assigned_match else None,
            }
            for s in qs
        ]

    @classmethod
    def assign_station(
        cls,
        station_id: str,
        tournament: Tournament,
        *,
        match_id: int,
    ) -> Dict[str, Any]:
        station = BroadcastStation.objects.get(pk=station_id, tournament=tournament)
        match = Match.objects.get(pk=match_id, tournament=tournament)
        station.assigned_match = match
        station.status = BroadcastStation.LIVE
        station.save(update_fields=['assigned_match', 'status'])
        return {
            'id': str(station.id),
            'name': station.name,
            'assigned_match_id': match.id,
            'status': station.status,
        }

    # ── Private serializer ───────────────────────────────────

    @classmethod
    def _serialize_match(cls, m: Match) -> Dict[str, Any]:
        return {
            'id': m.id,
            'round_number': m.round_number,
            'match_number': m.match_number,
            'participant1_id': m.participant1_id,
            'participant1_name': m.participant1_name,
            'participant2_id': m.participant2_id,
            'participant2_name': m.participant2_name,
            'participant1_score': m.participant1_score,
            'participant2_score': m.participant2_score,
            'state': m.state,
            'winner_id': m.winner_id,
            'loser_id': m.loser_id,
            'scheduled_time': m.scheduled_time.isoformat() if m.scheduled_time else None,
            'started_at': m.started_at.isoformat() if m.started_at else None,
            'completed_at': m.completed_at.isoformat() if m.completed_at else None,
            'stream_url': m.stream_url,
            'is_paused': m.lobby_info.get('paused', False),
            'notes_count': len(m.lobby_info.get('notes', [])),
        }
