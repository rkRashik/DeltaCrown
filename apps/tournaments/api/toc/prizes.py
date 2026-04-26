"""
TOC API - Prize Tab views.

Backs the modern Prizes & Awards tab:

  GET  /api/toc/<slug>/prizes/
  POST /api/toc/<slug>/prizes/save/
  POST /api/toc/<slug>/prizes/publish/
  POST /api/toc/<slug>/prizes/claims/<claim_id>/action/
"""

from __future__ import annotations

import logging

from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.cache_utils import bump_toc_scopes
from apps.tournaments.models import PrizeClaim, Registration, TournamentResult
from apps.tournaments.services.bracket_service import BracketService
from apps.tournaments.services.placement_service import PlacementService
from apps.tournaments.services.prize_config_service import PrizeConfigService
from apps.tournaments.services.rewards_read_model import TournamentRewardsReadModel
from apps.tournaments.services.staff_permission_checker import StaffPermissionChecker

logger = logging.getLogger(__name__)


def _has_any(tournament, user, codes):
    return StaffPermissionChecker(tournament, user).has_any(codes)


def _invalidate_rewards_cache(tournament):
    cache.delete(f'public_prize_overview_v1_{tournament.id}')
    cache.delete(f'public_prize_overview_v2_{tournament.id}')


def _registration_label(registration):
    team = getattr(registration, 'team', None)
    if team and getattr(team, 'name', None):
        return str(team.name)
    user = getattr(registration, 'user', None)
    if user:
        return getattr(user, 'username', '') or getattr(user, 'email', '') or f'User #{user.pk}'
    return f'Registration #{registration.pk}'


def _registration_subtitle(registration):
    parts = []
    if getattr(registration, 'status', None):
        parts.append(str(registration.status).replace('_', ' ').title())
    team = getattr(registration, 'team', None)
    user = getattr(registration, 'user', None)
    if team and getattr(team, 'tag', None):
        parts.append(str(team.tag))
    if user and getattr(user, 'email', None):
        parts.append(str(user.email))
    return ' · '.join(parts)


class PrizeConfigView(TOCBaseView):
    """GET /api/toc/<slug>/prizes/ - config, public preview, operations."""

    def get(self, request, slug):
        payload = TournamentRewardsReadModel.toc_payload(
            self.tournament,
            user=request.user,
        )
        response = Response(payload)
        if payload.get('operations', {}).get('status', {}).get('completed'):
            _invalidate_rewards_cache(self.tournament)
            response['Cache-Control'] = 'no-store, max-age=0'
        return response


