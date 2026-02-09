"""
Celery tasks for vNext Organizations and Teams.

This module contains asynchronous tasks for bulk operations:
- Team ranking recalculations (nightly)
- Inactivity decay processing (nightly)
- Organization aggregate ranking updates (nightly)

Phase 4 - Task P4-T2
"""

from .rankings import (
    recalculate_team_rankings,
    apply_inactivity_decay,
    recalculate_organization_rankings,
)

# Discord integration tasks
from .discord_sync import (
    send_discord_announcement,
    send_discord_chat_message,
    validate_discord_bot_presence,
    sync_discord_role,
)

# Legacy task aliases — registered under the old apps.teams.tasks.* names
# so Celery Beat schedules continue to work during migration.
from .legacy_bridge import (
    recompute_team_rankings,
    clean_expired_invites,
    expire_sponsors_task,
    process_scheduled_promotions_task,
)

__all__ = [
    'recalculate_team_rankings',
    'apply_inactivity_decay',
    'recalculate_organization_rankings',
    'send_discord_announcement',
    'send_discord_chat_message',
    'validate_discord_bot_presence',
    'sync_discord_role',
    'recompute_team_rankings',
    'clean_expired_invites',
    'expire_sponsors_task',
    'process_scheduled_promotions_task',
]
