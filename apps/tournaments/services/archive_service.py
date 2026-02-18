"""
Tournament Archive Service — Generate and persist a read-only archive snapshot.

When a tournament transitions to ARCHIVED status, this service creates a
comprehensive JSON snapshot of all tournament data: config, participants,
matches, brackets, standings, prizes, and certificates.

The archive is stored in the tournament's ``config['archive']`` JSON field
and optionally exported to cloud storage as a static JSON file.

Usage:
    from apps.tournaments.services.archive_service import ArchiveService

    # Generate archive for a completed/archived tournament
    archive = ArchiveService.generate(tournament_id=42)

    # Retrieve a previously generated archive
    data = ArchiveService.get_archive(tournament_id=42)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.tournaments.models.tournament import Tournament

logger = logging.getLogger(__name__)


class ArchiveService:
    """Generates and manages tournament archive snapshots."""

    ARCHIVE_VERSION = 1

    @classmethod
    @transaction.atomic
    def generate(cls, tournament_id: int) -> Dict[str, Any]:
        """
        Generate a comprehensive archive snapshot for a tournament.

        Args:
            tournament_id: PK of the tournament.

        Returns:
            The archive dict (also persisted in tournament.config['archive']).

        Raises:
            Tournament.DoesNotExist: if tournament not found.
            ValidationError: if tournament is not COMPLETED or ARCHIVED.
        """
        tournament = (
            Tournament.objects
            .select_related('game', 'organizer')
            .get(id=tournament_id)
        )

        if tournament.status not in (Tournament.COMPLETED, Tournament.ARCHIVED):
            raise ValidationError(
                f"Cannot archive tournament with status '{tournament.status}'. "
                "Must be COMPLETED or ARCHIVED."
            )

        archive: Dict[str, Any] = {
            'version': cls.ARCHIVE_VERSION,
            'generated_at': timezone.now().isoformat(),
            'tournament': cls._snapshot_tournament(tournament),
            'participants': cls._snapshot_participants(tournament),
            'matches': cls._snapshot_matches(tournament),
            'brackets': cls._snapshot_brackets(tournament),
            'standings': cls._snapshot_standings(tournament),
            'prizes': cls._snapshot_prizes(tournament),
            'groups': cls._snapshot_groups(tournament),
            'statistics': cls._snapshot_statistics(tournament),
        }

        # Persist in config
        config = tournament.config or {}
        config['archive'] = archive
        tournament.config = config
        tournament.save(update_fields=['config'])

        logger.info(
            "Archive generated for tournament %s (%s): %d participants, %d matches",
            tournament.id, tournament.name,
            len(archive['participants']),
            len(archive['matches']),
        )

        return archive

    @classmethod
    def get_archive(cls, tournament_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a previously generated archive from the config field."""
        tournament = Tournament.objects.get(id=tournament_id)
        config = tournament.config or {}
        return config.get('archive')

    # ── snapshot helpers ───────────────────────────────────────────────

    @classmethod
    def _snapshot_tournament(cls, t: Tournament) -> Dict[str, Any]:
        return {
            'id': t.id,
            'name': t.name,
            'slug': t.slug,
            'description': t.description,
            'status': t.status,
            'format': t.format,
            'participation_type': t.participation_type,
            'game': {
                'id': t.game_id,
                'name': t.game.name if t.game else None,
                'slug': t.game.slug if t.game else None,
            },
            'organizer': {
                'id': t.organizer_id,
                'username': t.organizer.username if t.organizer else None,
            },
            'max_participants': t.max_participants,
            'min_participants': t.min_participants,
            'prize_pool': str(t.prize_pool) if t.prize_pool else '0',
            'prize_currency': t.prize_currency,
            'prize_distribution': t.prize_distribution,
            'entry_fee_amount': str(t.entry_fee_amount) if t.entry_fee_amount else '0',
            'registration_start': t.registration_start.isoformat() if t.registration_start else None,
            'registration_end': t.registration_end.isoformat() if t.registration_end else None,
            'tournament_start': t.tournament_start.isoformat() if t.tournament_start else None,
            'tournament_end': t.tournament_end.isoformat() if t.tournament_end else None,
            'published_at': t.published_at.isoformat() if t.published_at else None,
            'created_at': t.created_at.isoformat() if t.created_at else None,
        }

    @classmethod
    def _snapshot_participants(cls, tournament: Tournament) -> List[Dict[str, Any]]:
        try:
            from apps.tournaments.models.registration import Registration

            regs = Registration.objects.filter(
                tournament=tournament, is_deleted=False,
            ).select_related('user', 'team').order_by('created_at')

            return [
                {
                    'id': r.id,
                    'type': 'team' if r.team_id else 'solo',
                    'user_id': r.user_id,
                    'username': r.user.username if r.user else None,
                    'team_id': r.team_id,
                    'team_name': r.team.name if r.team else None,
                    'status': r.status,
                    'registered_at': r.created_at.isoformat() if r.created_at else None,
                    'seed': getattr(r, 'seed', None),
                }
                for r in regs
            ]
        except Exception as e:
            logger.warning("[archive] Participants snapshot failed: %s", e)
            return []

    @classmethod
    def _snapshot_matches(cls, tournament: Tournament) -> List[Dict[str, Any]]:
        try:
            from apps.tournaments.models.match import Match

            matches = Match.objects.filter(
                tournament=tournament, is_deleted=False,
            ).order_by('round_number', 'match_number')

            return [
                {
                    'id': m.id,
                    'round': m.round_number,
                    'match_number': m.match_number,
                    'state': m.state,
                    'team1_id': m.team1_id,
                    'team2_id': m.team2_id,
                    'team1_score': m.team1_score,
                    'team2_score': m.team2_score,
                    'winner_id': m.winner_id,
                    'bracket_id': m.bracket_id,
                    'scheduled_at': m.scheduled_at.isoformat() if hasattr(m, 'scheduled_at') and m.scheduled_at else None,
                    'completed_at': m.completed_at.isoformat() if hasattr(m, 'completed_at') and m.completed_at else None,
                }
                for m in matches
            ]
        except Exception as e:
            logger.warning("[archive] Matches snapshot failed: %s", e)
            return []

    @classmethod
    def _snapshot_brackets(cls, tournament: Tournament) -> List[Dict[str, Any]]:
        try:
            from apps.tournaments.models.bracket import Bracket

            brackets = Bracket.objects.filter(
                tournament=tournament, is_deleted=False,
            )

            return [
                {
                    'id': b.id,
                    'format': b.format,
                    'participant_count': b.participant_count,
                    'rounds_count': getattr(b, 'rounds_count', None),
                    'created_at': b.created_at.isoformat() if b.created_at else None,
                }
                for b in brackets
            ]
        except Exception as e:
            logger.warning("[archive] Brackets snapshot failed: %s", e)
            return []

    @classmethod
    def _snapshot_standings(cls, tournament: Tournament) -> List[Dict[str, Any]]:
        try:
            from apps.tournaments.models.result import TournamentResult

            results = TournamentResult.objects.filter(
                tournament=tournament,
            ).order_by('placement')

            return [
                {
                    'placement': r.placement,
                    'participant_id': r.registration_id if hasattr(r, 'registration_id') else None,
                    'team_id': r.team_id if hasattr(r, 'team_id') else None,
                    'name': getattr(r, 'participant_name', str(r)),
                    'prize_amount': str(r.prize_amount) if hasattr(r, 'prize_amount') and r.prize_amount else None,
                }
                for r in results
            ]
        except Exception as e:
            logger.warning("[archive] Standings snapshot failed: %s", e)
            return []

    @classmethod
    def _snapshot_prizes(cls, tournament: Tournament) -> List[Dict[str, Any]]:
        try:
            from apps.tournaments.models.prize import Prize

            prizes = Prize.objects.filter(tournament=tournament).order_by('placement')

            return [
                {
                    'placement': p.placement,
                    'amount': str(p.amount) if hasattr(p, 'amount') else None,
                    'label': getattr(p, 'label', None),
                    'currency': getattr(p, 'currency', None),
                }
                for p in prizes
            ]
        except Exception as e:
            logger.warning("[archive] Prizes snapshot failed: %s", e)
            return []

    @classmethod
    def _snapshot_groups(cls, tournament: Tournament) -> List[Dict[str, Any]]:
        try:
            from apps.tournaments.models.group import Group

            groups = Group.objects.filter(
                tournament=tournament, is_deleted=False,
            ).order_by('name')

            return [
                {
                    'id': g.id,
                    'name': g.name,
                    'standings': g.standings if hasattr(g, 'standings') else None,
                }
                for g in groups
            ]
        except Exception as e:
            logger.warning("[archive] Groups snapshot failed: %s", e)
            return []

    @classmethod
    def _snapshot_statistics(cls, tournament: Tournament) -> Dict[str, Any]:
        """Aggregate high-level statistics."""
        try:
            from apps.tournaments.models.match import Match
            from apps.tournaments.models.registration import Registration

            total_matches = Match.objects.filter(tournament=tournament, is_deleted=False).count()
            completed_matches = Match.objects.filter(
                tournament=tournament, state='completed', is_deleted=False,
            ).count()
            total_participants = Registration.objects.filter(
                tournament=tournament, status='confirmed', is_deleted=False,
            ).count()

            return {
                'total_participants': total_participants,
                'total_matches': total_matches,
                'completed_matches': completed_matches,
                'completion_rate': round(completed_matches / total_matches * 100, 1) if total_matches else 0,
                'duration_hours': cls._calc_duration(tournament),
            }
        except Exception as e:
            logger.warning("[archive] Statistics snapshot failed: %s", e)
            return {}

    @staticmethod
    def _calc_duration(tournament: Tournament) -> Optional[float]:
        if tournament.tournament_start and tournament.tournament_end:
            delta = tournament.tournament_end - tournament.tournament_start
            return round(delta.total_seconds() / 3600, 1)
        return None
