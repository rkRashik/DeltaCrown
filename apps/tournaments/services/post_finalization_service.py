"""
Post-Finalization Service — Authoritative tournament completion lifecycle.

Once a tournament has a TournamentResult with a winner (or all bracket finals
are resolved), this service orchestrates *every* downstream effect required
for the event to read as truly "Completed" across TOC, HUB, and public pages.

Pipeline (idempotent end-to-end):
  1. Persist Tournament.status = COMPLETED (and tournament_end if missing).
  2. Run PlacementService.persist_standings to populate final_standings.
  3. Reconcile prize config so placements expose live winner names.
  4. Generate podium achievements (Champion / Runner-Up / Third / Fourth).
  5. Publish a single system announcement (deduped via config sentinel).
  6. Mark the HUB lifecycle phase as REWARDS in tournament.config.
  7. Invalidate TOC / HUB caches so all surfaces re-render.

Auto-triggered from:
  * TournamentLifecycleService.maybe_finalize_tournament — happy path
  * BracketService._maybe_finalize_tournament — final-match auto trigger
  * FinalizeView — manual recovery / idempotent sync

Calling this multiple times on the same tournament is a no-op for already-
completed steps. The sentinel ``tournament.config['post_finalization']``
records each step's last successful run for diagnostics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.tournaments.models.tournament import Tournament

logger = logging.getLogger(__name__)


_ANNOUNCEMENT_SENTINEL = 'post_finalization_announcement_id'
_ACHIEVEMENT_SENTINEL = 'post_finalization_achievements'

# Achievement name is the dedup key (user, name, context.tournament_id)
_ACHIEVEMENT_TIERS = {
    1: ('Champion', 'legendary', '🏆', 'Won the tournament — first place finisher.'),
    2: ('Runner-Up', 'epic',     '🥈', 'Finished second in the tournament final.'),
    3: ('Third Place', 'rare',   '🥉', 'Earned the bronze medal in the tournament.'),
    4: ('Semifinalist', 'rare',  '🎖️', 'Reached the tournament semifinals.'),
}


@dataclass
class PostFinalizationReport:
    tournament_id: int
    tournament_name: str
    status_persisted: bool = False
    standings_count: int = 0
    achievements_created: int = 0
    announcement_id: Optional[int] = None
    cache_invalidated: bool = False
    errors: List[str] = field(default_factory=list)
    completion_pipeline_status: Optional[str] = None

    @property
    def ok(self) -> bool:
        return not self.errors


class PostFinalizationService:
    """
    Idempotent orchestrator for the post-finalization lifecycle.

    All steps are isolated: a failure in one is logged and recorded on the
    report but does not block the others. The tournament is already
    COMPLETED before this runs, so partial failures are acceptable —
    operators can re-run via the FinalizeView idempotent path to retry.
    """

    @classmethod
    def run(
        cls,
        tournament_or_id: Union[int, Tournament],
        *,
        actor=None,
    ) -> PostFinalizationReport:
        tournament = cls._resolve_tournament(tournament_or_id)

        report = PostFinalizationReport(
            tournament_id=tournament.id,
            tournament_name=tournament.name,
        )

        # Step 1: Persist completion status (idempotent).
        cls._step_persist_completion(tournament, report, actor=actor)

        # Step 2: Persist standings.
        cls._step_persist_standings(tournament, report, actor=actor)

        # Step 3: Achievements.
        cls._step_generate_achievements(tournament, report)

        # Step 4: Announcement.
        cls._step_publish_announcement(tournament, report, actor=actor)

        # Step 5: HUB phase + sentinel.
        cls._step_mark_rewards_phase(tournament, report)

        # Step 6: Run the legacy CompletionPipeline (certificates, analytics,
        # notifications). It is *also* idempotent and stores its own metadata
        # under tournament.config['completion_pipeline'].
        cls._step_run_completion_pipeline(tournament, report, actor=actor)

        # Step 7: Cache invalidation.
        cls._step_invalidate_caches(tournament, report)

        if report.errors:
            logger.warning(
                "Post-finalization for %s finished with %d error(s): %s",
                tournament.name, len(report.errors), report.errors,
            )
        else:
            logger.info(
                "Post-finalization for %s ok: status_persisted=%s standings=%d achievements=%d announcement=%s",
                tournament.name,
                report.status_persisted,
                report.standings_count,
                report.achievements_created,
                report.announcement_id,
            )
        return report

    # ── Resolver ───────────────────────────────────────────────────────

    @staticmethod
    def _resolve_tournament(tournament_or_id: Union[int, Tournament]) -> Tournament:
        if isinstance(tournament_or_id, Tournament):
            return tournament_or_id
        return Tournament.objects.select_related('game', 'organizer').get(
            id=tournament_or_id,
        )

    # ── Step 1: persist completion ─────────────────────────────────────

    @classmethod
    def _step_persist_completion(
        cls,
        tournament: Tournament,
        report: PostFinalizationReport,
        *,
        actor=None,
    ) -> None:
        try:
            from apps.tournaments.models.result import TournamentResult
            has_winner = TournamentResult.objects.filter(
                tournament_id=tournament.id, is_deleted=False,
            ).exclude(winner_id__isnull=True).exists()
        except Exception:
            has_winner = False

        if tournament.status == Tournament.COMPLETED:
            # Already persisted. Backfill tournament_end if missing.
            if not tournament.tournament_end:
                tournament.tournament_end = timezone.now()
                tournament.save(update_fields=['tournament_end'])
            report.status_persisted = True
            return

        if not has_winner and not cls._all_finals_resolved(tournament):
            # Authoritative rule: don't force COMPLETED without a winner or
            # bracket finals resolved. Caller is responsible for waiting.
            report.errors.append(
                'completion: no TournamentResult winner and bracket finals not resolved'
            )
            return

        # Drive the transition through the formal state machine so audit /
        # on_enter callbacks fire. force=True because a winner exists →
        # match-completion guard would still pass, but we don't want a stray
        # disputed/orphan match to block.
        try:
            from apps.tournaments.services.lifecycle_service import (
                TournamentLifecycleService,
            )
            TournamentLifecycleService.transition(
                tournament_id=tournament.id,
                to_status=Tournament.COMPLETED,
                actor=actor,
                reason='Post-finalization persist completion',
                force=True,
            )
            tournament.refresh_from_db()
            report.status_persisted = True
        except ValidationError as e:
            # Already-completed → not actually an error.
            msg = str(e)
            if 'already' in msg.lower() or tournament.status == Tournament.COMPLETED:
                report.status_persisted = True
            else:
                report.errors.append(f'completion: {msg}')
        except Exception as e:
            report.errors.append(f'completion: {e}')
            logger.exception('Failed to persist completion for %s', tournament.id)

    @staticmethod
    def _all_finals_resolved(tournament: Tournament) -> bool:
        """Best-effort fallback: bracket finals are resolved if no LIVE/SCHEDULED matches remain."""
        try:
            from apps.tournaments.models.match import Match
            return not Match.objects.filter(
                tournament=tournament, is_deleted=False,
            ).exclude(
                state__in=['completed', 'cancelled', 'no_show', 'bye', 'forfeit'],
            ).exists()
        except Exception:
            return False

    # ── Step 2: standings ──────────────────────────────────────────────

    @classmethod
    def _step_persist_standings(
        cls,
        tournament: Tournament,
        report: PostFinalizationReport,
        *,
        actor=None,
    ) -> None:
        try:
            from apps.tournaments.services.placement_service import PlacementService
            result = PlacementService.persist_standings(tournament, actor=actor)
            report.standings_count = len(result.final_standings or [])
        except Exception as e:
            report.errors.append(f'standings: {e}')
            logger.exception('persist_standings failed for %s', tournament.id)

    # ── Step 3: achievements ───────────────────────────────────────────

    @classmethod
    def _step_generate_achievements(
        cls,
        tournament: Tournament,
        report: PostFinalizationReport,
    ) -> None:
        try:
            from apps.tournaments.models.result import TournamentResult
            from apps.tournaments.models.registration import Registration
            from apps.user_profile.models_main import Achievement
        except Exception as e:
            report.errors.append(f'achievements: imports failed ({e})')
            return

        result = TournamentResult.objects.filter(
            tournament=tournament, is_deleted=False,
        ).select_related('winner', 'runner_up', 'third_place', 'fourth_place').first()
        if not result:
            return

        slots = [
            (1, result.winner),
            (2, result.runner_up),
            (3, result.third_place),
            (4, result.fourth_place),
        ]

        config = tournament.config if isinstance(tournament.config, dict) else {}
        sentinel = config.get(_ACHIEVEMENT_SENTINEL) or {}
        if not isinstance(sentinel, dict):
            sentinel = {}

        created = 0
        for placement, registration in slots:
            if not registration:
                continue
            user_ids = cls._registration_user_ids(registration)
            if not user_ids:
                continue
            tier = _ACHIEVEMENT_TIERS.get(placement)
            if not tier:
                continue
            name, rarity, emoji, description = tier

            sentinel_key = str(placement)
            already_recorded = set(sentinel.get(sentinel_key) or [])

            for user_id in user_ids:
                if user_id in already_recorded:
                    continue
                # DB-level dedup: same (user, name, tournament_id) means
                # we already minted this achievement before.
                if Achievement.objects.filter(
                    user_id=user_id,
                    name=name,
                    context__tournament_id=tournament.id,
                ).exists():
                    already_recorded.add(user_id)
                    continue
                try:
                    Achievement.objects.create(
                        user_id=user_id,
                        name=name,
                        description=f'{description} — {tournament.name}',
                        emoji=emoji,
                        rarity=rarity,
                        context={
                            'tournament_id': tournament.id,
                            'tournament_slug': tournament.slug,
                            'placement': placement,
                            'registration_id': registration.pk,
                        },
                    )
                    created += 1
                    already_recorded.add(user_id)
                except Exception as e:
                    logger.warning(
                        'achievement create failed (user=%s placement=%s tournament=%s): %s',
                        user_id, placement, tournament.id, e,
                    )

            sentinel[sentinel_key] = sorted(already_recorded)

        report.achievements_created = created
        config[_ACHIEVEMENT_SENTINEL] = sentinel
        tournament.config = config
        tournament.save(update_fields=['config'])

    @staticmethod
    def _registration_user_ids(registration) -> List[int]:
        """All user ids that should receive an achievement for this placement."""
        user_ids: List[int] = []
        # Solo registration
        user_id = getattr(registration, 'user_id', None)
        if user_id:
            user_ids.append(user_id)
        # Team registration → award to every active member captured in the
        # lineup snapshot (preferred) or fall back to current memberships.
        team = getattr(registration, 'team', None)
        if team:
            lineup = getattr(registration, 'lineup_snapshot', None) or []
            if isinstance(lineup, list):
                for entry in lineup:
                    if isinstance(entry, dict):
                        uid = entry.get('user_id')
                        if uid and uid not in user_ids:
                            user_ids.append(uid)
            if not lineup:
                try:
                    from apps.organizations.models import TeamMembership
                    member_ids = list(
                        TeamMembership.objects.filter(
                            team_id=team.id,
                            status=TeamMembership.Status.ACTIVE,
                        ).values_list('user_id', flat=True)
                    )
                    for uid in member_ids:
                        if uid and uid not in user_ids:
                            user_ids.append(uid)
                except Exception:
                    pass
        return [uid for uid in user_ids if uid]

    # ── Step 4: announcement ───────────────────────────────────────────

    @classmethod
    def _step_publish_announcement(
        cls,
        tournament: Tournament,
        report: PostFinalizationReport,
        *,
        actor=None,
    ) -> None:
        config = tournament.config if isinstance(tournament.config, dict) else {}
        existing_id = config.get(_ANNOUNCEMENT_SENTINEL)
        if existing_id:
            try:
                from apps.tournaments.models import TournamentAnnouncement
                if TournamentAnnouncement.objects.filter(pk=existing_id).exists():
                    report.announcement_id = int(existing_id)
                    return
            except Exception:
                pass

        try:
            from apps.tournaments.models.result import TournamentResult
            from apps.tournaments.models import TournamentAnnouncement
        except Exception as e:
            report.errors.append(f'announcement: imports failed ({e})')
            return

        result = TournamentResult.objects.filter(
            tournament=tournament, is_deleted=False,
        ).select_related('winner', 'runner_up', 'third_place').first()
        if not result or not result.winner_id:
            return

        from apps.tournaments.services.placement_service import (
            _registration_label,
        )

        winner_label = _registration_label(result.winner)
        runner_up_label = _registration_label(result.runner_up) if result.runner_up_id else ''
        third_label = _registration_label(result.third_place) if result.third_place_id else ''

        title = f'🏆 {tournament.name} — Champion: {winner_label}'
        lines = [
            f'🏆 Champion: {winner_label}',
        ]
        if runner_up_label:
            lines.append(f'🥈 Runner-up: {runner_up_label}')
        if third_label:
            lines.append(f'🥉 Third place: {third_label}')
        lines.append('')
        lines.append('All matches concluded. Final standings and prizes are now available on the Hub.')
        message = '\n'.join(lines)

        try:
            ann = TournamentAnnouncement.objects.create(
                tournament=tournament,
                title=title,
                message=message,
                created_by=actor,
                is_pinned=True,
                is_important=True,
            )
            report.announcement_id = ann.id
            config[_ANNOUNCEMENT_SENTINEL] = ann.id
            tournament.config = config
            tournament.save(update_fields=['config'])

            # Best-effort hub refresh broadcast — never raises.
            try:
                from apps.tournaments.api.toc.announcements_service import (
                    TOCAnnouncementsService,
                )
                TOCAnnouncementsService._emit_hub_refresh(
                    tournament=tournament,
                    action='created',
                    announcement_id=ann.id,
                )
            except Exception:
                pass
        except Exception as e:
            report.errors.append(f'announcement: {e}')
            logger.exception('Announcement creation failed for %s', tournament.id)

    # ── Step 5: HUB phase ──────────────────────────────────────────────

    @classmethod
    def _step_mark_rewards_phase(
        cls,
        tournament: Tournament,
        report: PostFinalizationReport,
    ) -> None:
        try:
            config = tournament.config if isinstance(tournament.config, dict) else {}
            pf = config.get('post_finalization') or {}
            if not isinstance(pf, dict):
                pf = {}
            pf['ran_at'] = timezone.now().isoformat()
            pf['phase'] = 'rewards'
            pf['standings_count'] = report.standings_count
            pf['achievements_created'] = report.achievements_created
            pf['announcement_id'] = report.announcement_id
            pf['errors'] = list(report.errors)
            config['post_finalization'] = pf
            tournament.config = config
            tournament.save(update_fields=['config'])
        except Exception as e:
            report.errors.append(f'phase: {e}')
            logger.exception('Mark rewards phase failed for %s', tournament.id)

    # ── Step 6: legacy CompletionPipeline ──────────────────────────────

    @classmethod
    def _step_run_completion_pipeline(
        cls,
        tournament: Tournament,
        report: PostFinalizationReport,
        *,
        actor=None,
    ) -> None:
        try:
            from apps.tournaments.services.completion_pipeline import (
                CompletionPipeline,
            )
            sub_report = CompletionPipeline.run(tournament.id, actor=actor)
            report.completion_pipeline_status = sub_report.status
            for err in (sub_report.errors or []):
                report.errors.append(f'completion_pipeline: {err}')
        except Exception as e:
            # Tournament must already be COMPLETED for the pipeline; if not,
            # we logged the error in step 1 — don't double-fail here.
            logger.warning(
                'CompletionPipeline failed for %s: %s', tournament.id, e,
            )

    # ── Step 7: cache invalidation ─────────────────────────────────────

    @classmethod
    def _step_invalidate_caches(
        cls,
        tournament: Tournament,
        report: PostFinalizationReport,
    ) -> None:
        try:
            from apps.tournaments.api.toc.cache_utils import bump_toc_scopes
            bump_toc_scopes(
                tournament.id,
                'overview', 'analytics', 'brackets', 'matches',
                'participants', 'participants_adv', 'payments',
                'disputes', 'rosters', 'prizes', 'announcements',
            )
            report.cache_invalidated = True
        except Exception as e:
            logger.warning('Cache bump failed for %s: %s', tournament.id, e)

        # Best-effort Django cache key invalidation for HUB / public detail
        # rendering. These are framework-level keys with prefixes.
        try:
            from django.core.cache import cache
            keys = [
                f'hub:state:{tournament.slug}',
                f'hub:overview:{tournament.slug}',
                f'tournament:detail:{tournament.slug}',
                f'public_prize_overview_v1_{tournament.id}',
            ]
            cache.delete_many(keys)
        except Exception:
            pass


__all__ = ['PostFinalizationService', 'PostFinalizationReport']
