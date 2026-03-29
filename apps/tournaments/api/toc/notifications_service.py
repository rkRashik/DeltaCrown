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
        if templates:
            template_ids = {str(t.get("id")) for t in templates}
            templates = list(templates) + [
                t for t in TOCNotificationsService._default_templates()
                if str(t.get("id")) not in template_ids
            ]
        scheduled = notif_config.get("scheduled", [])
        auto_rules = notif_config.get("auto_rules", TOCNotificationsService._default_auto_rules())
        if auto_rules:
            existing_events = {str(r.get("event")) for r in auto_rules}
            auto_rules = list(auto_rules) + [
                r for r in TOCNotificationsService._default_auto_rules()
                if str(r.get("event")) not in existing_events
            ]
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
                "name": "Match Reminder",
                "subject": "Your match is starting soon",
                "body": "Your match is starting soon in {tournament_name}. Be ready to play.",
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
                "body": "The groups have been drawn for {tournament_name}. Check your group assignment.",
                "trigger": "group_draw_complete",
                "enabled": True,
            },
            {
                "id": "schedule_generated",
                "name": "Schedule Generated",
                "subject": "Match schedule is live",
                "body": "The match schedule is live for {tournament_name}. Check your upcoming match times.",
                "trigger": "schedule_generated",
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
            {"id": "auto_schedule_generated", "event": "schedule_generated", "template_id": "schedule_generated", "enabled": True},
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
        event_name = str(data.get("event") or "tournament_update")
        notification_url = data.get("url") or f"/tournaments/{tournament.slug}/hub/"
        force_email = bool(data.get("force_email", False))
        dedupe = bool(data.get("dedupe", False))
        email_template = data.get("email_template") or "notifications/email/tournament_update.html"
        email_subject = data.get("email_subject") or subject
        email_cta_label = data.get("email_cta_label") or "View Tournament Hub"
        context_values = data.get("context") if isinstance(data.get("context"), dict) else {}
        extra_email_ctx = data.get("email_ctx") if isinstance(data.get("email_ctx"), dict) else {}

        # Determine template
        if template_id:
            templates = notif_config.get("templates", [])
            tmpl = next((t for t in templates if t["id"] == template_id), None)
            if tmpl:
                subject = subject or tmpl["subject"]
                body = body or tmpl["body"]
                email_subject = email_subject or tmpl["subject"]

        # Replace placeholders
        placeholders = {
            "tournament_name": tournament.name,
            "event_name": event_name.replace("_", " ").title(),
            **context_values,
        }
        for key, value in placeholders.items():
            body = body.replace("{" + key + "}", str(value))
            subject = subject.replace("{" + key + "}", str(value))

        email_subject = (email_subject or subject).replace("{tournament_name}", tournament.name)

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
            "event": event_name,
            "subject": subject,
            "body": body[:200],
            "url": notification_url,
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
                    "event": event_name,
                    "tournament": tournament,
                    "url": notification_url,
                    "dedupe": dedupe,
                }
                # Only include email params if email channel is enabled
                if channels.get("email", False) or force_email:
                    emit_kwargs["email_subject"] = email_subject
                    emit_kwargs["email_template"] = email_template
                    emit_kwargs["email_ctx"] = {
                        "tournament_name": tournament.name,
                        "subject": subject,
                        "body": body,
                        "event_name": event_name.replace("_", " ").title(),
                        "cta_url": notification_url,
                        "cta_label": email_cta_label,
                        "generated_at": timezone.now(),
                        **extra_email_ctx,
                    }
                notify_emit(recipient_users, **emit_kwargs)
                logger.info("Dispatched notification '%s' to %d users via emit()", subject, len(recipient_users))
        except Exception as e:
            logger.warning("Failed to dispatch via emit(): %s", e)

        # ── Also dispatch to Discord webhook (announcements) ──
        try:
            from apps.tournaments.services.discord_webhook import DiscordWebhookService
            DiscordWebhookService.send_event_async(tournament, event_name, {
                'subject': subject,
                'body': body,
                'url': notification_url,
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

            # Get auto-rules/templates and backfill missing defaults for legacy configs.
            default_rules = cls._default_auto_rules()
            stored_rules = notif_config.get("auto_rules") or []
            if stored_rules:
                existing_events = {str(r.get("event")) for r in stored_rules}
                auto_rules = list(stored_rules) + [
                    r for r in default_rules
                    if str(r.get("event")) not in existing_events
                ]
            else:
                auto_rules = default_rules

            default_templates = cls._default_templates()
            stored_templates = notif_config.get("templates") or []
            if stored_templates:
                existing_template_ids = {str(t.get("id")) for t in stored_templates}
                templates = list(stored_templates) + [
                    t for t in default_templates
                    if str(t.get("id")) not in existing_template_ids
                ]
            else:
                templates = default_templates

            # Find matching enabled rule for this event
            matching_rules = [r for r in auto_rules if r.get("event") == event and r.get("enabled", True)]
            if not matching_rules:
                return  # No rule for this event, skip silently

            ctx = dict(context or {})
            target_user_ids = ctx.pop("target_user_ids", None)
            target_override = ctx.pop("target", None)
            target = target_user_ids if isinstance(target_user_ids, list) else target_override
            if target is None:
                target = "all"

            force_email = bool(ctx.pop("force_email", False))
            dedupe = bool(ctx.pop("dedupe", False))
            notification_url = ctx.pop("url", f"/tournaments/{tournament.slug}/hub/")
            email_template = ctx.pop("email_template", "notifications/email/tournament_update.html")
            email_cta_label = ctx.pop("email_cta_label", "View Tournament Hub")
            email_ctx = ctx.pop("email_ctx", {})
            if not isinstance(email_ctx, dict):
                email_ctx = {}

            # Explicit empty audience means do not dispatch this event.
            if isinstance(target, list) and not target:
                return

            sent_subject = ""
            sent_body = ""
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
                    "event": event,
                    "subject": subject,
                    "body": body,
                    "target": target,
                    "url": notification_url,
                    "force_email": force_email,
                    "dedupe": dedupe,
                    "email_template": email_template,
                    "email_cta_label": email_cta_label,
                    "context": ctx,
                    "email_ctx": {
                        **email_ctx,
                        "notification_rule": rule.get("id", ""),
                    },
                })
                sent_subject = subject
                sent_body = body
                logger.info("Auto-notification fired: event=%s, template=%s for %s", event, template_id, tournament.slug)

            # ── Also dispatch to Discord webhook async (if configured) ──
            try:
                from apps.tournaments.services.discord_webhook import DiscordWebhookService
                discord_ctx = dict(ctx) if ctx else {}
                discord_ctx['subject'] = sent_subject if 'subject' not in discord_ctx else discord_ctx['subject']
                discord_ctx['body'] = sent_body if 'body' not in discord_ctx else discord_ctx['body']
                discord_ctx['url'] = notification_url if 'url' not in discord_ctx else discord_ctx['url']
                DiscordWebhookService.send_event_async(tournament, event, discord_ctx)
            except Exception as discord_err:
                logger.warning("Discord webhook dispatch failed for %s/%s: %s", tournament.slug, event, discord_err)
        except Exception as e:
            logger.warning("Auto-notification fire_auto_event error for %s/%s: %s", tournament.slug, event, e)
