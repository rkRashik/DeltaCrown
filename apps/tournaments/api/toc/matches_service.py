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

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Count
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


_PURE_KNOCKOUT_FORMATS = frozenset({
    'single_elimination',
    'double_elimination',
})

# Formats whose later phase becomes a knockout bracket. Group-stage matches
# in these formats still need to read as 'group_stage' — bracket_id linkage
# decides per-match.
_HYBRID_KNOCKOUT_FORMATS = frozenset({
    'group_playoff',
})


from apps.tournaments.services.round_naming import (
    knockout_round_label as _knockout_round_label,
)


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
        stage: Optional[str] = None,
        page: int = 1,
        page_size: int = 60,
    ) -> Dict[str, Any]:
        page = max(1, int(page or 1))
        page_size = int(page_size or 60)
        page_size = min(120, max(10, page_size))

        # Canonical read model — authoritative source for stage/round_number.
        # We filter on the canonical (BracketNode-backed) round_number and
        # stage, then pull the corresponding Match rows for full serialisation.
        from apps.tournaments.services.match_read_model import MatchReadModel
        read_model = MatchReadModel.for_tournament(tournament)
        canonical_views = read_model.filter(
            state=state if state else None,
            stage=stage if stage else None,
            round_number=int(round_number) if round_number else None,
            search=search if search else None,
        )
        # Build an id → view map so the serialization path can overlay
        # canonical stage/round_label onto each Match.
        view_by_id = {v['match_id']: v for v in canonical_views}
        visible_match_ids = list(view_by_id.keys())

        qs = Match.objects.filter(
            tournament=tournament,
            is_deleted=False,
            pk__in=visible_match_ids,
        ).order_by('round_number', 'match_number')
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
        participant_media_map = cls._build_participant_media_map(tournament, participant_ids=participant_ids)

        # Pre-load bracket round names for knockout matches.
        # Derive total_rounds for the tournament so we can label knockout
        # matches as Quarterfinal/Semifinal/Final even when bracket linkage
        # is missing (single_elim/double_elim tournaments where matches
        # were generated without bracket_id assignment).
        tournament_format = (getattr(tournament, 'format', '') or '').lower()
        max_round_in_page = max(
            (int(m.round_number or 0) for m in page_matches),
            default=0,
        )
        try:
            total_rounds = max(
                int(r or 0)
                for r in Match.objects.filter(
                    tournament=tournament, is_deleted=False,
                ).values_list('round_number', flat=True)
            ) if page_matches else 0
        except (ValueError, TypeError):
            total_rounds = max_round_in_page

        # Canonical labels/stage come from the read_model built above.
        bracket = read_model.bracket
        total_rounds = read_model.total_rounds
        bracket_round_names = {
            m.id: (view_by_id.get(m.id, {}).get('round_label') or '')
            for m in page_matches
        }

        matches = [
            cls._serialize_match(
                m,
                tournament=tournament,
                group_cache=group_cache,
                participant_media_map=participant_media_map,
                bracket_round_label=bracket_round_names.get(m.id, ''),
                tournament_format=tournament_format,
                canonical_view=view_by_id.get(m.id),
            )
            for m in page_matches
        ]

        # Determine current tournament stage
        current_stage = None
        if hasattr(tournament, 'get_current_stage'):
            current_stage = tournament.get_current_stage()

        total_pages = max(1, int(ceil(total / float(page_size)))) if page_size else 1
        has_next = page < total_pages
        has_prev = page > 1

        # Build a stable round filter list from the canonical read model so
        # the dropdown shows Quarterfinals/Semifinals/Final consistently and
        # selecting a round routes to the canonical round_number (which may
        # differ from Match.round_number when bracket node coordinates are
        # authoritative).
        round_options = read_model.round_options()

        return {
            'matches': matches,
            'total_count': total,
            'state_counts': state_counts,
            'current_stage': current_stage,
            'round_options': round_options,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total,
                'total_pages': total_pages,
                'has_next': has_next,
                'has_prev': has_prev,
            },
        }

    @classmethod
    def _build_round_options(
        cls,
        *,
        tournament: Tournament,
        tournament_format: str,
        bracket,
        total_rounds: int,
    ) -> List[Dict[str, Any]]:
        """
        Build `[{value, label, stage}]` for the round filter dropdown.

        Routes ALL labels through the canonical helper so the dropdown
        always agrees with match cards.
        """
        from types import SimpleNamespace
        from apps.tournaments.services.match_classification import (
            compute_round_label,
            classify_stage,
            tournament_total_rounds,
        )

        rows = (
            Match.objects.filter(tournament=tournament, is_deleted=False)
            .exclude(round_number__isnull=True)
            .values_list('round_number', 'bracket_id')
            .distinct()
        )
        if not rows:
            return []

        if bracket is None:
            from apps.brackets.models import Bracket as _Bracket
            try:
                bracket = _Bracket.objects.filter(tournament=tournament).first()
            except Exception:
                bracket = None

        full_total_rounds = tournament_total_rounds(tournament, bracket=bracket)

        seen = set()
        options: List[Dict[str, Any]] = []
        for round_number, bracket_id in rows:
            if not round_number or round_number in seen:
                continue
            seen.add(round_number)
            shim = SimpleNamespace(
                round_number=round_number,
                bracket_id=bracket_id,
            )
            label = compute_round_label(
                tournament, shim,
                bracket=bracket,
                total_rounds=full_total_rounds,
            ) or f'Round {round_number}'
            stage = classify_stage(tournament, shim)
            options.append({
                'value': int(round_number),
                'label': label,
                'stage': stage,
            })
        options.sort(key=lambda o: o['value'])
        return options

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
        winner_side: Optional[Any] = None,
        football_stats: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        match = Match.objects.get(pk=match_id, tournament=tournament)
        previous_state = match.state
        previous_winner_id = match.winner_id
        normalized_winner_side = cls._normalize_winner_side(winner_side)
        try:
            actor_username = cls._resolve_username(user_id)
            updated = MatchService.organizer_override_score(
                match=match,
                score1=p1_score,
                score2=p2_score,
                reason='TOC organizer score override',
                overridden_by_username=actor_username,
                winner_side=normalized_winner_side,
            )
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        except (AttributeError, TypeError) as exc:
            logger.warning('organizer_override_score unavailable (%s), using fallback', exc)
            draw_allowed = cls._draws_allowed_for_match(match)
            match.participant1_score = p1_score
            match.participant2_score = p2_score

            if p1_score == p2_score:
                if draw_allowed:
                    match.winner_id = None
                    match.loser_id = None
                else:
                    if normalized_winner_side == 1:
                        match.winner_id = match.participant1_id
                        match.loser_id = match.participant2_id
                    elif normalized_winner_side == 2:
                        match.winner_id = match.participant2_id
                        match.loser_id = match.participant1_id
                    else:
                        raise ValueError('Tied scores require selecting a winner for this format.')
            elif p1_score > p2_score:
                match.winner_id = match.participant1_id
                match.loser_id = match.participant2_id
            else:
                match.winner_id = match.participant2_id
                match.loser_id = match.participant1_id

            if match.state not in ('completed', 'cancelled'):
                match.state = Match.COMPLETED
                match.completed_at = timezone.now()
            match.save()
            updated = match

        cls._sync_bracket_progression_if_needed(
            updated,
            previous_state=previous_state,
            previous_winner_id=previous_winner_id,
        )
        if football_stats is not None:
            cls._persist_football_stats(updated, football_stats, user_id=user_id)
        return cls._serialize_match(updated)

    @staticmethod
    def _persist_football_stats(match: Match, payload: Any, *, user_id: int) -> None:
        """Write organizer-entered football stats into ``match.lobby_info``.

        ``payload`` is dropped silently if not a mapping. Per-team values are
        clamped to safe ranges so a bad form post can't poison the JSON
        column. ``goals`` mirrors ``participantN_score`` so the stats card
        stays in sync with the headline score.
        """
        if not isinstance(payload, dict):
            return

        def _team(side_payload, score_fallback):
            if not isinstance(side_payload, dict):
                side_payload = {}

            def _int_clamped(value, *, fallback=0, minimum=0, maximum=999):
                try:
                    parsed = int(float(value))
                except (TypeError, ValueError):
                    parsed = int(fallback)
                return max(minimum, min(maximum, parsed))

            return {
                'display_name': str(side_payload.get('display_name') or '').strip()[:80],
                'goals': _int_clamped(side_payload.get('goals'), fallback=score_fallback, maximum=99),
                'penalties': _int_clamped(side_payload.get('penalties'), fallback=0, maximum=99),
                'possession_pct': _int_clamped(side_payload.get('possession_pct'), maximum=100),
                'shots': _int_clamped(side_payload.get('shots'), maximum=99),
                'shots_on_target': _int_clamped(side_payload.get('shots_on_target'), maximum=99),
                'passes_completed': _int_clamped(side_payload.get('passes_completed'), maximum=9999),
                'pass_accuracy_pct': _int_clamped(side_payload.get('pass_accuracy_pct'), maximum=100),
            }

        team1 = _team(payload.get('team1'), match.participant1_score or 0)
        team2 = _team(payload.get('team2'), match.participant2_score or 0)

        lobby_info = dict(match.lobby_info or {})
        lobby_info['football_stats'] = {
            'team1': team1,
            'team2': team2,
            'has_penalties': bool(payload.get('has_penalties'))
                or team1['penalties'] > 0 or team2['penalties'] > 0,
            'updated_at': timezone.now().isoformat(),
            'updated_by': int(user_id) if user_id else None,
        }
        match.lobby_info = lobby_info
        match.save(update_fields=['lobby_info'])

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
        previous_state = match.state
        previous_winner_id = match.winner_id
        match.state = Match.COMPLETED
        match.completed_at = timezone.now()
        match.lobby_info['force_completed_by'] = user_id
        match.save(update_fields=['state', 'completed_at', 'lobby_info'])
        cls._sync_bracket_progression_if_needed(
            match,
            previous_state=previous_state,
            previous_winner_id=previous_winner_id,
        )
        return cls._serialize_match(match)

    @classmethod
    @transaction.atomic
    def reset_match(cls, match_id: int, tournament: Tournament, *, user_id: int) -> Dict[str, Any]:
        """Reset score, verification artifacts, and state for a match."""
        match = Match.objects.select_for_update().get(pk=match_id, tournament=tournament)

        submission_ids = list(
            MatchResultSubmission.objects.filter(match=match).values_list('id', flat=True)
        )
        if submission_ids:
            ResultVerificationLog.objects.filter(submission_id__in=submission_ids).delete()
            DisputeRecord.objects.filter(submission_id__in=submission_ids).delete()
            MatchResultSubmission.objects.filter(id__in=submission_ids).delete()

        lobby_info = dict(match.lobby_info or {})
        for key in ('paused', 'paused_at', 'resumed_at', 'force_completed_by', 'score_override', 'forfeit'):
            lobby_info.pop(key, None)

        workflow = lobby_info.get('match_lobby_workflow')
        if isinstance(workflow, dict):
            workflow['result_status'] = 'pending'
            workflow.pop('final_result', None)
            workflow.pop('result_submissions', None)
            if str(workflow.get('phase') or '').lower() in ('results', 'completed'):
                workflow['phase'] = 'lobby_setup'
            lobby_info['match_lobby_workflow'] = workflow

        match.participant1_score = 0
        match.participant2_score = 0
        match.winner_id = None
        match.loser_id = None
        match.started_at = None
        match.completed_at = None

        if match.participant1_checked_in and match.participant2_checked_in:
            match.state = Match.READY
        elif match.participant1_checked_in or match.participant2_checked_in:
            match.state = Match.CHECK_IN
        else:
            match.state = Match.SCHEDULED

        lobby_info['reset'] = {
            'reset_at': timezone.now().isoformat(),
            'reset_by_user_id': user_id,
        }
        match.lobby_info = lobby_info
        match.save(
            update_fields=[
                'state',
                'participant1_score',
                'participant2_score',
                'winner_id',
                'loser_id',
                'started_at',
                'completed_at',
                'lobby_info',
                'updated_at',
            ]
        )
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
        previous_state = match.state
        previous_winner_id = match.winner_id
        try:
            if forfeiter_id == match.participant1_id:
                forfeiting_participant = 1
            elif forfeiter_id == match.participant2_id:
                forfeiting_participant = 2
            else:
                raise ValueError('Forfeiter must be one of the match participants.')

            actor_username = cls._resolve_username(user_id)
            updated = MatchService.organizer_forfeit_match(
                match=match,
                forfeiting_participant=forfeiting_participant,
                reason='TOC organizer forfeit',
                forfeited_by_username=actor_username,
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

        cls._sync_bracket_progression_if_needed(
            updated,
            previous_state=previous_state,
            previous_winner_id=previous_winner_id,
        )
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

        # Canonical participant resolution — bracket node beats raw TBA Match.
        try:
            from apps.tournaments.services.match_read_model import MatchReadModel
            _detail_rm = MatchReadModel.for_tournament(tournament)
            _detail_canonical_view = _detail_rm.by_id(match.id)
        except Exception:
            _detail_canonical_view = None

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
            'match': cls._serialize_match(
                match,
                canonical_view=_detail_canonical_view,
                tournament=tournament,
            ),
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

        previous_state = match.state
        previous_winner_id = match.winner_id

        try:
            p1_score = int(p1_score)
            p2_score = int(p2_score)
        except (TypeError, ValueError) as exc:
            raise ValueError('Scores must be valid integers.') from exc
        if p1_score < 0 or p2_score < 0:
            raise ValueError('Scores must be non-negative.')

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

        cls._sync_bracket_progression_if_needed(
            match,
            previous_state=previous_state,
            previous_winner_id=previous_winner_id,
        )

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
    def _sync_bracket_progression_if_needed(
        cls,
        match: Match,
        *,
        previous_state: Optional[str] = None,
        previous_winner_id: Optional[int] = None,
    ) -> None:
        """Advance bracket state when a match reaches terminal status with a winner."""
        terminal_states = (Match.COMPLETED, Match.FORFEIT)
        if match.state not in terminal_states:
            return
        if not match.winner_id:
            return
        # Transition-based progression is handled centrally via Match post-save signals.
        # This helper only covers terminal-to-terminal winner corrections.
        if previous_state not in terminal_states:
            return
        if previous_winner_id == match.winner_id:
            return

        try:
            from apps.tournaments.services.bracket_service import BracketService

            BracketService.update_bracket_after_match(match)
        except Exception as exc:
            logger.warning('Failed to advance bracket for match %s: %s', match.id, exc)

        try:
            MatchService.check_and_activate_gf_reset(match)
        except Exception as exc:
            logger.warning('Failed to evaluate GF reset for match %s: %s', match.id, exc)

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

    @staticmethod
    def _resolve_stage(m: Match, tournament_format: str) -> str:
        """Delegate to the canonical classifier (single source of truth)."""
        from apps.tournaments.services.match_classification import classify_stage
        # `tournament_format` may not carry a tournament object; build a
        # minimal shim so we don't need a DB roundtrip.
        from types import SimpleNamespace
        return classify_stage(SimpleNamespace(format=tournament_format), m)

    # ── Private helpers ──────────────────────────────────────

    @staticmethod
    def _coerce_optional_bool(value: Any) -> Optional[bool]:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        token = str(value).strip().lower()
        if token in {'1', 'true', 'yes', 'y', 'on', 'allow', 'allowed', 'enabled'}:
            return True
        if token in {'0', 'false', 'no', 'n', 'off', 'disallow', 'disallowed', 'disabled', ''}:
            return False
        return None

    @staticmethod
    def _normalize_winner_side(value: Any) -> Optional[Any]:
        if value is None:
            return None
        token = str(value).strip().lower()
        if token in {'', 'none', 'null'}:
            return None
        if token in {'1', 'a', 'p1', 'participant1', 'left', 'team1'}:
            return 1
        if token in {'2', 'b', 'p2', 'participant2', 'right', 'team2'}:
            return 2
        if token in {'draw', 'tie', 'd'}:
            return 'draw'
        return None

    @classmethod
    def _draws_allowed_for_match(cls, match: Match, tournament: Optional[Tournament] = None) -> bool:
        try:
            return bool(MatchService.draws_allowed_for_match(match))
        except Exception:
            pass

        if tournament is None:
            tournament = getattr(match, 'tournament', None)
        if tournament is None:
            return False

        format_token = str(getattr(tournament, 'format', '') or '').strip().lower()
        format_default = format_token in {
            str(Tournament.ROUND_ROBIN).lower(),
            str(Tournament.GROUP_PLAYOFF).lower(),
            'group_stage',
            'league',
        }

        lobby_info = match.lobby_info if isinstance(match.lobby_info, dict) else {}
        match_settings = lobby_info.get('match_settings') if isinstance(lobby_info.get('match_settings'), dict) else {}
        for key in ('allow_draws', 'draw_allowed', 'draws_allowed'):
            parsed = cls._coerce_optional_bool(match_settings.get(key))
            if parsed is not None:
                return parsed

        tournament_settings = getattr(tournament, 'settings', None)
        if isinstance(tournament_settings, dict):
            nested_match_settings = (
                tournament_settings.get('match_settings')
                if isinstance(tournament_settings.get('match_settings'), dict)
                else {}
            )
            for key in ('allow_draws', 'draw_allowed', 'draws_allowed'):
                parsed = cls._coerce_optional_bool(nested_match_settings.get(key))
                if parsed is not None:
                    return parsed
            for key in ('allow_draws', 'draw_allowed', 'draws_allowed'):
                parsed = cls._coerce_optional_bool(tournament_settings.get(key))
                if parsed is not None:
                    return parsed

        game = getattr(tournament, 'game', None)
        game_config = getattr(game, 'tournament_config', None)
        if isinstance(game_config, dict):
            for key in ('allow_draws', 'draw_allowed', 'draws_allowed'):
                parsed = cls._coerce_optional_bool(game_config.get(key))
                if parsed is not None:
                    return parsed

        return format_default

    @staticmethod
    def _normalize_media_url(value: Any) -> str:
        raw = str(value or '').strip()
        if not raw:
            return ''
        if raw.startswith('http://') or raw.startswith('https://'):
            return raw
        if raw.startswith('/'):
            return raw
        return '/media/' + raw

    @staticmethod
    def _user_avatar_url(user) -> str:
        if not user:
            return ''
        try:
            profile = getattr(user, 'profile', None)
            avatar = getattr(profile, 'avatar', None)
            if avatar:
                return TOCMatchesService._normalize_media_url(avatar.url)
        except Exception:
            pass
        username = str(getattr(user, 'username', '') or '').strip() or 'User'
        return f"https://ui-avatars.com/api/?name={username[:2]}&background=0A0A0E&color=fff&size=64"

    @classmethod
    def _build_participant_media_map(
        cls,
        tournament: Tournament,
        *,
        participant_ids: Optional[set] = None,
    ) -> Dict[int, str]:
        if tournament is None:
            return {}

        normalized_ids = set()
        for raw_id in participant_ids or set():
            if not raw_id:
                continue
            try:
                normalized_ids.add(int(raw_id))
            except (TypeError, ValueError):
                continue

        if not normalized_ids:
            return {}

        media_map: Dict[int, str] = {}
        is_team = str(getattr(tournament, 'participation_type', '') or '').lower() == 'team'

        if is_team:
            try:
                from apps.organizations.models import Team
                for team in Team.objects.filter(id__in=normalized_ids).only('id', 'logo'):
                    logo_url = ''
                    try:
                        if getattr(team, 'logo', None):
                            logo_url = cls._normalize_media_url(team.logo.url)
                    except Exception:
                        logo_url = ''
                    media_map[int(team.id)] = logo_url
            except Exception:
                return media_map

            # Fallback: for teams without logos, use registrant avatar
            empty_team_ids = {tid for tid, url in media_map.items() if not url}
            if empty_team_ids:
                try:
                    from apps.tournaments.models.registration import Registration
                    for reg in Registration.objects.filter(
                        tournament=tournament,
                        team_id__in=empty_team_ids,
                    ).select_related('user', 'user__profile')[:len(empty_team_ids)]:
                        if reg.team_id and not media_map.get(int(reg.team_id)):
                            media_map[int(reg.team_id)] = cls._user_avatar_url(reg.user)
                except Exception:
                    pass
            return media_map

        try:
            User = get_user_model()
            users = User.objects.filter(id__in=normalized_ids).select_related('profile')
            for user in users:
                media_map[int(user.id)] = cls._user_avatar_url(user)
        except Exception:
            pass
        return media_map

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

    @staticmethod
    def _resolve_username(user_id: int) -> str:
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            return 'system'
        if uid <= 0:
            return 'system'

        try:
            username = (
                get_user_model()
                .objects.filter(id=uid)
                .values_list('username', flat=True)
                .first()
            )
            if username:
                return str(username)
        except Exception:
            pass

        return f'user-{uid}'

    # ── Private serializer ───────────────────────────────────

    @classmethod
    def _serialize_match(
        cls,
        m: Match,
        *,
        tournament: Optional[Tournament] = None,
        group_cache: Optional[Dict[int, str]] = None,
        participant_media_map: Optional[Dict[int, str]] = None,
        bracket_round_label: str = '',
        tournament_format: str = '',
        canonical_view: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        lobby = m.lobby_info if isinstance(m.lobby_info, dict) else {}
        if tournament is None:
            tournament = getattr(m, 'tournament', None)
        if not tournament_format and tournament is not None:
            tournament_format = (getattr(tournament, 'format', '') or '').lower()
        if participant_media_map is None:
            participant_media_map = cls._build_participant_media_map(
                tournament,
                participant_ids={m.participant1_id, m.participant2_id},
            )

        p1_logo_url = str(participant_media_map.get(m.participant1_id, '') or '')
        p2_logo_url = str(participant_media_map.get(m.participant2_id, '') or '')

        winner_side = 0
        winner_name = ''
        winner_logo_url = ''
        if m.winner_id and m.winner_id == m.participant1_id:
            winner_side = 1
            winner_name = str(m.participant1_name or '')
            winner_logo_url = p1_logo_url
        elif m.winner_id and m.winner_id == m.participant2_id:
            winner_side = 2
            winner_name = str(m.participant2_name or '')
            winner_logo_url = p2_logo_url

        draw_allowed = cls._draws_allowed_for_match(m, tournament=tournament)

        # Overlay canonical stage/round/participant fields from the read model.
        # The bracket tree is authoritative for knockout matches — a TBA
        # match row should never win over a node that knows the real team.
        canonical_stage = canonical_view.get('stage') if canonical_view else None
        canonical_round_number = (
            canonical_view.get('round_number') if canonical_view else None
        )
        canonical_match_number = (
            canonical_view.get('match_number') if canonical_view else None
        )
        resolved_stage = canonical_stage or cls._resolve_stage(m, tournament_format)
        resolved_round_number = (
            canonical_round_number if canonical_round_number is not None
            else m.round_number
        )
        resolved_match_number = (
            canonical_match_number if canonical_match_number is not None
            else m.match_number
        )
        resolved_round_label = (
            (canonical_view.get('round_label') if canonical_view else '')
            or bracket_round_label or ''
        )
        # Canonical participant slots (node-first).
        if canonical_view:
            c_p1_id = canonical_view.get('participant1_id')
            c_p1_name = canonical_view.get('participant1_name') or ''
            c_p2_id = canonical_view.get('participant2_id')
            c_p2_name = canonical_view.get('participant2_name') or ''
            c_winner_id = canonical_view.get('winner_id') or m.winner_id
            c_winner_name = canonical_view.get('winner_name') or ''
            c_winner_side = canonical_view.get('winner_side') or 0
        else:
            c_p1_id = m.participant1_id
            c_p1_name = m.participant1_name or ''
            c_p2_id = m.participant2_id
            c_p2_name = m.participant2_name or ''
            c_winner_id = m.winner_id
            c_winner_name = ''
            c_winner_side = 0

        # Re-derive winner display when canonical_view didn't fill it.
        if not c_winner_name and c_winner_id:
            if c_winner_id == c_p1_id:
                c_winner_name = c_p1_name
                c_winner_side = 1
            elif c_winner_id == c_p2_id:
                c_winner_name = c_p2_name
                c_winner_side = 2

        # Recompute logos based on canonical participant IDs (not raw).
        c_p1_logo_url = str(participant_media_map.get(c_p1_id, '') or '') if c_p1_id else ''
        c_p2_logo_url = str(participant_media_map.get(c_p2_id, '') or '') if c_p2_id else ''
        c_winner_logo_url = ''
        if c_winner_side == 1:
            c_winner_logo_url = c_p1_logo_url
        elif c_winner_side == 2:
            c_winner_logo_url = c_p2_logo_url

        return {
            'id': m.id,
            'round_number': resolved_round_number,
            'match_number': resolved_match_number,
            'participant1_id': c_p1_id,
            'participant1_name': c_p1_name,
            'participant1_logo_url': c_p1_logo_url,
            'p1_logo_url': c_p1_logo_url,
            'participant2_id': c_p2_id,
            'participant2_name': c_p2_name,
            'participant2_logo_url': c_p2_logo_url,
            'p2_logo_url': c_p2_logo_url,
            'participant1_score': m.participant1_score,
            'participant2_score': m.participant2_score,
            'state': m.state,
            'winner_id': c_winner_id,
            'loser_id': m.loser_id,
            'winner_side': c_winner_side,
            'winner_name': c_winner_name,
            'winner_logo_url': c_winner_logo_url,
            'draw_allowed': draw_allowed,
            'scheduled_time': m.scheduled_time.isoformat() if m.scheduled_time else None,
            'started_at': m.started_at.isoformat() if m.started_at else None,
            'completed_at': m.completed_at.isoformat() if m.completed_at else None,
            'stream_url': m.stream_url,
            'is_paused': lobby.get('paused', False),
            'notes_count': len(lobby.get('notes', [])),
            # Sprint 26 additions
            'bracket_id': m.bracket_id,
            'bracket_node_id': canonical_view.get('bracket_node_id') if canonical_view else None,
            'source': canonical_view.get('source', 'match') if canonical_view else 'match',
            'group_label': cls._resolve_group_label(m, group_cache),
            'stage': resolved_stage,
            'bracket_round_label': resolved_round_label,
            # Raw fields preserved for debugging / repair tooling.
            'raw_round_number': m.round_number,
            'raw_match_number': m.match_number,
            'raw_participant1_id': m.participant1_id,
            'raw_participant1_name': m.participant1_name or '',
            'raw_participant2_id': m.participant2_id,
            'raw_participant2_name': m.participant2_name or '',
            'lobby_info': {
                'lobby_code': lobby.get('lobby_code', ''),
                'password': lobby.get('password', ''),
                'map': lobby.get('map', ''),
                'server': lobby.get('server', ''),
                'game_mode': lobby.get('game_mode', ''),
                'football_stats': (
                    lobby.get('football_stats')
                    if isinstance(lobby.get('football_stats'), dict)
                    else None
                ),
            },
            'participant1_checked_in': getattr(m, 'participant1_checked_in', False),
            'participant2_checked_in': getattr(m, 'participant2_checked_in', False),
            'check_in_deadline': m.check_in_deadline.isoformat() if getattr(m, 'check_in_deadline', None) else None,
            # Series (BO3/BO5)
            'best_of': getattr(m, 'best_of', 1),
            'game_scores': cls._safe_game_scores(m),
        }
