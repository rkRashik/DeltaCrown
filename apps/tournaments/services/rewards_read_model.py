"""
Shared tournament results/rewards read model.

This service is intentionally read-side only. It combines the canonical final
standings from PlacementService/TournamentResult with prize configuration,
claim/payout records, and certificate records, then trims the payload by
surface so public, HUB, and TOC views do not drift.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from django.db import IntegrityError

from apps.tournaments.models import (
    Certificate,
    PrizeClaim,
    PrizeTransaction,
    Match,
    BracketNode,
    Registration,
    Tournament,
    TournamentResult,
)
from apps.tournaments.services.completion_truth import (
    get_tournament_completion_payload,
    is_tournament_effectively_completed,
)
from apps.tournaments.services.placement_service import PlacementService
from apps.tournaments.services.participant_identity import ParticipantIdentityService
from apps.tournaments.services.prize_config_service import PrizeConfigService, _ordinal
from apps.tournaments.services.staff_permission_checker import StaffPermissionChecker


class TournamentRewardsReadModel:
    """Build surface-specific results/rewards payloads for one tournament."""

    NO_BRONZE_REASON = 'No Third Place Match configured, 3rd place cannot be assigned.'

    RANK_TO_TRANSACTION_PLACEMENT = {
        1: PrizeTransaction.Placement.FIRST,
        2: PrizeTransaction.Placement.SECOND,
        3: PrizeTransaction.Placement.THIRD,
    }

    RANK_TO_CERTIFICATE_TYPE = {
        1: Certificate.WINNER,
        2: Certificate.RUNNER_UP,
        3: Certificate.THIRD_PLACE,
    }

    ACHIEVEMENT_BY_RANK = {
        1: ('Champion', 'crown'),
        2: ('Runner-up', 'medal'),
        3: ('Third place', 'award'),
        4: ('Fourth place', 'shield-check'),
    }

    @classmethod
    def public_payload(cls, tournament: Tournament) -> Dict[str, Any]:
        """Safe spectator payload. No claims, payout destinations, or admin notes."""
        ctx = cls._build_context(tournament)
        return cls._public_from_context(ctx)

    @classmethod
    def hub_payload(
        cls,
        tournament: Tournament,
        *,
        user=None,
        registration: Optional[Registration] = None,
    ) -> Dict[str, Any]:
        """Participant payload with current viewer claim/payout/certificate state."""
        ctx = cls._build_context(tournament, ensure_transactions=True)
        payload = cls._public_from_context(ctx)
        payload['surface'] = 'hub'
        payload['viewer'] = cls._viewer_payload(registration)
        payload['your_result'] = cls._your_result(ctx, registration)
        payload['your_prizes'] = cls._your_prizes(ctx, registration)
        payload['certificate'] = cls._certificate_payload(
            ctx['certificates_by_participant'].get(registration.id)
            if registration else None,
            include_private=False,
        )
        payload['claim_actions_locked'] = False

        # Legacy HubEngine compatibility keys.
        payload['prize_pool'] = {
            'total': str(ctx['fiat_pool']),
            'currency': ctx['currency'],
            'distribution': getattr(tournament, 'prize_distribution', None) or {},
            'deltacoin': ctx['coin_pool'],
        }
        payload['overview'] = cls._transaction_overview(ctx['transactions'])
        payload['tournament_status'] = ctx['result_status']['tournament_status']
        return payload

    @classmethod
    def toc_payload(cls, tournament: Tournament, *, user=None) -> Dict[str, Any]:
        """Organizer operations payload with claim/payout/certificate details."""
        ctx = cls._build_context(tournament, ensure_transactions=True)
        public_preview = cls._public_from_context(ctx)
        permissions = cls._toc_permissions(tournament, user)
        operations = cls._toc_operations(ctx, permissions)
        return {
            'surface': 'toc',
            'config': ctx['config'],
            'public_preview': public_preview,
            'operations': operations,
            'capabilities': permissions,
        }

    # ------------------------------------------------------------------
    # Context assembly
    # ------------------------------------------------------------------

    @classmethod
    def _build_context(
        cls,
        tournament: Tournament,
        *,
        ensure_transactions: bool = False,
    ) -> Dict[str, Any]:
        cfg = PrizeConfigService.get_config(tournament)
        completion_payload = get_tournament_completion_payload(tournament)
        effectively_completed = bool(
            completion_payload.get('completed') or
            is_tournament_effectively_completed(tournament)
        )
        standings_payload = PlacementService.standings_payload(tournament)
        result = (
            TournamentResult.objects
            .filter(tournament=tournament, is_deleted=False)
            .select_related(
                'winner',
                'winner__user',
                'runner_up',
                'runner_up__user',
                'third_place',
                'third_place__user',
                'fourth_place',
                'fourth_place__user',
            )
            .first()
        )

        standings = cls._normalise_standings(
            standings_payload.get('standings') or
            completion_payload.get('standings') or
            []
        )
        standings = PlacementService._sanitize_unresolved_single_elim_standings(
            tournament,
            standings,
        )

        # Read-only fallback: if post-finalization has produced a
        # TournamentResult but final_standings has not been persisted, expose
        # winner/runner/third/fourth from FK fields without mutating lifecycle
        # or placement state.
        if result and getattr(result, 'winner_id', None) and not standings:
            standings = cls._derive_standings_from_result(result)

        if standings:
            standings_payload = dict(standings_payload or {})
            standings_payload['standings'] = standings
            standings_payload['top4'] = standings[:4]
            standings_payload['finalized'] = bool(
                standings_payload.get('finalized') or
                completion_payload.get('finalized') or
                (result and getattr(result, 'winner_id', None))
            )
            if result and getattr(result, 'winner_id', None):
                standings_payload.setdefault('winner', cls._participant_snapshot(result.winner))
                standings_payload.setdefault('runner_up', cls._participant_snapshot(result.runner_up))
                standings_payload.setdefault('third_place', cls._participant_snapshot(result.third_place))
                standings_payload.setdefault('fourth_place', cls._participant_snapshot(result.fourth_place))

        tier_by_rank = {
            int(t.get('rank') or 0): t
            for t in (cfg.get('placements') or [])
            if isinstance(t, dict)
        }
        standings_by_rank = {
            int(s.get('placement') or 0): s
            for s in standings
            if isinstance(s, dict)
        }
        participant_identities = ParticipantIdentityService.for_registrations(
            tournament,
            [
                cls._int(s.get('registration_id'))
                for s in standings
                if isinstance(s, dict) and cls._int(s.get('registration_id'))
            ],
        )

        if ensure_transactions and effectively_completed:
            cls._ensure_prize_transactions(
                tournament,
                standings_by_rank,
                tier_by_rank,
            )

        transactions = list(
            PrizeTransaction.objects.filter(tournament=tournament)
            .select_related('participant', 'participant__user', 'claim')
            .order_by('placement', '-created_at', 'id')
        )
        certificates = list(
            Certificate.objects.filter(
                tournament=tournament,
                revoked_at__isnull=True,
            )
            .select_related('participant', 'participant__user')
            .order_by('-generated_at', '-id')
        )

        ctx = {
            'tournament': tournament,
            'config': cfg,
            'currency': cfg.get('currency') or 'BDT',
            'fiat_pool': cls._int(cfg.get('fiat_pool')),
            'coin_pool': cls._int(cfg.get('coin_pool')),
            'certificates_enabled': bool(cfg.get('certificates_enabled', True)),
            'completion_payload': completion_payload,
            'effectively_completed': effectively_completed,
            'standings_payload': standings_payload,
            'standings': standings,
            'standings_by_rank': standings_by_rank,
            'participant_identities': participant_identities,
            'tier_by_rank': tier_by_rank,
            'result': result,
            'placements_published': bool(result and (result.final_standings or [])),
            'transactions': transactions,
            'transactions_by_participant': cls._transactions_by_participant(transactions),
            'transactions_by_participant_placement': cls._transactions_by_participant_placement(transactions),
            'certificates_by_participant': cls._certificates_by_participant(certificates),
        }
        ctx['placements'] = cls._placement_rows(ctx)
        ctx['standings_rows'] = cls._standing_rows(ctx)
        ctx['result_status'] = cls._result_status(ctx)
        ctx['special_awards_public'] = cls._special_awards(
            tournament,
            cfg.get('special_awards') or [],
            include_internal=False,
        )
        ctx['special_awards_toc'] = cls._special_awards(
            tournament,
            cfg.get('special_awards') or [],
            include_internal=True,
        )
        ctx['derived_achievements_public'] = cls._derived_achievements(
            ctx,
            include_internal=False,
        )
        ctx['derived_achievements_toc'] = cls._derived_achievements(
            ctx,
            include_internal=True,
        )
        ctx['achievement_cards_public'] = (
            ctx['special_awards_public'] or ctx['derived_achievements_public']
        )
        ctx['achievement_cards_toc'] = (
            ctx['special_awards_toc'] or ctx['derived_achievements_toc']
        )
        return ctx

    @classmethod
    def _ensure_prize_transactions(
        cls,
        tournament: Tournament,
        standings_by_rank: Dict[int, Dict[str, Any]],
        tier_by_rank: Dict[int, Dict[str, Any]],
    ) -> None:
        """Create missing manual prize transactions for completed winners.

        This is intentionally idempotent and only creates the audit record that
        lets the winner submit a claim. It does not execute an automated payout.
        """
        for rank, placement in cls.RANK_TO_TRANSACTION_PLACEMENT.items():
            standing = standings_by_rank.get(rank) or {}
            registration_id = cls._int(standing.get('registration_id'))
            if not registration_id:
                continue
            tier = tier_by_rank.get(rank) or {}
            fiat = cls._int(tier.get('fiat'))
            coins = cls._int(tier.get('coins'))
            if not (fiat or coins):
                continue
            amount = Decimal(str(coins or fiat or 0))
            notes = (
                'Manual payout required. Created from Results & Rewards read model. '
                f'Configured reward: fiat={fiat}, coins={coins}.'
            )
            try:
                tx, created = PrizeTransaction.objects.get_or_create(
                    tournament=tournament,
                    participant_id=registration_id,
                    placement=placement,
                    defaults={
                        'amount': amount,
                        'status': PrizeTransaction.Status.PENDING,
                        'notes': notes,
                    },
                )
            except IntegrityError:
                tx = PrizeTransaction.objects.filter(
                    tournament=tournament,
                    participant_id=registration_id,
                    placement=placement,
                ).first()
                created = False
            if not tx or created:
                continue
            if tx.status == PrizeTransaction.Status.PENDING and (
                tx.amount != amount or 'Manual payout required' not in (tx.notes or '')
            ):
                tx.amount = amount
                if 'Manual payout required' not in (tx.notes or ''):
                    tx.notes = f'{tx.notes}\n{notes}'.strip() if tx.notes else notes
                tx.save(update_fields=['amount', 'notes', 'updated_at'])

    @classmethod
    def _placement_rows(cls, ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows = []
        for tier in ctx['config'].get('placements') or []:
            if not isinstance(tier, dict):
                continue
            rank = cls._int(tier.get('rank'))
            standing = ctx['standings_by_rank'].get(rank)
            participant_id = cls._int(standing.get('registration_id')) if standing else None
            identity = ctx.get('participant_identities', {}).get(participant_id) or {}
            display_name = (
                (standing.get('team_name') if standing else '')
                or identity.get('name')
                or ''
            )
            image_url = identity.get('image_url') or identity.get('logo_url') or identity.get('avatar_url') or ''
            certificate = ctx['certificates_by_participant'].get(participant_id)
            rows.append({
                'rank': rank,
                'rank_label': _ordinal(rank) if rank else '',
                'title': tier.get('title') or (_ordinal(rank) if rank else ''),
                'percent': cls._int(tier.get('percent')),
                'fiat': cls._int(tier.get('fiat')),
                'coins': cls._int(tier.get('coins')),
                'winner': {
                    'registration_id': participant_id,
                    'team_name': display_name,
                    'name': display_name,
                    'image_url': image_url,
                    'logo_url': identity.get('logo_url') or image_url,
                    'avatar_url': identity.get('avatar_url') or image_url,
                } if standing else None,
                'image_url': image_url,
                'logo_url': identity.get('logo_url') or image_url,
                'avatar_url': identity.get('avatar_url') or image_url,
                **cls._placement_resolution(ctx, rank, standing),
                'certificate_badge': cls._certificate_badge(
                    certificate,
                    enabled=ctx['certificates_enabled'],
                    has_recipient=bool(participant_id),
                ),
            })
        return rows

    @classmethod
    def _standing_rows(cls, ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows = []
        for standing in ctx['standings']:
            rank = cls._int(standing.get('placement'))
            participant_id = cls._int(standing.get('registration_id'))
            tier = ctx['tier_by_rank'].get(rank) or {}
            certificate = ctx['certificates_by_participant'].get(participant_id)
            identity = ctx.get('participant_identities', {}).get(participant_id) or {}
            display_name = standing.get('team_name') or identity.get('name') or ''
            image_url = identity.get('image_url') or identity.get('logo_url') or identity.get('avatar_url') or ''
            rows.append({
                'rank': rank,
                'rank_label': _ordinal(rank) if rank else '',
                'title': tier.get('title') or (_ordinal(rank) if rank else ''),
                'registration_id': participant_id,
                'team_name': display_name,
                'result_label': display_name,
                'image_url': image_url,
                'logo_url': identity.get('logo_url') or image_url,
                'avatar_url': identity.get('avatar_url') or image_url,
                'placement_unresolved': False,
                'payout_blocked': False,
                'block_reason': '',
                'source': standing.get('source') or '',
                'is_tied': bool(standing.get('is_tied')),
                'prize': cls._prize_from_tier(tier, ctx['currency']),
                'certificate_badge': cls._certificate_badge(
                    certificate,
                    enabled=ctx['certificates_enabled'],
                    has_recipient=bool(participant_id),
                ),
            })
        return rows

    @classmethod
    def _public_from_context(cls, ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'surface': 'public',
            'currency': ctx['currency'],
            'fiat_pool': ctx['fiat_pool'],
            'coin_pool': ctx['coin_pool'],
            'placements': cls._surface_placements(ctx, include_registration_ids=False),
            'standings': cls._surface_standings(ctx, include_registration_ids=False),
            'podium': cls._surface_standings(ctx, include_registration_ids=False)[:3],
            'special_awards': ctx['special_awards_public'],
            'achievements': ctx['achievement_cards_public'],
            'derived_achievements': ctx['derived_achievements_public'],
            'certificates_enabled': ctx['certificates_enabled'],
            'finalized': bool(ctx['result_status']['finalized']),
            'placements_published': ctx['placements_published'],
            'top4': cls._strip_registration_ids(ctx['standings_payload'].get('top4') or []),
            'requires_review': bool(ctx['standings_payload'].get('requires_review')),
            'result_status': ctx['result_status'],
            'empty_states': cls._empty_states(ctx),
        }

    # ------------------------------------------------------------------
    # HUB
    # ------------------------------------------------------------------

    @classmethod
    def _viewer_payload(cls, registration: Optional[Registration]) -> Optional[Dict[str, Any]]:
        if not registration:
            return None
        identity = ParticipantIdentityService.for_registrations(
            registration.tournament,
            {registration.id},
        ).get(int(registration.id), {})
        image_url = identity.get('image_url') or identity.get('logo_url') or identity.get('avatar_url') or ''
        return {
            'registration_id': registration.id,
            'team_name': identity.get('name') or cls._registration_label(registration),
            'image_url': image_url,
            'logo_url': identity.get('logo_url') or image_url,
            'avatar_url': identity.get('avatar_url') or image_url,
        }

    @classmethod
    def _your_result(
        cls,
        ctx: Dict[str, Any],
        registration: Optional[Registration],
    ) -> Optional[Dict[str, Any]]:
        if not registration:
            return None
        for row in ctx['standings_rows']:
            if row.get('registration_id') == registration.id:
                transaction = cls._transaction_for_rank(ctx, registration.id, row.get('rank'))
                claim = getattr(transaction, 'claim', None) if transaction else None
                out = dict(row)
                out['has_prize'] = bool(
                    row.get('prize', {}).get('fiat') or
                    row.get('prize', {}).get('coins') or
                    transaction
                )
                out['claim'] = cls._claim_payload(claim, include_private=False)
                out['payout'] = cls._payout_payload(transaction, claim, include_private=False)
                out['certificate'] = cls._certificate_payload(
                    ctx['certificates_by_participant'].get(registration.id),
                    include_private=False,
                )
                out['achievement_badges'] = cls._achievement_badges_for_registration(
                    ctx,
                    registration,
                    row.get('rank'),
                )
                out['claimable'] = bool(transaction and not claim and transaction.status in (
                    PrizeTransaction.Status.PENDING,
                    PrizeTransaction.Status.COMPLETED,
                ))
                return out
        return None

    @classmethod
    def _your_prizes(
        cls,
        ctx: Dict[str, Any],
        registration: Optional[Registration],
    ) -> List[Dict[str, Any]]:
        if not registration:
            return []
        transactions = ctx['transactions_by_participant'].get(registration.id) or []
        prizes = []
        for pt in transactions:
            claim = getattr(pt, 'claim', None)
            prizes.append({
                'id': pt.id,
                'placement': pt.placement,
                'placement_display': pt.get_placement_display(),
                'amount': str(pt.amount),
                'status': pt.status,
                'claimed': claim is not None,
                'claimable': bool(not claim and pt.status in (
                    PrizeTransaction.Status.PENDING,
                    PrizeTransaction.Status.COMPLETED,
                )),
                'claim_status': claim.status if claim else None,
                'claim': cls._claim_payload(claim, include_private=False),
                'payout': cls._payout_payload(pt, claim, include_private=False),
                'claim_payout_method': claim.payout_method if claim else None,
                'paid_at': claim.paid_at.isoformat() if claim and claim.paid_at else None,
                'certificate': cls._certificate_payload(
                    ctx['certificates_by_participant'].get(registration.id),
                    include_private=False,
                ),
            })

        if prizes:
            return prizes

        return []

    # ------------------------------------------------------------------
    # TOC
    # ------------------------------------------------------------------

    @classmethod
    def _toc_operations(
        cls,
        ctx: Dict[str, Any],
        permissions: Dict[str, bool],
    ) -> Dict[str, Any]:
        placements = []
        for row in ctx['standings_rows']:
            participant_id = row.get('registration_id')
            transaction = cls._transaction_for_rank(ctx, participant_id, row.get('rank'))
            claim = getattr(transaction, 'claim', None) if transaction else None
            merged = dict(row)
            merged['claim'] = cls._claim_payload(claim, include_private=True)
            merged['payout'] = cls._payout_payload(transaction, claim, include_private=True)
            merged['certificate'] = cls._certificate_payload(
                ctx['certificates_by_participant'].get(participant_id),
                include_private=True,
            )
            merged['contact'] = {
                'enabled': False,
                'label': 'Messaging integration pending',
            }
            claim_status = getattr(claim, 'status', '') if claim else ''
            claim_is_open = claim_status in {
                PrizeClaim.STATUS_PENDING,
                PrizeClaim.STATUS_PROCESSING,
            }
            merged['actions'] = {
                'can_review_claim': bool(
                    claim and permissions.get('can_manage_payouts') and claim_is_open
                ),
                'can_mark_paid': bool(
                    claim and permissions.get('can_manage_payouts') and claim_is_open
                ),
            }
            placements.append(merged)

        for row in ctx['placements']:
            if not row.get('placement_unresolved'):
                continue
            prize = cls._prize_from_tier(row, ctx['currency'])
            block_reason = row.get('block_reason') or cls.NO_BRONZE_REASON
            placements.append({
                'rank': row.get('rank'),
                'rank_label': row.get('rank_label'),
                'title': row.get('title') or '',
                'registration_id': None,
                'team_name': row.get('result_label') or '',
                'result_label': row.get('result_label') or '',
                'placement_unresolved': True,
                'payout_blocked': True,
                'block_reason': block_reason,
                'source': 'unresolved_no_bronze',
                'is_tied': bool(row.get('is_tied')),
                'prize': prize,
                'certificate_badge': row.get('certificate_badge') or {},
                'claim': None,
                'payout': {
                    'status': 'blocked',
                    'label': block_reason,
                },
                'certificate': None,
                'contact': {
                    'enabled': False,
                    'label': 'Placement unresolved',
                },
                'actions': {
                    'can_review_claim': False,
                    'can_mark_paid': False,
                },
            })

        claim_queue = [
            item for item in placements
            if item.get('claim') and item['claim'].get('status') != PrizeClaim.STATUS_PAID
        ]

        return {
            'status': ctx['result_status'],
            'placements': placements,
            'claim_queue': claim_queue,
            'special_awards': ctx['special_awards_toc'],
            'achievements': ctx['achievement_cards_toc'],
            'derived_achievements': ctx['derived_achievements_toc'],
            'certificates_enabled': ctx['certificates_enabled'],
            'messaging': {
                'enabled': False,
                'reason': 'No direct recipient messaging endpoint is wired for prize operations yet.',
            },
            'empty_states': cls._empty_states(ctx),
        }

    @classmethod
    def _toc_permissions(cls, tournament: Tournament, user=None) -> Dict[str, bool]:
        if not user or not getattr(user, 'is_authenticated', False):
            return {
                'can_edit_prizes': False,
                'can_publish_placements': False,
                'can_manage_payouts': False,
            }
        checker = StaffPermissionChecker(tournament, user)
        return {
            'can_edit_prizes': checker.has_any(['full_access', 'edit_settings']),
            'can_publish_placements': checker.has_any([
                'full_access',
                'edit_settings',
                'manage_brackets',
            ]),
            'can_manage_payouts': checker.has_any(['full_access', 'approve_payments']),
        }

    # ------------------------------------------------------------------
    # Serializers/helpers
    # ------------------------------------------------------------------

    @classmethod
    def _participant_snapshot(
        cls,
        registration: Optional[Registration],
    ) -> Optional[Dict[str, Any]]:
        if not registration:
            return None
        identity = ParticipantIdentityService.for_registrations(
            registration.tournament,
            {registration.pk},
        ).get(int(registration.pk), {})
        image_url = identity.get('image_url') or identity.get('logo_url') or identity.get('avatar_url') or ''
        return {
            'registration_id': cls._int(getattr(registration, 'pk', None)),
            'team_name': identity.get('name') or cls._registration_label(registration),
            'image_url': image_url,
            'logo_url': identity.get('logo_url') or image_url,
            'avatar_url': identity.get('avatar_url') or image_url,
        }

    @classmethod
    def _surface_placements(
        cls,
        ctx: Dict[str, Any],
        *,
        include_registration_ids: bool,
    ) -> List[Dict[str, Any]]:
        rows = []
        for tier in ctx['placements']:
            row = dict(tier)
            winner = row.get('winner')
            if isinstance(winner, dict):
                winner = dict(winner)
                if not include_registration_ids:
                    winner.pop('registration_id', None)
                row['winner'] = winner
            rows.append(row)
        return rows

    @classmethod
    def _surface_standings(
        cls,
        ctx: Dict[str, Any],
        *,
        include_registration_ids: bool,
    ) -> List[Dict[str, Any]]:
        rows = []
        for standing in ctx['standings_rows']:
            row = dict(standing)
            if not include_registration_ids:
                row.pop('registration_id', None)
            rows.append(row)
        return rows

    @classmethod
    def _strip_registration_ids(
        cls,
        rows: Iterable[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        out = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            clean = dict(row)
            clean.pop('registration_id', None)
            out.append(clean)
        return out

    @classmethod
    def _derived_achievements(
        cls,
        ctx: Dict[str, Any],
        *,
        include_internal: bool,
    ) -> List[Dict[str, Any]]:
        achievements = []
        for row in ctx['standings_rows']:
            rank = cls._int(row.get('rank'))
            if rank not in cls.ACHIEVEMENT_BY_RANK:
                continue
            title, icon = cls.ACHIEVEMENT_BY_RANK[rank]
            recipient_name = row.get('team_name') or ''
            if not recipient_name:
                continue
            image_url = row.get('image_url') or row.get('logo_url') or row.get('avatar_url') or ''
            achievement = {
                'id': f'placement-{rank}',
                'title': title,
                'description': f'{row.get("rank_label") or _ordinal(rank)} in the final standings',
                'type': 'placement',
                'icon': icon,
                'rank': rank,
                'source': 'placement',
                'recipient_name': recipient_name,
                'image_url': image_url,
                'logo_url': row.get('logo_url') or image_url,
                'avatar_url': row.get('avatar_url') or image_url,
                'reward_text': cls._achievement_reward_text(row.get('prize') or {}),
            }
            if include_internal:
                achievement['recipient_id'] = row.get('registration_id')
                achievement['contact'] = {
                    'enabled': False,
                    'label': 'Messaging integration pending',
                }
            achievements.append(achievement)
        return achievements

    @classmethod
    def _achievement_badges_for_registration(
        cls,
        ctx: Dict[str, Any],
        registration: Registration,
        rank: Optional[int],
    ) -> List[Dict[str, Any]]:
        badges = []
        rank = cls._int(rank)
        for achievement in ctx.get('derived_achievements_public') or []:
            if cls._int(achievement.get('rank')) == rank:
                badges.append({
                    'title': achievement.get('title') or '',
                    'icon': achievement.get('icon') or 'award',
                    'source': 'placement',
                })

        label = cls._registration_label(registration)
        for award in ctx.get('config', {}).get('special_awards') or []:
            if not isinstance(award, dict):
                continue
            recipient_id = cls._int(award.get('recipient_id'))
            recipient_name = award.get('recipient_name') or ''
            if recipient_id == registration.id or (
                recipient_name and label and recipient_name == label
            ):
                badges.append({
                    'title': award.get('title') or 'Special Award',
                    'icon': award.get('icon') or 'medal',
                    'source': 'special_award',
                })
        return badges

    @classmethod
    def _achievement_reward_text(cls, prize: Dict[str, Any]) -> str:
        parts = []
        fiat = cls._int(prize.get('fiat'))
        coins = cls._int(prize.get('coins'))
        currency = prize.get('currency') or 'BDT'
        if fiat:
            parts.append(f'{currency} {fiat:,}')
        if coins:
            parts.append(f'{coins:,} DC')
        return ' + '.join(parts)

    @classmethod
    def _derive_standings_from_result(
        cls,
        result: TournamentResult,
    ) -> List[Dict[str, Any]]:
        """
        Last-resort fallback used by ``_build_context`` when neither
        ``result.final_standings`` nor ``PlacementService.build_final_standings``
        produced any rows. Reads winner / runner_up / third_place / fourth_place
        FK fields directly so prize surfaces always show winner names when
        a TournamentResult exists.
        """
        out: List[Dict[str, Any]] = []
        for placement, attr_name, source in (
            (1, 'winner', 'final_winner'),
            (2, 'runner_up', 'final_loser'),
            (3, 'third_place', 'third_place'),
            (4, 'fourth_place', 'fourth_place'),
        ):
            registration = getattr(result, attr_name, None)
            if not registration:
                continue
            out.append({
                'placement': placement,
                'registration_id': cls._int(getattr(registration, 'pk', None)),
                'team_name': cls._registration_label(registration),
                'source': source,
                'is_tied': False,
                'tied_with': [],
            })
        return out

    @classmethod
    def _normalise_standings(cls, standings: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for row in standings:
            if not isinstance(row, dict):
                continue
            placement = cls._int(row.get('placement'))
            if placement <= 0:
                continue
            out.append({
                'placement': placement,
                'registration_id': cls._int(row.get('registration_id')),
                'team_name': row.get('team_name') or '',
                'source': row.get('source') or '',
                'is_tied': bool(row.get('is_tied')),
                'tied_with': row.get('tied_with') or [],
            })
        out.sort(key=lambda item: item['placement'])
        return out

    @classmethod
    def _result_status(cls, ctx: Dict[str, Any]) -> Dict[str, Any]:
        tournament = ctx['tournament']
        raw_effective_status = getattr(
            tournament,
            'get_effective_status',
            lambda: tournament.status,
        )()
        has_winner = bool(ctx['result'] and getattr(ctx['result'], 'winner_id', None))
        completed = bool(ctx.get('effectively_completed')) or raw_effective_status in (
            Tournament.COMPLETED,
            Tournament.ARCHIVED,
        ) or has_winner
        effective_status = raw_effective_status
        if completed and effective_status not in (
            Tournament.COMPLETED,
            Tournament.ARCHIVED,
        ):
            effective_status = Tournament.COMPLETED
        finalized = bool(ctx['standings_payload'].get('finalized') or has_winner)
        placements_published = bool(ctx['placements_published'])
        results_available = bool(ctx['standings_rows']) or has_winner
        if not completed:
            message = 'Tournament not completed yet.'
        elif not results_available:
            message = 'Tournament completed. Final result is not available yet.'
        elif cls._has_no_bronze_unresolved_placements(ctx):
            message = cls.NO_BRONZE_REASON
        elif not placements_published:
            message = 'Completed results are available. Publish placements to persist operations.'
        else:
            message = 'Results and rewards are finalized.'
        return {
            'tournament_status': effective_status,
            'completed': completed,
            'finalized': finalized,
            'results_available': results_available,
            'placements_published': placements_published,
            'requires_review': bool(ctx['standings_payload'].get('requires_review')),
            'placement_resolution': cls._placement_resolution_status(ctx),
            'message': message,
        }

    @classmethod
    def _empty_states(cls, ctx: Dict[str, Any]) -> Dict[str, bool]:
        has_paid_tier = any(
            cls._int(p.get('fiat')) or cls._int(p.get('coins'))
            for p in (ctx['config'].get('placements') or [])
            if isinstance(p, dict)
        )
        return {
            'no_prize_configured': not bool(
                ctx['fiat_pool'] or ctx['coin_pool'] or
                has_paid_tier or ctx['special_awards_public']
            ),
            'no_placements': not bool(ctx['standings_rows'] or ctx.get('placements')),
            'no_special_awards': not bool(ctx['special_awards_public']),
            'no_achievements': not bool(ctx.get('achievement_cards_public')),
            'not_completed': not bool(ctx['result_status']['completed']),
            'placements_not_published': bool(
                ctx['result_status']['finalized'] and not ctx['placements_published']
            ),
        }

    @classmethod
    def _special_awards(
        cls,
        tournament: Tournament,
        awards: Iterable[Dict[str, Any]],
        *,
        include_internal: bool,
    ) -> List[Dict[str, Any]]:
        out = []
        recipient_ids = [
            cls._int(award.get('recipient_id'))
            for award in awards
            if isinstance(award, dict) and cls._int(award.get('recipient_id'))
        ]
        recipients_by_id = ParticipantIdentityService.for_registrations(
            tournament,
            recipient_ids,
        )
        for award in awards:
            if not isinstance(award, dict):
                continue
            recipient_id = cls._int(award.get('recipient_id'))
            recipient_name = award.get('recipient_name') or ''
            resolved_recipient = recipients_by_id.get(recipient_id)
            if not recipient_name and recipient_id:
                recipient_name = (resolved_recipient or {}).get('name') or ''
            awaiting_recipient = not bool(recipient_name or resolved_recipient)
            image_url = (
                (resolved_recipient or {}).get('image_url')
                or (resolved_recipient or {}).get('logo_url')
                or (resolved_recipient or {}).get('avatar_url')
                or ''
            )
            row = {
                'id': award.get('id') or '',
                'title': award.get('title') or '',
                'description': award.get('description') or '',
                'type': award.get('type') or 'cash',
                'icon': award.get('icon') or 'medal',
                'fiat': cls._int(award.get('fiat')),
                'coins': cls._int(award.get('coins')),
                'reward_text': award.get('reward_text') or '',
                'recipient_name': recipient_name or 'Awaiting assignment',
                'image_url': image_url,
                'logo_url': (resolved_recipient or {}).get('logo_url') or image_url,
                'avatar_url': (resolved_recipient or {}).get('avatar_url') or image_url,
                'awaiting_recipient': awaiting_recipient,
            }
            if include_internal:
                row['recipient_id'] = recipient_id or None
                row['contact'] = {
                    'enabled': False,
                    'label': 'Messaging integration pending',
                }
            out.append(row)
        return out

    @classmethod
    def _prize_from_tier(cls, tier: Dict[str, Any], currency: str) -> Dict[str, Any]:
        return {
            'currency': currency,
            'fiat': cls._int(tier.get('fiat')) if tier else 0,
            'coins': cls._int(tier.get('coins')) if tier else 0,
            'percent': cls._int(tier.get('percent')) if tier else 0,
        }

    @classmethod
    def _placement_resolution(
        cls,
        ctx: Dict[str, Any],
        rank: int,
        standing: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if standing:
            participant_id = cls._int(standing.get('registration_id'))
            identity = ctx.get('participant_identities', {}).get(participant_id) or {}
            return {
                'result_label': standing.get('team_name') or identity.get('name') or '',
                'placement_unresolved': False,
                'payout_blocked': False,
                'block_reason': '',
                'is_tied': bool(standing.get('is_tied')),
            }
        if rank not in (3, 4) or not cls._single_elimination_context(ctx):
            return {
                'result_label': '',
                'placement_unresolved': False,
                'payout_blocked': False,
                'block_reason': '',
                'is_tied': False,
            }
        status = ctx.get('result_status') or {}
        completed = bool(ctx.get('effectively_completed')) or bool(status.get('completed'))
        if not completed:
            return {
                'result_label': '',
                'placement_unresolved': False,
                'payout_blocked': False,
                'block_reason': '',
                'is_tied': False,
            }
        third_place_match = cls._third_place_match(ctx)
        if third_place_match and getattr(third_place_match, 'winner_id', None):
            return {
                'result_label': '',
                'placement_unresolved': False,
                'payout_blocked': False,
                'block_reason': '',
                'is_tied': False,
            }
        label = cls._unresolved_placement_label(ctx)
        reason = (
            'Third Place Match is not completed yet.'
            if third_place_match
            else cls.NO_BRONZE_REASON
        )
        return {
            'result_label': label,
            'placement_unresolved': True,
            'payout_blocked': True,
            'block_reason': reason,
            'is_tied': label == 'Joint 3rd',
        }

    @classmethod
    def _single_elimination_context(cls, ctx: Dict[str, Any]) -> bool:
        tournament = ctx['tournament']
        fmt = (getattr(tournament, 'format', '') or '').replace('_', '-').lower()
        if fmt == 'single-elimination':
            return True
        try:
            bracket = tournament.bracket
        except Exception:
            bracket = None
        structure = getattr(bracket, 'bracket_structure', None) or {}
        return (structure.get('format') or '').replace('_', '-').lower() == 'single-elimination'

    @classmethod
    def _unresolved_placement_label(cls, ctx: Dict[str, Any]) -> str:
        cfg = getattr(ctx['tournament'], 'config', None) or {}
        policy = (
            cfg.get('third_place_policy') or
            cfg.get('placement_policy') or
            (cfg.get('bracket_settings') or {}).get('third_place_policy') or
            (cfg.get('knockout_config') or {}).get('third_place_policy') or
            ''
        )
        if str(policy).replace('-', '_').lower() in {'joint_3rd', 'joint_third', 'joint_third_place'}:
            return 'Joint 3rd'
        return 'Semi-finalist / placement unresolved'

    @classmethod
    def _has_no_bronze_unresolved_placements(cls, ctx: Dict[str, Any]) -> bool:
        return any(
            row.get('placement_unresolved')
            for row in ctx.get('placements') or []
        )

    @classmethod
    def _placement_resolution_status(cls, ctx: Dict[str, Any]) -> Dict[str, Any]:
        unresolved = cls._has_no_bronze_unresolved_placements(ctx)
        third_place_match = cls._third_place_match(ctx)
        third_place_match_exists = bool(third_place_match)
        third_place_match_completed = bool(
            third_place_match and
            getattr(third_place_match, 'state', '') in (Match.COMPLETED, Match.FORFEIT) and
            getattr(third_place_match, 'winner_id', None)
        )
        message = ''
        if unresolved:
            message = (
                'Third Place Match is not completed yet.'
                if third_place_match_exists
                else cls.NO_BRONZE_REASON
            )
        return {
            'third_place_assignable': not unresolved,
            'bronze_match_enabled': cls._bronze_match_enabled(ctx),
            'third_place_match_enabled': cls._bronze_match_enabled(ctx) or third_place_match_exists,
            'third_place_match_exists': third_place_match_exists,
            'third_place_match_completed': third_place_match_completed,
            'third_place_match_id': getattr(third_place_match, 'id', None) if third_place_match else None,
            'can_create_third_place_match': bool(unresolved and not third_place_match_exists),
            'payout_blocked_for_ranks': [3, 4] if unresolved else [],
            'message': message,
        }

    @classmethod
    def _bronze_match_enabled(cls, ctx: Dict[str, Any]) -> bool:
        cfg = getattr(ctx['tournament'], 'config', None) or {}
        for source in (
            cfg,
            cfg.get('bracket_settings') or {},
            cfg.get('knockout_config') or {},
        ):
            if source.get('third_place_match_enabled') is True:
                return True
            if source.get('bronze_match_enabled') is True:
                return True
        try:
            structure = (ctx['tournament'].bracket.bracket_structure or {})
        except Exception:
            structure = {}
        return bool(
            structure.get('third_place_match_enabled') is True or
            structure.get('bronze_match_enabled') is True
        )

    @classmethod
    def _third_place_match(cls, ctx: Dict[str, Any]) -> Optional[Match]:
        tournament = ctx['tournament']
        filters = {
            'tournament': tournament,
            'is_deleted': False,
        }
        try:
            bracket = tournament.bracket
        except Exception:
            bracket = None
        qs = Match.objects.filter(**filters)
        if bracket:
            qs = qs.filter(bracket=bracket)
        match = (
            qs.filter(bracket_node__bracket_type=BracketNode.THIRD_PLACE)
            .order_by('-round_number', 'match_number', '-id')
            .first()
        )
        if match:
            return match
        for candidate in qs.order_by('-round_number', 'match_number', '-id')[:20]:
            info = getattr(candidate, 'lobby_info', None) or {}
            if info.get('third_place_match') is True or info.get('stage') in {'third_place', 'bronze'}:
                return candidate
        return None

    @classmethod
    def _claim_payload(cls, claim: Optional[PrizeClaim], *, include_private: bool) -> Optional[Dict[str, Any]]:
        if not claim:
            return None
        out = {
            'id': claim.id,
            'status': claim.status,
            'payout_method': claim.payout_method,
            'claimed_at': claim.claimed_at.isoformat() if claim.claimed_at else None,
            'paid_at': claim.paid_at.isoformat() if claim.paid_at else None,
        }
        if include_private:
            out.update({
                'claimed_by_id': claim.claimed_by_id,
                'claimed_by': getattr(claim.claimed_by, 'username', '') if claim.claimed_by_id else '',
                'payout_destination': claim.payout_destination,
                'claim_details': claim.claim_details or {},
                'admin_notes': claim.admin_notes,
            })
        return out

    @classmethod
    def _payout_payload(
        cls,
        transaction: Optional[PrizeTransaction],
        claim: Optional[PrizeClaim],
        *,
        include_private: bool,
    ) -> Dict[str, Any]:
        claim_status = claim.status if claim else None
        status = claim_status or (transaction.status if transaction else 'not_started')
        if not transaction:
            label = 'No payout started'
            requires_manual = False
        elif claim and claim.status == PrizeClaim.STATUS_PAID:
            label = 'Paid'
            requires_manual = False
        elif claim and claim.status == PrizeClaim.STATUS_REJECTED:
            label = 'Rejected'
            requires_manual = False
        elif claim and claim.status == PrizeClaim.STATUS_PROCESSING:
            label = 'Manual payout required'
            requires_manual = True
        elif claim and claim.status == PrizeClaim.STATUS_PENDING:
            label = 'Claim pending review'
            requires_manual = True
        elif transaction.status == PrizeTransaction.Status.COMPLETED:
            label = 'Paid'
            requires_manual = False
        elif transaction.status == PrizeTransaction.Status.FAILED:
            label = 'Failed'
            requires_manual = False
        else:
            label = 'Manual payout required'
            requires_manual = True
        out = {
            'status': status,
            'label': label,
            'requires_manual_payout': requires_manual,
            'transaction_id': transaction.id if transaction else None,
            'amount': str(transaction.amount) if transaction else '0',
            'placement': transaction.placement if transaction else '',
        }
        if include_private:
            out.update({
                'coin_transaction_id': transaction.coin_transaction_id if transaction else None,
                'notes': transaction.notes if transaction else '',
                'processed_by_id': transaction.processed_by_id if transaction else None,
            })
        return out

    @classmethod
    def _certificate_payload(
        cls,
        certificate: Optional[Certificate],
        *,
        include_private: bool,
    ) -> Optional[Dict[str, Any]]:
        if not certificate:
            return None
        out = {
            'id': certificate.id,
            'status': 'revoked' if certificate.is_revoked else 'available',
            'type': certificate.certificate_type,
            'placement': certificate.placement,
            'download_url': f'/api/tournaments/certificates/{certificate.id}/?format=pdf',
            'verification_url': certificate.verification_url,
        }
        if include_private:
            out.update({
                'generated_at': certificate.generated_at.isoformat() if certificate.generated_at else None,
                'download_count': certificate.download_count,
                'downloaded_at': certificate.downloaded_at.isoformat() if certificate.downloaded_at else None,
            })
        return out

    @classmethod
    def _certificate_badge(
        cls,
        certificate: Optional[Certificate],
        *,
        enabled: bool,
        has_recipient: bool,
    ) -> Dict[str, Any]:
        if not enabled:
            return {'enabled': False, 'status': 'disabled'}
        if certificate:
            return {'enabled': True, 'status': 'available'}
        if has_recipient:
            return {'enabled': True, 'status': 'pending'}
        return {'enabled': True, 'status': 'awaiting_recipient'}

    @classmethod
    def _transaction_overview(cls, transactions: Iterable[PrizeTransaction]) -> List[Dict[str, Any]]:
        buckets: Dict[str, Dict[str, Any]] = {}
        for tx in transactions:
            row = buckets.setdefault(tx.placement, {
                'placement': tx.placement,
                'total': Decimal('0'),
                'count': 0,
            })
            row['total'] += tx.amount or Decimal('0')
            row['count'] += 1
        return [
            {
                'placement': placement,
                'total': str(row['total']),
                'count': row['count'],
            }
            for placement, row in sorted(buckets.items())
        ]

    @classmethod
    def _transactions_by_participant(
        cls,
        transactions: Iterable[PrizeTransaction],
    ) -> Dict[int, List[PrizeTransaction]]:
        out: Dict[int, List[PrizeTransaction]] = {}
        for tx in transactions:
            out.setdefault(tx.participant_id, []).append(tx)
        return out

    @classmethod
    def _transactions_by_participant_placement(
        cls,
        transactions: Iterable[PrizeTransaction],
    ) -> Dict[tuple, PrizeTransaction]:
        out: Dict[tuple, PrizeTransaction] = {}
        for tx in transactions:
            out.setdefault((tx.participant_id, tx.placement), tx)
        return out

    @classmethod
    def _certificates_by_participant(
        cls,
        certificates: Iterable[Certificate],
    ) -> Dict[int, Certificate]:
        out: Dict[int, Certificate] = {}
        for certificate in certificates:
            out.setdefault(certificate.participant_id, certificate)
        return out

    @classmethod
    def _transaction_for_rank(
        cls,
        ctx: Dict[str, Any],
        participant_id: Optional[int],
        rank: Optional[int],
    ) -> Optional[PrizeTransaction]:
        if not participant_id:
            return None
        placement = cls.RANK_TO_TRANSACTION_PLACEMENT.get(cls._int(rank))
        if placement:
            tx = ctx['transactions_by_participant_placement'].get((participant_id, placement))
            if tx:
                return tx
        participant_txs = ctx['transactions_by_participant'].get(participant_id) or []
        return participant_txs[0] if participant_txs else None

    @staticmethod
    def _registration_label(registration: Optional[Registration]) -> str:
        if not registration:
            return ''
        team = getattr(registration, 'team', None)
        if team and getattr(team, 'name', None):
            return str(team.name)
        user = getattr(registration, 'user', None)
        if user:
            return getattr(user, 'username', '') or getattr(user, 'email', '') or 'Player'
        return f'Registration #{registration.pk}'

    @staticmethod
    def _int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0


__all__ = ['TournamentRewardsReadModel']
