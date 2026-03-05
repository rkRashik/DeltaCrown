"""
Discord Webhook Celery Tasks.

Tasks:
    dispatch_discord_webhook  — Async HTTP dispatch with retry + delivery logging
"""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name='apps.tournaments.tasks.dispatch_discord_webhook',
    bind=True,
    max_retries=3,
    default_retry_delay=30,   # 30 s, then 60 s, then 120 s (exponential via countdown)
    ignore_result=True,
    queue='default',
)
def dispatch_discord_webhook(
    self,
    tournament_id: int,
    webhook_url: str,
    embed: dict,
    event: str = 'unknown',
    content: str = None,
):
    """
    Async Discord webhook dispatcher with retry and delivery logging.

    Called from DiscordWebhookService.send_event_async() instead of making
    a blocking HTTP call in the request thread.

    Args:
        tournament_id: Tournament PK (for logging only)
        webhook_url:   Discord webhook URL
        embed:         Discord embed dict (pre-built by DiscordWebhookService)
        event:         Event name string for the delivery log
        content:       Optional plain-text content above the embed
    """
    from apps.tournaments.services.discord_webhook import DiscordWebhookService
    from apps.tournaments.models.discord_webhook_log import DiscordWebhookLog

    success = False
    response_code = None
    error_message = ''

    try:
        # Use the synchronous post_embed — but now runs in a worker process
        result = DiscordWebhookService._post_embed_raw(webhook_url, embed, content)
        success = result.get('success', False)
        response_code = result.get('status_code')
        if not success:
            error_message = result.get('error', '')
    except Exception as exc:
        error_message = str(exc)
        logger.error(
            "[discord_task] Unhandled error dispatching webhook for tournament %s / %s: %s",
            tournament_id, event, exc,
        )
        # Exponential backoff: 30s, 60s, 120s
        countdown = 30 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
    finally:
        # Always log — even on failure
        DiscordWebhookLog.record(
            tournament_id=tournament_id,
            event=event,
            webhook_url=webhook_url,
            success=success,
            response_code=response_code,
            error_message=error_message,
        )

    if not success:
        # Retry on HTTP errors (rate limits, server errors)
        if response_code and response_code in (429, 500, 502, 503, 504):
            countdown = 30 * (2 ** self.request.retries)
            raise self.retry(
                exc=Exception(f"Discord returned {response_code}"),
                countdown=countdown,
            )
