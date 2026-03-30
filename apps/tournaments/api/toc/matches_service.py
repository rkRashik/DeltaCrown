"""
TOC Matches Service — Sprint 6 + Sprint 9 (Match Verification).

Wraps MatchService, handles match listing, scoring, Match Medic
(pause/resume), reschedule requests, forfeits, notes, media, stations,
and Sprint 9 match verification split-screen API.

PRD: §6.1–§6.10, §9.1 (Match Verification Split-Screen)
"""

from __future__ import annotations

import logging
from math import ceil
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.db.models import Q, Prefetch, Count
from django.utils import timezone

from apps.tournaments.models.match import Match
from apps.tournaments.models.match_operations import (
    BroadcastStation,
    MatchMedia,
    MatchServerSelection,
    RescheduleRequest,
)
from apps.tournaments.models.result_submission import (
    MatchResultSubmission,
    ResultVerificationLog,
)
from apps.tournaments.models.dispute import DisputeRecord
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.services.match_service import MatchService

try:
    from apps.tournaments.models import GroupStanding
except ImportError:
    GroupStanding = None

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
        group: Optional[str] = None,
        page: int = 1,
        page_size: int = 60,
    ) -> Dict[str, Any]:
        page = max(1, int(page or 1))
        page_size = int(page_size or 60)
        page_size = min(120, max(10, page_size))

        qs = Match.objects.filter(
            tournament=tournament,
            is_deleted=False,
        ).select_related(
            'tournament',
            'bracket',
        ).prefetch_related(
            Prefetch(
                'result_submissions',
                queryset=MatchResultSubmission.objects.only('id', 'match_id', 'status', 'submitted_at').order_by('-submitted_at'),
            ),
            Prefetch(
                'media',
                queryset=MatchMedia.objects.only('id', 'match_id', 'media_type', 'is_evidence', 'created_at').order_by('-created_at'),
            ),
        ).order_by('round_number', 'match_number')
        if round_number:
            qs = qs.filter(round_number=round_number)
        if state:
            qs = qs.filter(state=state)
        if search:
            qs = qs.filter(
                Q(participant1_name__icontains=search)
                | Q(participant2_name__icontains=search)
            )
        if group:
            qs = qs.filter(lobby_info__group_label=group)

        state_counts = {
            str(row.get('state') or ''): int(row.get('count') or 0)
            for row in qs.values('state').annotate(count=Count('id'))
            if row.get('state')
        }

        qs = qs.only(
            'id',
            'tournament_id',
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
            'loser_id',
            'scheduled_time',
            'started_at',
            'completed_at',
            'stream_url',
            'lobby_info',
            'bracket_id',
            'participant1_checked_in',
            'participant2_checked_in',
            'check_in_deadline',
            'best_of',
            'game_scores',
        )

        total = qs.count()
        offset = (page - 1) * page_size
        page_matches = list(qs[offset:offset + page_size])
        participant_ids = set()
        for match in page_matches:
            if match.participant1_id:
                participant_ids.add(match.participant1_id)
            if match.participant2_id:
                participant_ids.add(match.participant2_id)

        group_cache = cls._build_group_cache(tournament, participant_ids=participant_ids)
        matches = [cls._serialize_match(m, group_cache=group_cache) for m in page_matches]

        total_pages = max(1, int(ceil(total / float(page_size)))) if page_size else 1
        has_next = page < total_pages
        has_prev = page > 1

        return {
            'matches': matches,
            'total_count': total,
            'state_counts': state_counts,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total,
                'total_pages': total_pages,
                'has_next': has_next,
                'has_prev': has_prev,
            },
        }

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
        except (AttributeError, TypeError) as exc:
            logger.warning('organizer_override_score unavailable (%s), using fallback', exc)
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
        except (AttributeError, TypeError) as exc:
            logger.warning('transition_to_live unavailable (%s), using fallback', exc)
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
        except (AttributeError, TypeError) as exc:
            logger.warning('organizer_forfeit_match unavailable (%s), using fallback', exc)
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

    # ── S9-B1: Match detail (composite) ─────────────────────

    @classmethod
    def get_match_detail(
        cls,
        match_id: int,
        tournament: Tournament,
    ) -> Dict[str, Any]:
        """Return enriched match data with submissions, media, disputes, notes."""
        match = Match.objects.get(pk=match_id, tournament=tournament)

        # Submissions (both captains)
        submissions = list(
            MatchResultSubmission.objects.filter(match=match)
            .select_related('submitted_by_user')
            .order_by('submitted_at')
        )

        # Serialize submissions
        subs_data = []
        for s in submissions:
            subs_data.append({
                'id': s.id,
                'submitted_by_user_id': s.submitted_by_user_id,
                'submitted_by_name': (
                    getattr(s.submitted_by_user, 'username', '')
                    or str(s.submitted_by_user_id)
                ),
                'submitted_by_team_id': s.submitted_by_team_id,
                'raw_result_payload': s.raw_result_payload or {},
                'proof_screenshot_url': s.proof_screenshot_url or '',
                'status': s.status,
                'submitted_at': s.submitted_at.isoformat() if s.submitted_at else None,
                'submitter_notes': s.submitter_notes,
                'organizer_notes': s.organizer_notes,
            })

        # Media
        media_qs = MatchMedia.objects.filter(match=match).order_by('-created_at')
        media_data = [
            {
                'id': str(m.id),
                'media_type': m.media_type,
                'url': m.url or (m.file.url if m.file else ''),
                'description': m.description,
                'is_evidence': m.is_evidence,
                'created_at': m.created_at.isoformat(),
            }
            for m in media_qs
        ]

        # Disputes (via submissions)
        sub_ids = [s.id for s in submissions]
        disputes = []
        if sub_ids:
            dispute_qs = DisputeRecord.objects.filter(
                submission_id__in=sub_ids
            ).select_related('opened_by_user').order_by('-opened_at')
            for d in dispute_qs:
                disputes.append({
                    'id': d.id,
                    'status': d.status,
                    'reason_code': d.reason_code,
                    'description': d.description,
                    'resolution_notes': d.resolution_notes,
                    'opened_by_name': (
                        getattr(d.opened_by_user, 'username', '')
                        if d.opened_by_user else ''
                    ),
                    'opened_at': d.opened_at.isoformat() if d.opened_at else None,
                    'resolved_at': d.resolved_at.isoformat() if d.resolved_at else None,
                })

        # Notes from lobby_info
        notes = match.lobby_info.get('notes', [])

        # ── Verification status (smart mismatch detection) ──
        verification_status = cls._compute_verification_status(match, submissions)

        return {
            'match': cls._serialize_match(match),
            'submissions': subs_data,
            'media': media_data,
            'disputes': disputes,
            'notes': notes,
            'verification_status': verification_status,
        }

    @classmethod
    def _compute_verification_status(
        cls,
        match: Match,
        submissions: List[MatchResultSubmission],
    ) -> Dict[str, Any]:
        """
        Smart Mismatch Detection.

        Returns:
          {
            'code': 'match' | 'mismatch' | 'pending' | 'finalized',
            'label': str,
            'detail': str,
          }
        """
        if match.state in ('completed', 'forfeit'):
            return {
                'code': 'finalized',
                'label': 'Finalized',
                'detail': f'Final score: {match.participant1_score}–{match.participant2_score}',
            }

        active = [s for s in submissions if s.status not in ('rejected',)]
        if len(active) == 0:
            return {
                'code': 'pending',
                'label': 'Pending',
                'detail': 'No submissions received yet.',
            }
        if len(active) == 1:
            s = active[0]
            p = s.raw_result_payload or {}
            return {
                'code': 'pending',
                'label': 'Pending',
                'detail': (
                    f'Only 1 submission received '
                    f'({p.get("score_p1", "?")}–{p.get("score_p2", "?")}).'
                    f' Waiting for opponent.'
                ),
            }

        # Two or more active submissions — compare
        s1, s2 = active[0], active[1]
        p1 = s1.raw_result_payload or {}
        p2 = s2.raw_result_payload or {}
        s1_p1 = p1.get('score_p1')
        s1_p2 = p1.get('score_p2')
        s2_p1 = p2.get('score_p1')
        s2_p2 = p2.get('score_p2')

        if s1_p1 == s2_p1 and s1_p2 == s2_p2:
            return {
                'code': 'match',
                'label': 'Match',
                'detail': f'Both submissions agree: {s1_p1}–{s1_p2}. Auto-confirm available.',
            }
        else:
            return {
                'code': 'mismatch',
                'label': 'Mismatch',
                'detail': (
                    f'Captain A reported {s1_p1}–{s1_p2}, '
                    f'Captain B reported {s2_p1}–{s2_p2}.'
                ),
            }

    # ── S9-B2: Verify / Confirm / Dispute ────────────────────

    @classmethod
    @transaction.atomic
    def verify_match(
        cls,
        match_id: int,
        tournament: Tournament,
        *,
        action: str,
        user_id: int,
        p1_score: Optional[int] = None,
        p2_score: Optional[int] = None,
        notes: str = '',
        reason_code: str = 'other',
    ) -> Dict[str, Any]:
        """
        Sprint 9 verification action.

        action:
            'confirm'  — Finalize match with the given scores.
            'dispute'  — Open a DisputeRecord, set match state to disputed.
            'note'     — Add an admin note (no state change).
        """
        match = Match.objects.select_for_update().get(
            pk=match_id, tournament=tournament,
        )
        submissions = list(
            MatchResultSubmission.objects.filter(match=match)
            .order_by('submitted_at')
        )

        if action == 'confirm':
            return cls._action_confirm(match, submissions, user_id, p1_score, p2_score, notes)
        elif action == 'dispute':
            return cls._action_dispute(match, submissions, user_id, notes, reason_code)
        elif action == 'note':
            return cls._action_add_note(match, user_id, notes)
        else:
            raise ValueError(f'Unknown verify action: {action}')

    @classmethod
    def _action_confirm(cls, match, submissions, user_id, p1_score, p2_score, notes):
        """Confirm & finalize the match result."""
        if p1_score is None or p2_score is None:
            raise ValueError('Scores are required for confirm action.')

        match.participant1_score = p1_score
        match.participant2_score = p2_score
        if p1_score > p2_score:
            match.winner_id = match.participant1_id
            match.loser_id = match.participant2_id
        elif p2_score > p1_score:
            match.winner_id = match.participant2_id
            match.loser_id = match.participant1_id
        else:
            match.winner_id = None
            match.loser_id = None
        match.state = Match.COMPLETED
        match.completed_at = timezone.now()
        match.save()

        # Mark submissions finalized
        for s in submissions:
            if s.status not in ('rejected', 'finalized'):
                s.status = MatchResultSubmission.STATUS_FINALIZED
                s.finalized_at = timezone.now()
                s.organizer_notes = notes or s.organizer_notes
                s.save(update_fields=['status', 'finalized_at', 'organizer_notes'])

        # Audit log
        for s in submissions:
            ResultVerificationLog.objects.create(
                submission=s,
                step=ResultVerificationLog.STEP_FINALIZATION,
                status=ResultVerificationLog.STATUS_SUCCESS,
                details={
                    'final_score': f'{p1_score}–{p2_score}',
                    'notes': notes,
                },
                performed_by_id=user_id,
            )

        return {
            'status': 'confirmed',
            'match': cls._serialize_match(match),
        }

    @classmethod
    def _action_dispute(cls, match, submissions, user_id, notes, reason_code):
        """Open a dispute against the latest submission."""
        match.state = Match.DISPUTED if hasattr(Match, 'DISPUTED') else 'disputed'
        match.save(update_fields=['state'])

        target_sub = submissions[-1] if submissions else None
        dispute = None
        if target_sub:
            dispute = DisputeRecord.objects.create(
                submission=target_sub,
                opened_by_user_id=user_id,
                status=DisputeRecord.OPEN,
                reason_code=reason_code,
                description=notes or 'Opened by organizer during verification review.',
            )
            # Audit
            ResultVerificationLog.objects.create(
                submission=target_sub,
                step=ResultVerificationLog.STEP_DISPUTE_ESCALATED,
                status=ResultVerificationLog.STATUS_SUCCESS,
                details={'reason_code': reason_code, 'notes': notes},
                performed_by_id=user_id,
            )

        return {
            'status': 'disputed',
            'match': cls._serialize_match(match),
            'dispute_id': dispute.id if dispute else None,
        }

    @classmethod
    def _action_add_note(cls, match, user_id, notes):
        """Add an admin note to lobby_info."""
        note_list = match.lobby_info.get('notes', [])
        note_list.append({
            'text': notes,
            'user_id': user_id,
            'created_at': timezone.now().isoformat(),
        })
        match.lobby_info['notes'] = note_list
        match.save(update_fields=['lobby_info'])
        return {
            'status': 'noted',
            'match': cls._serialize_match(match),
            'notes': note_list,
        }

    # ── Group label cache ────────────────────────────────────

    @classmethod
    def _build_group_cache(
        cls,
        tournament: Tournament,
        participant_ids: Optional[set[int]] = None,
    ) -> Dict[int, str]:
        """Map participant_id to group name for the tournament."""
        cache: Dict[int, str] = {}
        if GroupStanding is None:
            return cache
        try:
            standings_qs = GroupStanding.objects.filter(group__tournament=tournament)
            if participant_ids:
                standings_qs = standings_qs.filter(
                    Q(team_id__in=participant_ids) | Q(user_id__in=participant_ids)
                )

            standings = standings_qs.select_related('group').only(
                'user_id',
                'team_id',
                'group__name',
            )
            for gs in standings:
                key = gs.team_id or gs.user_id
                if key:
                    cache[key] = gs.group.name
        except Exception:
            pass
        return cache

    @classmethod
    def _resolve_group_label(cls, m: Match, group_cache: Optional[Dict[int, str]] = None) -> str:
        """Derive group label for a match."""
        # 1. lobby_info (set during match generation)
        label = (m.lobby_info or {}).get('group_label', '')
        if label:
            return label
        # 2. Lookup via participants in group standings cache
        if group_cache:
            label = group_cache.get(m.participant1_id) or group_cache.get(m.participant2_id) or ''
        return label

    # ── Private helpers ──────────────────────────────────────

    @staticmethod
    def _safe_game_scores(m):
        """
        Always return a normalised list of game-score dicts for the frontend.
        Handles dict-with-maps format, list format, string, or None.
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

    # ── Private serializer ───────────────────────────────────

    @classmethod
    def _serialize_match(cls, m: Match, *, group_cache: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
        lobby = m.lobby_info or {}
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
            'is_paused': lobby.get('paused', False),
            'notes_count': len(lobby.get('notes', [])),
            # Sprint 26 additions
            'bracket_id': m.bracket_id,
            'group_label': cls._resolve_group_label(m, group_cache),
            'lobby_info': {
                'lobby_code': lobby.get('lobby_code', ''),
                'password': lobby.get('password', ''),
                'map': lobby.get('map', ''),
                'server': lobby.get('server', ''),
                'game_mode': lobby.get('game_mode', ''),
            },
            'participant1_checked_in': getattr(m, 'participant1_checked_in', False),
            'participant2_checked_in': getattr(m, 'participant2_checked_in', False),
            'check_in_deadline': m.check_in_deadline.isoformat() if getattr(m, 'check_in_deadline', None) else None,
            # Series (BO3/BO5)
            'best_of': getattr(m, 'best_of', 1),
            'game_scores': cls._safe_game_scores(m),
        }
