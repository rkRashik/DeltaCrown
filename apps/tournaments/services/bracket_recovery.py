"""Worker-independent recovery of bracket advancement.

``BracketService.update_bracket_after_match`` is the only writer of
``BracketNode.winner_id`` and runs atomically, so a finished match whose node
still has no winner is, by construction, one whose advancement never committed
(swallowed signal error, unprocessed Celery task, crash). That state is the
durable "pending" marker: no schema change, no queue.
"""
import logging
from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

logger = logging.getLogger(__name__)

# Let the normal post-save signal commit first.
GRACE = timedelta(minutes=2)
# After a failure, leave the node alone for a while so one bad row cannot starve the batch.
FAILURE_BACKOFF_SECONDS = 900


def advance_pending_matches(limit: int = 25) -> dict:
    from apps.brackets.models import Bracket, BracketNode
    from apps.tournaments.models.match import Match
    from apps.tournaments.models.tournament import Tournament
    from apps.tournaments.services.bracket_service import BracketService

    now = timezone.now()
    candidates = list(
        BracketNode.objects.filter(
            is_deleted=False,
            winner_id__isnull=True,
            match__isnull=False,
            match__is_deleted=False,
            match__state__in=(Match.COMPLETED, Match.FORFEIT),
            match__winner_id__isnull=False,
            match__updated_at__lt=now - GRACE,
            bracket__tournament__status=Tournament.LIVE,
            bracket__tournament__is_deleted=False,
        ).filter(
            Q(match__winner_id=F('match__participant1_id'))
            | Q(match__winner_id=F('match__participant2_id'))
        ).exclude(
            # Parent slot already holds the winner (legacy/repair): not stuck, don't re-run history.
            # Not for double elimination: the WB loser drop must still run.
            ~Q(bracket__format=Bracket.DOUBLE_ELIMINATION)
            & (
                Q(parent_slot=1, parent_node__participant1_id=F('match__winner_id'))
                | Q(parent_slot=2, parent_node__participant2_id=F('match__winner_id'))
            )
        ).order_by('match__updated_at').values_list('pk', flat=True)[: limit * 3]
    )
    backoff_keys = {pk: f'bracket_advance_failed:{pk}' for pk in candidates}
    blocked = cache.get_many(backoff_keys.values())
    candidates = [pk for pk in candidates if backoff_keys[pk] not in blocked][:limit]

    advanced = skipped = failed = 0
    for pk in candidates:
        try:
            with transaction.atomic():
                node = (
                    BracketNode.objects.select_for_update(skip_locked=True, of=('self',))
                    .select_related('match')
                    .filter(pk=pk, winner_id__isnull=True)
                    .first()
                )
                if node is None:  # advanced or locked by another runner meanwhile
                    skipped += 1
                    continue
                BracketService.update_bracket_after_match(node.match)
            advanced += 1
        except Exception:
            failed += 1
            cache.set(backoff_keys[pk], 1, FAILURE_BACKOFF_SECONDS)
            logger.exception('[bracket_recovery] advancement failed for node=%s', pk)

    if advanced or failed:
        logger.info('[bracket_recovery] advanced=%s skipped=%s failed=%s', advanced, skipped, failed)
    return {'advanced': advanced, 'skipped': skipped, 'failed': failed}
