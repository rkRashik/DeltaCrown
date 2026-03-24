"""
TOC Notifications Center Service — Sprint 28.

Notification templates, scheduled notifications, auto-notification rules,
delivery channels, notification log, per-team messaging.
"""

import logging
import uuid
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.tournaments.models.tournament import Tournament

logger = logging.getLogger("toc.notifications")
User = get_user_model()


class TOCNotificationsService:
    """All read/write operations for the Notifications tab."""

    @staticmethod
    def get_notifications_dashboard(tournament: Tournament) -> dict:
        """Full notifications center dashboard."""
        config = tournament.config or {}
        notif_config = config.get("notifications", {})

        templates = notif_config.get("templates", TOCNotificationsService._default_templates())
        scheduled = notif_config.get("scheduled", [])
        auto_rules = notif_config.get("auto_rules", TOCNotificationsService._default_auto_rules())
        channels = notif_config.get("channels", {"in_app": True, "email": False, "discord": False})
        log = notif_config.get("log", [])

        pending = [s for s in scheduled if s.get("status") == "pending"]
        sent = [s for s in scheduled if s.get("status") == "sent"]

        return {
            "templates": templates,
            "scheduled": scheduled[-20:],
            "auto_rules": auto_rules,
            "channels": {
                **channels,
                "platform": channels.get("in_app", True),  # JS alias
            },
            "log": log[-50:],
            "summary": {
                "total_templates": len(templates),
                "template_count": len(templates),
                "pending_scheduled": len(pending),
                "scheduled_pending": len(pending),
                "sent_count": len(sent),
                "total_sent": len(sent),
                "total_log_entries": len(log),
                "active_channels": sum(1 for v in channels.values() if v),
                "active_auto_rules": sum(1 for r in auto_rules if r.get("enabled", True)),
                "auto_rules_active": sum(1 for r in auto_rules if r.get("enabled", True)),
            },
        }

    @staticmethod
    def _default_templates():
        """Default notification templates."""
        return [
            {
                "id": "match_ready",
                "name": "Match Ready",
                "subject": "Your match is ready!",
                "body": "Your match in {tournament_name} is ready. Head to the match room now.",
                "trigger": "match_ready",
                "enabled": True,
            },
            {
                "id": "checkin_reminder",
                "name": "Check-in Reminder",
                "subject": "Check-in is open",
                "body": "Check-in for {tournament_name} is now open. Please check in before it closes.",
                "trigger": "checkin_open",
                "enabled": True,
            },
            {
                "id": "match_result",
                "name": "Match Result",
                "subject": "Match result recorded",
                "body": "Your match result in {tournament_name} has been recorded: {result}.",
                "trigger": "match_complete",
                "enabled": True,
            },
            {
                "id": "tournament_update",
                "name": "Tournament Update",
                "subject": "Tournament Update",
                "body": "{message}",
                "trigger": "manual",
                "enabled": True,
            },
            {
                "id": "round_start",
                "name": "Round Start",
                "subject": "New round starting",
                "body": "Round {round_number} of {tournament_name} is starting. Check your match.",
                "trigger": "round_start",
                "enabled": True,
            },
            {
                "id": "bracket_generated",
                "name": "Bracket Generated",
                "subject": "Bracket is Ready!",
                "body": "The bracket for {tournament_name} has been generated. Check your matchups!",
                "trigger": "bracket_generated",
                "enabled": True,
            },
            {
                "id": "bracket_published",
                "name": "Bracket Published",
                "subject": "Bracket Published",
                "body": "The bracket for {tournament_name} has been published. View it now on the tournament hub.",
                "trigger": "bracket_published",
                "enabled": True,
            },
            {
                "id": "group_draw_complete",
                "name": "Group Draw Complete",
                "subject": "Group Draw Complete",
                "body": "The group draw for {tournament_name} is complete. Check your group assignment.",
                "trigger": "group_draw_complete",
                "enabled": True,
            },
            {
                "id": "checkin_closed",
                "name": "Check-in Closed",
                "subject": "Check-in has closed",
                "body": "Check-in for {tournament_name} is now closed.",
                "trigger": "checkin_closed",
                "enabled": True,
            },
        ]

    @staticmethod
    def _default_auto_rules():
        """Default auto-notification rules."""
        return [
            {"id": "auto_checkin_open", "event": "checkin_open", "template_id": "checkin_reminder", "enabled": True},
            {"id": "auto_checkin_closed", "event": "checkin_closed", "template_id": "checkin_closed", "enabled": True},
            {"id": "auto_match_ready", "event": "match_ready", "template_id": "match_ready", "enabled": True},
            {"id": "auto_match_complete", "event": "match_complete", "template_id": "match_result", "enabled": True},
            {"id": "auto_round_start", "event": "round_start", "template_id": "round_start", "enabled": True},
            {"id": "auto_bracket_generated", "event": "bracket_generated", "template_id": "bracket_generated", "enabled": True},
            {"id": "auto_bracket_published", "event": "bracket_published", "template_id": "bracket_published", "enabled": True},
            {"id": "auto_group_draw", "event": "group_draw_complete", "template_id": "group_draw_complete", "enabled": True},
        ]

    @staticmethod
    def create_template(tournament: Tournament, data: dict) -> dict:
        """Create a new notification template."""
        config = tournament.config or {}
        notif_config = config.get("notifications", {})
        templates = notif_config.get("templates", TOCNotificationsService._default_templates())

        template = {
            "id": data.get("id", f"tpl-{uuid.uuid4().hex[:8]}"),
            "name": data.get("name", "Custom Template"),
            "subject": data.get("subject", ""),
            "body": data.get("body", ""),
            "trigger": data.get("trigger", "manual"),
            "enabled": data.get("enabled", True),
            "created_at": timezone.now().isoformat(),
        }
        templates.append(template)
        notif_config["templates"] = templates
        config["notifications"] = notif_config
        tournament.config = config
        tournament.save(update_fields=["config"])
        return template

    @staticmethod
    def update_template(tournament: Tournament, template_id: str, data: dict) -> dict:
        """Update a notification template."""
        config = tournament.config or {}
        notif_config = config.get("notifications", {})
        templates = notif_config.get("templates", [])

        for t in templates:
            if t["id"] == template_id:
                for key in ("name", "subject", "body", "trigger", "enabled"):
                    if key in data:
                        t[key] = data[key]
                t["updated_at"] = timezone.now().isoformat()
                notif_config["templates"] = templates
                config["notifications"] = notif_config
                tournament.config = config
                tournament.save(update_fields=["config"])
                return t

        return {"error": "Template not found"}

    @staticmethod
    def delete_template(tournament: Tournament, template_id: str) -> dict:
        """Delete a notification template."""
        config = tournament.config or {}
        notif_config = config.get("notifications", {})
        templates = notif_config.get("templates", [])
        templates = [t for t in templates if t["id"] != template_id]
        notif_config["templates"] = templates
        config["notifications"] = notif_config
        tournament.config = config
        tournament.save(update_fields=["config"])
        return {"deleted": True}

    @staticmethod
    def send_notification(tournament: Tournament, data: dict) -> dict:
        """Send an immediate notification to participants."""
        from apps.tournaments.models.registration import Registration

        config = tournament.config or {}
        notif_config = config.get("notifications", {})

        template_id = data.get("template_id")
        subject = data.get("subject", "")
        body = data.get("body", "")
        target = data.get("target", "all")  # all, team_id, user_ids
        force_email = bool(data.get("force_email", False))

        # Determine template
        if template_id:
            templates = notif_config.get("templates", [])
            tmpl = next((t for t in templates if t["id"] == template_id), None)
            if tmpl:
                subject = subject or tmpl["subject"]
                body = body or tmpl["body"]

        # Replace placeholders
        body = body.replace("{tournament_name}", tournament.name)
        subject = subject.replace("{tournament_name}", tournament.name)

        recipient_users_qs = User.objects.none()
        if target and target != "all":
            if isinstance(target, list):
                recipient_users_qs = User.objects.filter(id__in=target)
            elif str(target).isdigit():
                # Treat numeric target as team_id
                regs = Registration.objects.filter(
                    tournament=tournament,
                    team_id=int(target),
                    user__isnull=False,
                    is_deleted=False,
                )
                recipient_users_qs = User.objects.filter(
                    id__in=regs.values_list('user_id', flat=True)
                )
        else:
            regs = Registration.objects.filter(
                tournament=tournament,
                status__in=["confirmed", "auto_approved"],
                user__isnull=False,
                is_deleted=False,
            )
            recipient_users_qs = User.objects.filter(
                id__in=regs.values_list('user_id', flat=True)
            )

        recipient_users = list(recipient_users_qs.distinct())
        recipient_count = len(recipient_users)

        # Log the notification
        log = notif_config.get("log", [])
        entry = {
            "id": f"notif-{uuid.uuid4().hex[:8]}",
            "subject": subject,
            "body": body[:200],
            "target": str(target),
            "recipient_count": recipient_count,
            "sent_at": timezone.now().isoformat(),
            "status": "sent",
        }
        log.append(entry)
        notif_config["log"] = log[-200:]  # Keep last 200
        config["notifications"] = notif_config
        tournament.config = config
        tournament.save(update_fields=["config"])

        # ── Dispatch to real notification system ──
        channels = notif_config.get("channels", {})
        try:
            from apps.notifications.services import emit as notify_emit

            if recipient_users:
                emit_kwargs = {
                    "title": subject,
                    "body": body,
                    "event": "tournament_update",
                    "tournament": tournament,
                    "url": f"/tournaments/{tournament.slug}/hub/",
                    "dedupe": False,
                }
                # Only include email params if email channel is enabled
                if channels.get("email", False) or force_email:
                    emit_kwargs["email_subject"] = subject
                    emit_kwargs["email_template"] = "notifications/email/tournament_update.html"
                    emit_kwargs["email_ctx"] = {
                        "tournament_name": tournament.name,
                        "subject": subject,
                        "body": body,
                    }
                notify_emit(recipient_users, **emit_kwargs)
                logger.info("Dispatched notification '%s' to %d users via emit()", subject, len(recipient_users))
        except Exception as e:
            logger.warning("Failed to dispatch via emit(): %s", e)

        # ── Also dispatch to Discord webhook (announcements) ──
        try:
            from apps.tournaments.services.discord_webhook import DiscordWebhookService
            DiscordWebhookService.send_event_async(tournament, 'announcement', {
                'subject': subject,
                'body': body,
            })
        except Exception as e:
            logger.warning("Discord webhook dispatch failed for announcement: %s", e)

        return entry

    @staticmethod
    def schedule_notification(tournament: Tournament, data: dict) -> dict:
        """Schedule a future notification."""
        config = tournament.config or {}
        notif_config = config.get("notifications", {})
        scheduled = notif_config.get("scheduled", [])

        entry = {
            "id": f"sched-{uuid.uuid4().hex[:8]}",
            "template_id": data.get("template_id"),
            "subject": data.get("subject", ""),
            "body": data.get("body", ""),
            "target": data.get("target", "all"),
            "send_at": data.get("send_at") or data.get("scheduled_for"),
            "status": "pending",
            "created_at": timezone.now().isoformat(),
        }
        scheduled.append(entry)
        notif_config["scheduled"] = scheduled
        config["notifications"] = notif_config
        tournament.config = config
        tournament.save(update_fields=["config"])
        return entry

    @staticmethod
    def cancel_scheduled(tournament: Tournament, scheduled_id: str) -> dict:
        """Cancel a scheduled notification."""
        config = tournament.config or {}
        notif_config = config.get("notifications", {})
        scheduled = notif_config.get("scheduled", [])

        for s in scheduled:
            if s["id"] == scheduled_id:
                s["status"] = "cancelled"
                notif_config["scheduled"] = scheduled
                config["notifications"] = notif_config
                tournament.config = config
                tournament.save(update_fields=["config"])
                return {"cancelled": True}
        return {"error": "Not found"}

    @staticmethod
    def update_auto_rules(tournament: Tournament, rules: list) -> dict:
        """Update auto-notification rules."""
        config = tournament.config or {}
        notif_config = config.get("notifications", {})
        notif_config["auto_rules"] = rules
        config["notifications"] = notif_config
        tournament.config = config
        tournament.save(update_fields=["config"])
        return {"rules": rules}

    @staticmethod
    def update_channels(tournament: Tournament, data: dict) -> dict:
        """Update notification delivery channels."""
        config = tournament.config or {}
        notif_config = config.get("notifications", {})
        channels = notif_config.get("channels", {"in_app": True, "email": False, "discord": False})

        for key in ("in_app", "email", "discord", "webhook_url"):
            if key in data:
                channels[key] = data[key]

        notif_config["channels"] = channels
        config["notifications"] = notif_config
        tournament.config = config
        tournament.save(update_fields=["config"])
        return channels

    @staticmethod
    def send_team_message(tournament: Tournament, team_id: int, data: dict) -> dict:
        """Send a notification to a specific team."""
        from apps.tournaments.models.registration import Registration

        regs = Registration.objects.filter(
            tournament=tournament, team_id=team_id,
            status__in=["confirmed", "auto_approved"],
        )
        user_ids = list(regs.values_list("user_id", flat=True))

        return TOCNotificationsService.send_notification(
            tournament,
            {
                "subject": data.get("subject", "Team Message"),
                "body": data.get("body", data.get("message", "")),
                "target": user_ids,
            },
        )

    @classmethod
    def fire_auto_event(cls, tournament: Tournament, event: str, context: dict = None):
        """
        Fire an auto-notification if a matching enabled rule exists for the event.

        Called by bracket/group/checkin services when key events occur:
          - bracket_generated, bracket_published
          - checkin_open, checkin_closed
          - match_ready, match_complete
          - round_start, group_draw_complete
          - tournament_live

        Args:
            tournament: The tournament instance
            event: Event identifier string (e.g., "bracket_generated")
            context: Optional dict with template placeholders (round_number, result, etc.)
        """
        try:
            config = tournament.config or {}
            notif_config = config.get("notifications", {})

            # Get auto-rules — fall back to defaults
            auto_rules = notif_config.get("auto_rules", cls._default_auto_rules())
            templates = notif_config.get("templates", cls._default_templates())

            # Find matching enabled rule for this event
            matching_rules = [r for r in auto_rules if r.get("event") == event and r.get("enabled", True)]
            if not matching_rules:
                return  # No rule for this event, skip silently

            ctx = context or {}
            for rule in matching_rules:
                template_id = rule.get("template_id")
                tmpl = next((t for t in templates if t.get("id") == template_id and t.get("enabled", True)), None)

                subject = ""
                body = ""
                if tmpl:
                    subject = tmpl.get("subject", "")
                    body = tmpl.get("body", "")
                else:
                    # No template — use event as subject
                    subject = event.replace("_", " ").title()
                    body = f"{tournament.name}: {subject}"

                # Replace common placeholders
                body = body.replace("{tournament_name}", tournament.name)
                subject = subject.replace("{tournament_name}", tournament.name)
                for key, val in ctx.items():
                    body = body.replace("{" + key + "}", str(val))
                    subject = subject.replace("{" + key + "}", str(val))

                cls.send_notification(tournament, {
                    "subject": subject,
                    "body": body,
                    "target": "all",
                })
                logger.info("Auto-notification fired: event=%s, template=%s for %s", event, template_id, tournament.slug)

            # ── Also dispatch to Discord webhook async (if configured) ──
            try:
                from apps.tournaments.services.discord_webhook import DiscordWebhookService
                discord_ctx = dict(ctx) if ctx else {}
                discord_ctx['subject'] = subject if 'subject' not in discord_ctx else discord_ctx['subject']
                discord_ctx['body'] = body if 'body' not in discord_ctx else discord_ctx['body']
                DiscordWebhookService.send_event_async(tournament, event, discord_ctx)
            except Exception as discord_err:
                logger.warning("Discord webhook dispatch failed for %s/%s: %s", tournament.slug, event, discord_err)
        except Exception as e:
            logger.warning("Auto-notification fire_auto_event error for %s/%s: %s", tournament.slug, event, e)
