"""
DiscordWebhookLog — Delivery receipt log for Discord webhook dispatches.

Stores the last N deliveries per tournament for observability.
Auto-purged by the `purge_old_webhook_logs` task (keep MAX_LOGS_PER_TOURNAMENT).
"""

import logging

from django.db import models

logger = logging.getLogger(__name__)

# Maximum delivery records stored per tournament (rolling window)
MAX_LOGS_PER_TOURNAMENT = 50


class DiscordWebhookLog(models.Model):
    """
    Immutable delivery receipt for a single Discord webhook dispatch.

    Created by DiscordWebhookService.post_embed() after every send attempt.
    """

    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='discord_webhook_logs',
        db_index=True,
    )
    event = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Event name (e.g. 'bracket_generated', 'match_ready')",
    )
    webhook_url_preview = models.CharField(
        max_length=80,
        blank=True,
        help_text="First 80 characters of the webhook URL (for debugging; never the full secret)",
    )
    success = models.BooleanField(
        default=False,
        db_index=True,
    )
    response_code = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="HTTP response status code from Discord (204 = success)",
    )
    error_message = models.TextField(
        blank=True,
        help_text="Exception message or Discord error body when success=False",
    )
    sent_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        app_label = 'tournaments'
        ordering = ['-sent_at']
        verbose_name = 'Discord Webhook Log'
        verbose_name_plural = 'Discord Webhook Logs'
        indexes = [
            models.Index(fields=['tournament', '-sent_at'], name='idx_discord_log_tournament'),
        ]

    def __str__(self):
        status = 'OK' if self.success else 'FAIL'
        return f"[{status}] {self.tournament_id} / {self.event} @ {self.sent_at}"

    # ── Class-level helpers ──────────────────────────────────────────────────

    @classmethod
    def record(cls, tournament_id: int, event: str, webhook_url: str, success: bool,
               response_code: int = None, error_message: str = '') -> 'DiscordWebhookLog':
        """
        Create a log entry and purge old entries beyond MAX_LOGS_PER_TOURNAMENT.

        Silently catches all exceptions so logging never blocks webhook dispatch.
        """
        try:
            entry = cls.objects.create(
                tournament_id=tournament_id,
                event=event,
                webhook_url_preview=(webhook_url or '')[:80],
                success=success,
                response_code=response_code,
                error_message=error_message or '',
            )
            # Rolling purge — keep only MAX_LOGS_PER_TOURNAMENT per tournament
            old_ids = (
                cls.objects
                .filter(tournament_id=tournament_id)
                .order_by('-sent_at')
                .values_list('id', flat=True)[MAX_LOGS_PER_TOURNAMENT:]
            )
            if old_ids:
                cls.objects.filter(id__in=list(old_ids)).delete()
            return entry
        except Exception as exc:
            logger.warning("DiscordWebhookLog.record() failed: %s", exc)
            return None  # Silently continue

    @classmethod
    def for_tournament(cls, tournament_id: int) -> models.QuerySet:
        """Last 50 delivery records for a tournament, newest first."""
        return cls.objects.filter(
            tournament_id=tournament_id,
        ).order_by('-sent_at')[:MAX_LOGS_PER_TOURNAMENT]