class PrizeConfigSaveView(TOCBaseView):
    """POST /api/toc/<slug>/prizes/save/ - persist prize configuration."""

    def post(self, request, slug):
        if not _has_any(self.tournament, request.user, ['full_access', 'edit_settings']):
            return Response(
                {'error': 'You do not have permission to edit prize settings.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            saved = PrizeConfigService.save_config(
                self.tournament,
                request.data or {},
                actor=request.user,
            )
        except (TypeError, ValueError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        bump_toc_scopes(self.tournament.id, 'overview', 'analytics', 'prizes')
        _invalidate_rewards_cache(self.tournament)
        payload = TournamentRewardsReadModel.toc_payload(
            self.tournament,
            user=request.user,
        )
        payload.update({'config': saved, 'status': 'saved'})
        return Response(payload)


class PrizePublishView(TOCBaseView):
    """
    POST /api/toc/<slug>/prizes/publish/

    Re-derive placements and persist them onto TournamentResult. Idempotent.
    """

    def post(self, request, slug):
        if not _has_any(
            self.tournament,
            request.user,
            ['full_access', 'edit_settings', 'manage_brackets'],
        ):
            return Response(
                {'error': 'You do not have permission to publish placements.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            PlacementService.persist_standings(self.tournament, actor=request.user)
        except Exception as e:
            logger.exception('Prize publish failed for %s', slug)
            return Response(
                {'error': str(e), 'status': 'failed'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bump_toc_scopes(self.tournament.id, 'overview', 'analytics', 'standings', 'prizes')
        _invalidate_rewards_cache(self.tournament)
        payload = TournamentRewardsReadModel.toc_payload(
            self.tournament,
            user=request.user,
        )
        payload['status'] = 'published'
        return Response(payload)


class PrizeClaimActionView(TOCBaseView):
    """
    POST /api/toc/<slug>/prizes/claims/<claim_id>/action/

    Supports the claim lifecycle the current models actually have:
    review/approve -> processing, reject -> rejected, mark_paid -> paid.
    No automated payout is faked here; mark_paid records manual payout state.
    """

    def post(self, request, slug, claim_id):
        if not _has_any(self.tournament, request.user, ['full_access', 'approve_payments']):
            return Response(
                {'error': 'You do not have permission to manage prize claims.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        claim = (
            PrizeClaim.objects
            .select_related('prize_transaction', 'prize_transaction__tournament')
            .filter(
                id=claim_id,
                prize_transaction__tournament=self.tournament,
            )
            .first()
        )
        if not claim:
            return Response(
                {'error': 'Prize claim not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        action = str((request.data or {}).get('action') or '').strip().lower()
        notes = str((request.data or {}).get('notes') or '').strip()[:1000]

        if action in {'review', 'approve'}:
            claim.status = PrizeClaim.STATUS_PROCESSING
        elif action == 'reject':
            claim.status = PrizeClaim.STATUS_REJECTED
        elif action == 'mark_paid':
            claim.status = PrizeClaim.STATUS_PAID
            claim.paid_at = timezone.now()
        else:
            return Response(
                {'error': 'Action must be review, approve, reject, or mark_paid.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if notes:
            existing = (claim.admin_notes or '').strip()
            claim.admin_notes = f'{existing}\n{notes}'.strip() if existing else notes
        claim.save(update_fields=['status', 'paid_at', 'admin_notes', 'updated_at'])

        bump_toc_scopes(self.tournament.id, 'overview', 'analytics', 'standings', 'prizes')
        _invalidate_rewards_cache(self.tournament)
        payload = TournamentRewardsReadModel.toc_payload(
            self.tournament,
            user=request.user,
        )
        payload['status'] = 'claim_updated'
        return Response(payload)


class PrizeRecipientSearchView(TOCBaseView):
    """GET /api/toc/<slug>/prizes/recipients/?q= - participant picker."""

    def get(self, request, slug):
        query = str(request.GET.get('q') or '').strip()
        qs = (
            Registration.objects
            .filter(tournament=self.tournament, is_deleted=False)
            .select_related('user', 'team')
            .order_by('id')
        )
        if query:
            qs = qs.filter(
                Q(user__username__icontains=query) |
                Q(user__email__icontains=query) |
                Q(team__name__icontains=query) |
                Q(team__tag__icontains=query)
            )
        results = []
        for reg in qs[:30]:
            results.append({
                'registration_id': reg.id,
                'name': _registration_label(reg),
                'subtitle': _registration_subtitle(reg),
                'status': reg.status,
                'team_id': getattr(reg, 'team_id', None),
                'user_id': getattr(reg, 'user_id', None),
            })
        return Response({'results': results})


class PrizePlacementAssignView(TOCBaseView):
    """POST /api/toc/<slug>/prizes/placements/assign/ - manual placement override."""

    def post(self, request, slug):
        if not _has_any(
            self.tournament,
            request.user,
            ['full_access', 'edit_settings', 'manage_brackets'],
        ):
            return Response(
                {'error': 'You do not have permission to assign placements.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        rank = int((request.data or {}).get('rank') or 0)
        recipient_id = int((request.data or {}).get('recipient_id') or 0)
        if rank not in {1, 2, 3, 4}:
            return Response({'error': 'Rank must be 1, 2, 3, or 4.'}, status=status.HTTP_400_BAD_REQUEST)
        recipient = (
            Registration.objects
            .filter(tournament=self.tournament, is_deleted=False, id=recipient_id)
            .select_related('user', 'team')
            .first()
        )
        if not recipient:
            return Response({'error': 'Recipient is not registered in this tournament.'}, status=status.HTTP_400_BAD_REQUEST)

        payload = PlacementService.standings_payload(self.tournament)
        standings = list(payload.get('standings') or [])
        standings = [row for row in standings if int(row.get('placement') or 0) != rank]
        standings.append({
            'placement': rank,
            'registration_id': recipient.id,
            'team_name': _registration_label(recipient),
            'source': 'manual_assignment',
            'is_tied': False,
            'tied_with': [],
        })
        standings.sort(key=lambda row: int(row.get('placement') or 0))

        winner_id = next((r.get('registration_id') for r in standings if int(r.get('placement') or 0) == 1), None)
        if not winner_id:
            return Response(
                {'error': 'Champion must exist before manual placement assignment.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result, _ = TournamentResult.objects.get_or_create(
            tournament=self.tournament,
            defaults={
                'winner_id': winner_id,
                'determination_method': 'manual',
                'created_by': request.user,
                'rules_applied': {
                    'source': 'manual_prize_assignment',
                    'assigned_rank': rank,
                },
            },
        )
        field_by_rank = {
            1: 'winner_id',
            2: 'runner_up_id',
            3: 'third_place_id',
            4: 'fourth_place_id',
        }
        setattr(result, field_by_rank[rank], recipient.id)
        for required_rank, field_name in ((1, 'winner_id'), (2, 'runner_up_id')):
            if not getattr(result, field_name):
                value = next((
                    row.get('registration_id')
                    for row in standings
                    if int(row.get('placement') or 0) == required_rank
                ), None)
                if value:
                    setattr(result, field_name, value)
        result.final_standings = standings
        result.determination_method = 'manual'
        rules = dict(result.rules_applied or {})
        rules.setdefault('manual_assignments', [])
        rules['manual_assignments'].append({
            'rank': rank,
            'registration_id': recipient.id,
            'recipient_name': _registration_label(recipient),
            'assigned_by_id': getattr(request.user, 'id', None),
            'assigned_at': timezone.now().isoformat(),
        })
        result.rules_applied = rules
        result.is_override = True
        result.save(update_fields=[
            'winner_id',
            'runner_up_id',
            'third_place_id',
            'fourth_place_id',
            'final_standings',
            'determination_method',
            'rules_applied',
            'is_override',
            'updated_at',
        ])

        bump_toc_scopes(self.tournament.id, 'overview', 'analytics', 'standings', 'prizes')
        _invalidate_rewards_cache(self.tournament)
        payload = TournamentRewardsReadModel.toc_payload(
            self.tournament,
            user=request.user,
        )
        payload['status'] = 'placement_assigned'
        return Response(payload)


class PrizeBronzeCreateView(TOCBaseView):
    """POST /api/toc/<slug>/prizes/bronze/create/ - organizer repair shortcut."""

    def post(self, request, slug):
        if not _has_any(
            self.tournament,
            request.user,
            ['full_access', 'edit_settings', 'manage_brackets'],
        ):
            return Response(
                {'error': 'You do not have permission to create a bronze match.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            match = BracketService.create_bronze_match_from_semifinal_losers(
                self.tournament.id,
                actor=request.user,
            )
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        bump_toc_scopes(self.tournament.id, 'brackets', 'matches', 'overview', 'analytics', 'standings', 'prizes')
        _invalidate_rewards_cache(self.tournament)
        payload = TournamentRewardsReadModel.toc_payload(
            self.tournament,
            user=request.user,
        )
        payload['status'] = 'bronze_created'
        payload['bronze_match'] = {
            'id': match.id,
            'participant1_name': match.participant1_name,
            'participant2_name': match.participant2_name,
            'state': match.state,
        }
        return Response(payload, status=status.HTTP_201_CREATED)
