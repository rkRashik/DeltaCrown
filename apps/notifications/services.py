from __future__ import annotations

import os
import logging
import hashlib
import json
from typing import Iterable, Optional, Any, Dict

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import PermissionDenied
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.db import transaction, connection, IntegrityError
from django.utils import timezone

User = get_user_model()
FROM_EMAIL = os.getenv("DeltaCrownEmail", "no-reply@deltacrown.local")
logger = logging.getLogger(__name__)

Notification = apps.get_model("notifications", "Notification")
_NOTIFICATION_MODEL_FIELDS = {
    f.name for f in Notification._meta.get_fields() if hasattr(f, "name")
}

_CATEGORY_NORMALIZATION_MAP = {
    "tournament": "TOURNAMENT",
    "tournaments": "TOURNAMENT",
    "team": "TEAM",
    "teams": "TEAM",
    "economy": "ECONOMY",
    "bounties": "ECONOMY",
    "social": "SOCIAL",
    "follow": "SOCIAL",
    "system": "SYSTEM",
    "warning": "WARNING",
}

_PRIORITY_LEVEL_MAP = {
    "LOW": 0,
    "NORMAL": 1,
    "HIGH": 2,
    "CRITICAL": 3,
}


def _normalize_notification_category_value(raw_value: Any, fallback: str = "SYSTEM") -> str:
    if raw_value is None:
        return fallback

    normalized = _CATEGORY_NORMALIZATION_MAP.get(str(raw_value).strip().lower())
    if normalized:
        return normalized

    candidate = str(raw_value).strip().upper()
    if candidate in {"TOURNAMENT", "TEAM", "ECONOMY", "SOCIAL", "SYSTEM", "WARNING"}:
        return candidate

    return fallback


def _generate_dedupe_key_from_kwargs(kwargs: Dict[str, Any]) -> str:
    recipient = kwargs.get("recipient")
    recipient_id = getattr(recipient, "id", None)
    event = str(kwargs.get("event") or kwargs.get("type") or "generic").strip().lower()
    title = str(kwargs.get("title") or "").strip()
    body = str(kwargs.get("body") or "").strip()
    url = str(kwargs.get("url") or "").strip()
    tournament_id = kwargs.get("tournament_id")
    match_id = kwargs.get("match_id")
    action_object_id = kwargs.get("action_object_id")

    material = "|".join(
        [
            event,
            str(recipient_id or ""),
            str(tournament_id or ""),
            str(match_id or ""),
            str(action_object_id or ""),
            title,
            body,
            url,
            timezone.now().strftime("%Y%m%d%H%M%S%f"),
        ]
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    event_prefix = "".join(ch for ch in event if ch.isalnum() or ch == "_")[:24] or "generic"
    return f"{event_prefix}:{digest}"


def _create_notification_with_dedupe_fallback(**kwargs):
    """
    Create a notification row and backfill dedupe_key when legacy ORM models
    run against stricter Postgres schemas where dedupe_key is NOT NULL.
    """
    dedupe_key_override = kwargs.pop("dedupe_key", None)

    try:
        # Keep integrity failures scoped to a savepoint so callers inside
        # outer atomic blocks can still run the SQL fallback.
        with transaction.atomic():
            return Notification.objects.create(**kwargs)
    except IntegrityError as exc:
        error_text = str(exc).lower()
        if connection.vendor != "postgresql" or "dedupe_key" not in error_text or "null" not in error_text:
            raise

        recipient = kwargs.get("recipient")
        recipient_id = getattr(recipient, "id", None)
        if not recipient_id:
            raise

        tournament_id = kwargs.get("tournament_id")
        if tournament_id is None and kwargs.get("tournament") is not None:
            tournament_id = getattr(kwargs.get("tournament"), "id", None)

        match_id = kwargs.get("match_id")
        if match_id is None and kwargs.get("match") is not None:
            match_id = getattr(kwargs.get("match"), "id", None)

        category = _normalize_notification_category_value(kwargs.get("category"), fallback="SYSTEM")
        notification_type = _normalize_notification_category_value(
            kwargs.get("notification_type"),
            fallback=category,
        )
        priority = str(kwargs.get("priority") or "NORMAL").upper()
        if priority not in _PRIORITY_LEVEL_MAP:
            priority = "NORMAL"

        dedupe_key = str(dedupe_key_override or _generate_dedupe_key_from_kwargs(kwargs))
        created_at = timezone.now()
        read_at = kwargs.get("read_at")
        is_read = bool(kwargs.get("is_read", False))
        if is_read and read_at is None:
            read_at = created_at

        action_data_value = kwargs.get("action_data")
        action_data_json = json.dumps(action_data_value if action_data_value is not None else {})

        insert_columns = [
            "recipient_id",
            "event",
            "type",
            "title",
            "body",
            "html_text",
            "url",
            "avatar_url",
            "image_url",
            "is_read",
            "is_delivered",
            "is_actionable",
            "priority",
            "created_at",
            "action_label",
            "action_url",
            "category",
            "notification_type",
            "message",
            "action_data",
            "action_object_id",
            "action_type",
            "tournament_id",
            "match_id",
            "dedupe_key",
            "payload_version",
            "priority_level",
            "read_at",
        ]
        insert_values = [
            recipient_id,
            str(kwargs.get("event") or kwargs.get("type") or "generic"),
            str(kwargs.get("type") or "generic"),
            str(kwargs.get("title") or "")[:140],
            str(kwargs.get("body") or ""),
            str(kwargs.get("html_text") or ""),
            str(kwargs.get("url") or ""),
            str(kwargs.get("avatar_url") or ""),
            str(kwargs.get("image_url") or ""),
            is_read,
            bool(kwargs.get("is_delivered", False)),
            bool(kwargs.get("is_actionable", False)),
            priority,
            created_at,
            str(kwargs.get("action_label") or ""),
            str(kwargs.get("action_url") or ""),
            category,
            notification_type,
            str(kwargs.get("message") or kwargs.get("body") or ""),
            action_data_json,
            kwargs.get("action_object_id"),
            str(kwargs.get("action_type") or ""),
            tournament_id,
            match_id,
            dedupe_key,
            1,
            _PRIORITY_LEVEL_MAP[priority],
            read_at,
        ]

        if "fingerprint" in _NOTIFICATION_MODEL_FIELDS:
            insert_columns.append("fingerprint")
            insert_values.append(str(kwargs.get("fingerprint") or ""))

        with connection.cursor() as schema_cursor:
            table_columns = {
                col.name for col in connection.introspection.get_table_description(
                    schema_cursor,
                    "notifications_notification",
                )
            }

        filtered = [
            (col, val)
            for col, val in zip(insert_columns, insert_values)
            if col in table_columns
        ]
        if not filtered or "dedupe_key" not in table_columns:
            raise

        insert_columns = [col for col, _ in filtered]
        insert_values = [val for _, val in filtered]

        placeholders = ", ".join(["%s"] * len(insert_columns))
        columns_sql = ",\n                    ".join(insert_columns)

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO notifications_notification (
                    {columns_sql}
                )
                VALUES ({placeholders})
                RETURNING id
                """,
                insert_values,
            )
            notification_id = cursor.fetchone()[0]

        return Notification.objects.get(id=notification_id)


class NotificationActionError(Exception):
    """Raised when a notification action cannot be processed safely."""

    def __init__(self, message: str, *, status_code: int = 400, error_code: str = "action_error"):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class NotificationActionService:
    """Executes actionable notification commands from action IDs."""

    @staticmethod
    def execute(user: User, action_id: str) -> dict:
        parts = (action_id or "").split("_")
        if len(parts) < 3:
            raise NotificationActionError(
                "Unsupported action identifier.",
                status_code=400,
                error_code="invalid_action_id",
            )

        namespace, verb, object_id_raw = parts[0], parts[1], parts[-1]
        if not object_id_raw.isdigit():
            raise NotificationActionError(
                "Invalid action target.",
                status_code=400,
                error_code="invalid_action_target",
            )
        object_id = int(object_id_raw)

        if namespace == "follow":
            if verb in {"accept", "approve"}:
                return NotificationActionService._approve_follow_request(user, object_id)
            if verb in {"reject", "decline"}:
                return NotificationActionService._reject_follow_request(user, object_id)
        elif namespace == "invite":
            if verb in {"accept", "approve"}:
                return NotificationActionService._accept_team_invite(user, object_id)
            if verb in {"reject", "decline"}:
                return NotificationActionService._decline_team_invite(user, object_id)
        elif namespace == "open":
            return NotificationActionService._consume_open_action(user, object_id)

        raise NotificationActionError(
            "Action is not supported.",
            status_code=400,
            error_code="unsupported_action",
        )

    @staticmethod
    @transaction.atomic
    def _approve_follow_request(user: User, follow_request_id: int) -> dict:
        FollowRequest = apps.get_model("user_profile", "FollowRequest")
        try:
            from apps.user_profile.services.follow_service import FollowService

            FollowService.approve_follow_request(target_user=user, request_id=follow_request_id)
        except FollowRequest.DoesNotExist as exc:
            raise NotificationActionError(
                "Follow request not found.",
                status_code=404,
                error_code="follow_request_not_found",
            ) from exc
        except PermissionDenied as exc:
            raise NotificationActionError(
                "Not authorized to approve this follow request.",
                status_code=403,
                error_code="follow_request_forbidden",
            ) from exc
        except ValueError as exc:
            raise NotificationActionError(
                str(exc),
                status_code=409,
                error_code="follow_request_already_processed",
            ) from exc

        consumed = NotificationActionService._consume_action_notifications(
            user=user,
            action_object_id=follow_request_id,
            action_type="follow_request",
            notification_type=Notification.Type.FOLLOW_REQUEST,
        )
        return {
            "message": "Follow request approved.",
            "consumed_notifications": consumed,
            "resource_id": follow_request_id,
        }

    @staticmethod
    @transaction.atomic
    def _reject_follow_request(user: User, follow_request_id: int) -> dict:
        FollowRequest = apps.get_model("user_profile", "FollowRequest")
        try:
            from apps.user_profile.services.follow_service import FollowService

            FollowService.reject_follow_request(target_user=user, request_id=follow_request_id)
        except FollowRequest.DoesNotExist as exc:
            raise NotificationActionError(
                "Follow request not found.",
                status_code=404,
                error_code="follow_request_not_found",
            ) from exc
        except PermissionDenied as exc:
            raise NotificationActionError(
                "Not authorized to reject this follow request.",
                status_code=403,
                error_code="follow_request_forbidden",
            ) from exc
        except ValueError as exc:
            raise NotificationActionError(
                str(exc),
                status_code=409,
                error_code="follow_request_already_processed",
            ) from exc

        consumed = NotificationActionService._consume_action_notifications(
            user=user,
            action_object_id=follow_request_id,
            action_type="follow_request",
            notification_type=Notification.Type.FOLLOW_REQUEST,
        )
        return {
            "message": "Follow request rejected.",
            "consumed_notifications": consumed,
            "resource_id": follow_request_id,
        }

    @staticmethod
    @transaction.atomic
    def _accept_team_invite(user: User, invite_id: int) -> dict:
        TeamInvite = apps.get_model("organizations", "TeamInvite")
        TeamMembership = apps.get_model("organizations", "TeamMembership")

        try:
            invite = TeamInvite.objects.select_related("team").select_for_update().get(id=invite_id)
        except TeamInvite.DoesNotExist as exc:
            raise NotificationActionError(
                "Team invite not found.",
                status_code=404,
                error_code="team_invite_not_found",
            ) from exc

        if invite.invited_user_id != user.id:
            raise NotificationActionError(
                "Not authorized to respond to this invite.",
                status_code=403,
                error_code="team_invite_forbidden",
            )

        if invite.status != "PENDING":
            raise NotificationActionError(
                "Invite is no longer pending.",
                status_code=409,
                error_code="team_invite_already_processed",
            )

        now = timezone.now()
        if invite.expires_at and invite.expires_at < now:
            invite.status = "EXPIRED"
            invite.save(update_fields=["status"])
            raise NotificationActionError(
                "This invite has expired.",
                status_code=409,
                error_code="team_invite_expired",
            )

        team = invite.team
        if not team.organization_id:
            existing = TeamMembership.objects.filter(
                user=user,
                game_id=team.game_id,
                organization_id__isnull=True,
                status="ACTIVE",
            ).exclude(team=team).first()
            if existing:
                raise NotificationActionError(
                    "You already have an active independent team for this game.",
                    status_code=409,
                    error_code="independent_team_conflict",
                )

        invite.status = "ACCEPTED"
        invite.responded_at = now
        invite.save(update_fields=["status", "responded_at"])

        membership, created = TeamMembership.objects.get_or_create(
            team=team,
            user=user,
            defaults={
                "role": invite.role,
                "status": "ACTIVE",
                "game_id": team.game_id,
                "organization_id": team.organization_id,
            },
        )
        if not created:
            membership.role = invite.role
            membership.status = "ACTIVE"
            membership.game_id = team.game_id
            membership.organization_id = team.organization_id
            membership.save(update_fields=["role", "status", "game_id", "organization_id"])

        consumed = NotificationActionService._consume_action_notifications(
            user=user,
            action_object_id=invite_id,
            action_type="team_invite",
            notification_type=Notification.Type.INVITE_SENT,
        )

        return {
            "message": f"You joined {team.name}.",
            "consumed_notifications": consumed,
            "resource_id": invite_id,
            "team_slug": team.slug,
        }

    @staticmethod
    @transaction.atomic
    def _decline_team_invite(user: User, invite_id: int) -> dict:
        TeamInvite = apps.get_model("organizations", "TeamInvite")
        try:
            invite = TeamInvite.objects.select_for_update().get(id=invite_id)
        except TeamInvite.DoesNotExist as exc:
            raise NotificationActionError(
                "Team invite not found.",
                status_code=404,
                error_code="team_invite_not_found",
            ) from exc

        if invite.invited_user_id != user.id:
            raise NotificationActionError(
                "Not authorized to respond to this invite.",
                status_code=403,
                error_code="team_invite_forbidden",
            )

        if invite.status != "PENDING":
            raise NotificationActionError(
                "Invite is no longer pending.",
                status_code=409,
                error_code="team_invite_already_processed",
            )

        invite.status = "DECLINED"
        invite.responded_at = timezone.now()
        invite.save(update_fields=["status", "responded_at"])

        consumed = NotificationActionService._consume_action_notifications(
            user=user,
            action_object_id=invite_id,
            action_type="team_invite",
            notification_type=Notification.Type.INVITE_SENT,
        )
        return {
            "message": "Invite declined.",
            "consumed_notifications": consumed,
            "resource_id": invite_id,
        }

    @staticmethod
    @transaction.atomic
    def _consume_open_action(user: User, notification_id: int) -> dict:
        notification = Notification.objects.select_for_update().filter(
            id=notification_id,
            recipient=user,
        ).first()
        if not notification:
            raise NotificationActionError(
                "Notification not found.",
                status_code=404,
                error_code="notification_not_found",
            )

        notification.is_read = True
        notification.is_actionable = False
        notification.read_at = notification.read_at or timezone.now()
        notification.save(update_fields=["is_read", "is_actionable", "read_at"])
        return {
            "message": "Notification consumed.",
            "consumed_notifications": 1,
            "resource_id": notification_id,
            "action_url": notification.action_url or notification.url,
        }

    @staticmethod
    def _consume_action_notifications(
        *,
        user: User,
        action_object_id: int,
        action_type: str,
        notification_type: str,
    ) -> int:
        now = timezone.now()
        return Notification.objects.filter(
            recipient=user,
            action_object_id=action_object_id,
            action_type=action_type,
            type=notification_type,
        ).update(
            is_actionable=False,
            is_read=True,
            read_at=now,
        )


def _infer_category_from_event(event_str: str) -> str:
    """
    Infer notification category from event string.
    
    Args:
        event_str: Event type string
    
    Returns:
        str: Category name for enforcement
    """
    event_lower = event_str.lower()
    
    # Tournament-related
    if any(word in event_lower for word in ['tournament', 'match', 'bracket', 'result', 'checkin', 'registration']):
        return 'tournaments'
    
    # Team-related
    if any(word in event_lower for word in ['team', 'invite', 'roster', 'sponsor', 'promotion']):
        return 'teams'
    
    # Economy/bounty-related
    if any(word in event_lower for word in ['payment', 'payout', 'bounty', 'achievement', 'economy']):
        return 'bounties'
    
    # Messages
    if any(word in event_lower for word in ['message', 'chat']):
        return 'messages'
    
    # Default to system
    return 'system'


class EmitResult(dict):
    """
    Hybrid result that supports BOTH attribute access (r.created)
    and dict-style access (r["created"]). This satisfies mixed tests.
    """
    def __init__(self, created: int, skipped: int, email_sent: int = 0):
        super().__init__(created=created, skipped=skipped, email_sent=email_sent)
        self.created = created
        self.skipped = skipped
        self.email_sent = email_sent


def _resolve_email(target: Any) -> Optional[str]:
    """Return an email from accounts.User / UserProfile / raw string."""
    if isinstance(target, str):
        return target
    u = getattr(target, "user", None)
    if u and getattr(u, "email", ""):
        return u.email
    if getattr(target, "email", ""):
        return target.email
    return None


def _to_user_model(target: Any) -> Optional[User]:
    """Normalize target to accounts.User (UserProfile ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ .user; User ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ itself)."""
    if getattr(target, "user", None) and getattr(getattr(target, "user"), "_meta", None):
        usr = target.user
        if getattr(usr._meta, "model_name", "") == "user":
            return usr
    if getattr(target, "_meta", None) and getattr(target._meta, "model_name", "") == "user":
        return target
    return None


def _normalize_email_template_slug(template_slug: str) -> str:
    """Accept either bare slug or full template path and normalize to slug."""
    slug = str(template_slug or "").strip()
    if not slug:
        return ""

    slug = slug.replace("\\", "/")
    prefix = "notifications/email/"
    if slug.startswith(prefix):
        slug = slug[len(prefix):]

    if slug.endswith(".html"):
        slug = slug[:-5]
    elif slug.endswith(".txt"):
        slug = slug[:-4]

    return slug.strip("/")


def _send_templated_email(to_email: Optional[str], subject: str, template_slug: str, ctx: Dict[str, Any]) -> bool:
    """
    Render & send multipart email:
      notifications/email/{slug}.txt (required)
      notifications/email/{slug}.html (optional)
    If templates are missing, skip quietly (tests may omit them).
    
    PHASE 5B: This function should only be called after enforcement checks pass.
    """
    if not to_email or not template_slug:
        return False
    normalized_slug = _normalize_email_template_slug(template_slug)
    if not normalized_slug:
        return False

    try:
        txt = render_to_string(f"notifications/email/{normalized_slug}.txt", ctx)
    except TemplateDoesNotExist:
        return False
    try:
        html = render_to_string(f"notifications/email/{normalized_slug}.html", ctx)
    except TemplateDoesNotExist:
        html = None

    msg = EmailMultiAlternatives(subject, txt, FROM_EMAIL, [to_email])
    if html:
        msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=True)
    return True


def notify(
    recipients: Iterable[Any],
    ntype: Optional[str] = None,   # tests sometimes pass event as the 2nd positional arg
    *,
    event: Optional[str] = None,   # alias used by other callers
    title: str,
    body: str = "",
    url: str = "",
    tournament=None,
    tournament_id=None,
    match=None,
    match_id=None,
    dedupe: bool = True,
    fingerprint: Optional[str] = None,
    email_subject: Optional[str] = None,
    email_template: Optional[str] = None,
    email_ctx: Optional[Dict[str, Any]] = None,
    category: Optional[str] = None,  # PHASE 5B: Explicit category for enforcement
    bypass_user_prefs: bool = False,  # PHASE 5B: Bypass preferences for critical notifications
) -> dict:
    """
    Create Notification rows for accounts.User recipients and optionally send emails.
    RETURNS a dict: {"created": X, "skipped": Y, "email_sent": Z}
    
    PHASE 5B: Enforcement Integration
    - Checks can_deliver_notification() before sending emails
    - Respects channel/category/quiet hours preferences
    - Allows bypassing for critical system notifications
    """
    from apps.notifications.enforcement import can_deliver_notification, log_suppressed_notification
    
    event_str = event or ntype or "generic"
    
    # PHASE 5B: Determine category for enforcement
    if category is None:
        category = _infer_category_from_event(event_str)
    
    # Extract IDs from objects if provided
    if tournament is not None and tournament_id is None:
        tournament_id = getattr(tournament, 'id', None)
    if match is not None and match_id is None:
        match_id = getattr(match, 'id', None)

    # Map to enum when possible; else fall back to "generic"
    enum_values = set(getattr(Notification, "Type").values) if hasattr(Notification, "Type") else set()
    type_str = event_str if event_str in enum_values else "generic"

    created = skipped = sent = 0

    # Detect presence of an optional fingerprint column on your Notification model
    has_fp = any(getattr(f, "name", None) == "fingerprint" for f in Notification._meta.get_fields())

    for target in recipients:
        user = _to_user_model(target)

        if user is not None:
            with transaction.atomic():
                if has_fp and fingerprint:
                    if Notification.objects.filter(recipient=user, fingerprint=fingerprint).exists():
                        skipped += 1
                    else:
                        _create_notification_with_dedupe_fallback(
                            recipient=user,
                            fingerprint=fingerprint,
                            type=type_str,
                            event=event_str,
                            title=title or "",
                            body=body or "",
                            url=url or "",
                            tournament=tournament,
                            match=match,
                        )
                        created += 1
                else:
                    # Fallback dedupe tuple (works even when fingerprint column isn't present)
                    if dedupe:
                        exists = Notification.objects.filter(
                            recipient=user,
                            type=type_str,
                            event=event_str,
                            tournament_id=tournament_id,
                            match_id=match_id,
                        ).exists()
                        if exists:
                            skipped += 1
                        else:
                            _create_notification_with_dedupe_fallback(
                                recipient=user,
                                type=type_str,
                                event=event_str,
                                title=title or "",
                                body=body or "",
                                url=url or "",
                                tournament_id=tournament_id,
                                match_id=match_id,
                            )
                            created += 1
                    else:
                        _create_notification_with_dedupe_fallback(
                            recipient=user,
                            type=type_str,
                            event=event_str,
                            title=title or "",
                            body=body or "",
                            url=url or "",
                            tournament_id=tournament_id,
                            match_id=match_id,
                        )
                        created += 1

        # PHASE 5B: Optional email with enforcement checks
        if email_subject and email_template:
            user_model = _to_user_model(target)
            if user_model:
                # Check if email delivery is allowed
                if can_deliver_notification(user_model, 'email', category, bypass_user_prefs=bypass_user_prefs):
                    if _send_templated_email(_resolve_email(target), email_subject, email_template, email_ctx or {}):
                        sent += 1
                else:
                    # Log suppressed email
                    log_suppressed_notification(user_model, 'email', category, 'enforcement_blocked', title)
            else:
                # No user model, send anyway (for non-user recipients)
                if _send_templated_email(_resolve_email(target), email_subject, email_template, email_ctx or {}):
                    sent += 1
    
    # MILESTONE F: Optional webhook delivery
    webhook_sent = 0
    if getattr(settings, 'NOTIFICATIONS_WEBHOOK_ENABLED', False):
        try:
            from apps.notifications.services.webhook_service import deliver_webhook
            
            # Prepare webhook data
            webhook_data = {
                'event': event_str,
                'title': title,
                'body': body,
                'url': url,
                'recipient_count': len(list(recipients)) if recipients else 0,
                'tournament_id': tournament_id,
                'match_id': match_id,
            }
            
            # Prepare metadata
            webhook_metadata = {
                'created': created,
                'skipped': skipped,
                'email_sent': sent,
            }
            
            # Deliver webhook
            success, _ = deliver_webhook(
                event=event_str,
                data=webhook_data,
                metadata=webhook_metadata,
            )
            
            if success:
                webhook_sent = 1
        
        except Exception as e:
            # Log but don't fail notification delivery
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Webhook delivery failed: {e}")

    return {"created": created, "skipped": skipped, "email_sent": sent, "webhook_sent": webhook_sent}


def emit(
    recipients: Iterable[Any],
    *args,
    title: str,
    body: str = "",
    url: str = "",
    tournament=None,
    match=None,
    dedupe: bool = True,
    fingerprint: Optional[str] = None,
    email_subject: Optional[str] = None,
    email_template: Optional[str] = None,
    email_ctx: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> EmitResult:
    """
    Back-compat wrapper expected by tests:
      - accepts EVENT as positional 2nd arg OR keyword `event=...`
      - RETURNS an object with attributes .created/.skipped
        (and supports dict-style indexing too)
    """
    # Resolve event value from positional or keyword usage
    event_value = None
    if args:
        event_value = args[0]
    if "event" in kwargs and kwargs["event"]:
        event_value = kwargs["event"]

    result = notify(
        recipients,
        ntype=None,
        event=event_value,
        title=title,
        body=body,
        url=url,
        tournament=tournament,
        match=match,
        dedupe=dedupe,
        fingerprint=fingerprint,
        email_subject=email_subject,
        email_template=email_template,
        email_ctx=email_ctx,
    )
    return EmitResult(created=result["created"], skipped=result["skipped"], email_sent=result["email_sent"])


__all__ = ["notify", "emit", "EmitResult", "NotificationService"]


class NotificationService:
    """
    Enhanced notification service for Task 9 with multi-channel delivery.
    Supports in-app, email, and Discord notifications with user preferences.
    """
    
    @staticmethod
    def _send_notification_multi_channel(users, notification_type, title, body, url='', **metadata):
        """
        Send notification through multiple channels based on user preferences.
        
        Args:
            users: List of User objects
            notification_type: Type of notification (from Notification.Type)
            title: Notification title
            body: Notification body
            url: Optional URL
            **metadata: Additional metadata (tournament, match, etc.)
        """
        from apps.notifications.models import NotificationPreference
        from apps.notifications.tasks import send_email_notification, send_discord_notification
        
        created_notifications = []
        
        for user in users:
            # Get user preferences
            prefs = NotificationPreference.get_or_create_for_user(user)
            channels = prefs.get_channels_for_type(notification_type)
            
            # Always create in-app notification
            if 'in_app' in channels:
                notification = _create_notification_with_dedupe_fallback(
                    recipient=user,
                    type=notification_type,
                    event=notification_type,
                    title=title,
                    body=body,
                    url=url,
                    **{k: v for k, v in metadata.items() if hasattr(Notification, k)}
                )
                created_notifications.append(notification)
                
                # Queue email notification if enabled (graceful degradation
                # when Redis / Celery broker is unavailable â€” the in-app
                # notification is already persisted, email is best-effort).
                if 'email' in channels:
                    try:
                        send_email_notification.apply_async(
                            args=[notification.id],
                            ignore_result=True,
                            retry=False,
                        )
                    except Exception:
                        logger.warning(
                            "Email notification queuing failed (broker down?) â€” "
                            "in-app notification %s still delivered", notification.id,
                        )
            
            # Queue Discord notification if enabled (same graceful degradation)
            if 'discord' in channels and getattr(settings, 'DISCORD_NOTIFICATIONS_ENABLED', False):
                try:
                    send_discord_notification.apply_async(
                        args=[{
                            'title': title,
                            'body': body,
                            'url': url,
                            'color': 3447003,  # Blue
                        }],
                        ignore_result=True,
                        retry=False,
                    )
                except Exception:
                    logger.warning("Discord notification queuing failed (broker down?)")
        
        return created_notifications
    
    @staticmethod
    def notify_invite_sent(invite):
        """
        Notify user when they receive a team invite.
        
        Args:
            invite: TeamInvite object
        """
        from django.urls import reverse
        
        if not invite.invited_user:
            # Can't notify if no user profile (email-only invite)
            return None
        
        title = f"Team Invite from {invite.team.name}"
        body = f"{invite.inviter.user.username if invite.inviter else 'A team captain'} invited you to join {invite.team.name} as {invite.get_role_display()}"
        
        # Link to my_invites page where user can accept/decline
        url = reverse('organizations:team_invites')
        
        return NotificationService._send_notification_multi_channel(
            users=[invite.invited_user.user],
            notification_type='invite_sent',
            title=title,
            body=body,
            url=url
        )

    @staticmethod
    def notify_vnext_team_invite_sent(*, recipient_user, team, inviter_user=None, role: str = 'PLAYER', invite_id=None):
        """Notify user when they receive a vNext team invite (organizations.TeamMembership INVITED).

        This avoids the legacy teams.TeamInvite dependency and works for vNext membership invites.
        """
        from django.urls import reverse

        if not recipient_user:
            return None

        inviter_name = getattr(inviter_user, 'username', None) or 'A team captain'
        team_name = getattr(team, 'name', 'a team')
        title = f"Team Invite: {team_name}"
        body = f"{inviter_name} invited you to join {team_name} as {role}."

        try:
            url = reverse('organizations:team_invites')
        except Exception:
            url = '/dashboard/'

        extra = {}
        if invite_id:
            extra['action_object_id'] = invite_id
            extra['action_type'] = 'team_invite'
            extra['action_label'] = 'View Invite'
            extra['action_url'] = url

        return NotificationService._send_notification_multi_channel(
            users=[recipient_user],
            notification_type='invite_sent',
            title=title,
            body=body,
            url=url,
            **extra,
        )
    
    @staticmethod
    def notify_invite_accepted(invite):
        """
        Notify team captain when invite is accepted.
        
        Args:
            invite: TeamInvite object
        """
        # P3-T1: Use TeamAdapter for cross-system URL generation
        from apps.organizations.adapters import TeamAdapter
        
        if not invite.invited_user:
            return None
        
        title = f"{invite.invited_user.user.username} joined your team!"
        body = f"{invite.invited_user.user.username} has accepted the invite to join {invite.team.name}"
        
        # Adapter routes to correct system (legacy or vNext)
        try:
            adapter = TeamAdapter()
            url = adapter.get_team_url(invite.team.id)
        except Exception:
            # Fallback to organizations URL if adapter fails
            from django.urls import reverse
            url = reverse('organizations:team_detail', kwargs={'team_slug': invite.team.slug})
        
        # Notify team creator and managers
        recipients = []
        if invite.team.created_by:
            recipients.append(invite.team.created_by)
        
        # Add team managers
        from apps.organizations.models import TeamMembership
        managers = TeamMembership.objects.filter(
            team=invite.team,
            status='ACTIVE',
            role__in=[TeamMembership.Role.OWNER, TeamMembership.Role.GENERAL_MANAGER, TeamMembership.Role.TEAM_MANAGER]
        ).select_related('user')
        
        for membership in managers:
            if membership.user not in recipients:
                recipients.append(membership.user)
        
        if not recipients:
            return None
        
        return NotificationService._send_notification_multi_channel(
            users=recipients,
            notification_type='invite_accepted',
            title=title,
            body=body,
            url=url
        )
    
    @staticmethod
    def notify_roster_change(team, change_type, affected_user):
        """
        Notify team members about roster changes.
        
        Args:
            team: Team object
            change_type: 'added', 'removed', 'role_changed'
            affected_user: User who was affected
        """
        # P3-T1: Use TeamAdapter for cross-system URL generation
        from apps.organizations.adapters import TeamAdapter
        
        change_messages = {
            'added': f"{affected_user.username} joined the team",
            'removed': f"{affected_user.username} left the team",
            'role_changed': f"{affected_user.username}'s role was updated",
        }
        
        title = f"Roster Change: {team.name}"
        body = change_messages.get(change_type, "Team roster has been updated")
        
        # Adapter routes to correct system (legacy or vNext)
        try:
            adapter = TeamAdapter()
            url = adapter.get_team_url(team.id)
        except Exception:
            # Fallback: build URL directly from slug
            url = f"/teams/{team.slug}/"
        
        # Get all team members (support both vNext and legacy)
        if hasattr(team, 'vnext_memberships'):
            team_members = [m.user for m in team.vnext_memberships.filter(status='ACTIVE').select_related('user') if m.user]
        else:
            team_members = [member.user for member in team.members.all() if member.user]
        
        return NotificationService._send_notification_multi_channel(
            users=team_members,
            notification_type='roster_changed',
            title=title,
            body=body,
            url=url
        )
    
    @staticmethod
    def notify_tournament_registration(tournament, team):
        """
        Notify team members when team registers for tournament.
        
        Args:
            tournament: Tournament object
            team: Team object
        """
        from django.urls import reverse
        
        title = f"Registered for {tournament.name}"
        body = f"Your team {team.name} has been registered for {tournament.name}"
        url = reverse('tournaments:detail', kwargs={'slug': tournament.slug})
        
        # Get all team members
        team_members = [member.user for member in team.members.all() if member.user]
        
        return NotificationService._send_notification_multi_channel(
            users=team_members,
            notification_type='tournament_registered',
            title=title,
            body=body,
            url=url,
            tournament=tournament
        )
    
    @staticmethod
    def notify_match_result(match):
        """
        Notify teams when match result is posted.
        
        Args:
            match: Match object
        """
        from django.urls import reverse
        
        title = f"Match Result: {match.team1.name} vs {match.team2.name}"
        
        if match.winner:
            body = f"Winner: {match.winner.name}"
        else:
            body = f"Match result has been posted"
        
        url = reverse('tournaments:match_detail', kwargs={'slug': match.tournament.slug, 'match_id': match.id})
        
        # Get all members from both teams
        team1_members = [member.user for member in match.team1.members.all() if member.user]
        team2_members = [member.user for member in match.team2.members.all() if member.user]
        all_members = team1_members + team2_members
        
        return NotificationService._send_notification_multi_channel(
            users=all_members,
            notification_type='match_result',
            title=title,
            body=body,
            url=url,
            match=match,
            tournament=match.tournament
        )
    
    @staticmethod
    def notify_match_scheduled(match):
        """
        Notify teams when match is scheduled.
        
        Args:
            match: Match object
        """
        from django.urls import reverse
        
        title = f"Match Scheduled: {match.team1.name} vs {match.team2.name}"
        body = f"Your match in {match.tournament.name} has been scheduled"
        
        if match.scheduled_at:
            body += f" for {match.scheduled_at.strftime('%B %d, %Y at %H:%M UTC')}"
        
        url = reverse('tournaments:match_detail', kwargs={'slug': match.tournament.slug, 'match_id': match.id})
        
        # Get all members from both teams
        team1_members = [member.user for member in match.team1.members.all() if member.user]
        team2_members = [member.user for member in match.team2.members.all() if member.user]
        all_members = team1_members + team2_members
        
        return NotificationService._send_notification_multi_channel(
            users=all_members,
            notification_type='match_scheduled',
            title=title,
            body=body,
            url=url,
            match=match,
            tournament=match.tournament
        )
    
    @staticmethod
    def notify_ranking_changed(team, old_rank, new_rank, points_change):
        """
        Notify team about ranking changes.
        
        Args:
            team: Team object
            old_rank: Previous ranking
            new_rank: New ranking
            points_change: Change in points
        """
        from django.urls import reverse
        
        if new_rank < old_rank:
            direction = "up"
            emoji = "ðŸ“ˆ"
        else:
            direction = "down"
            emoji = "ðŸ“‰"
        
        title = f"{emoji} Ranking Update: {team.name}"
        body = f"Your team moved {direction} from #{old_rank} to #{new_rank} ({points_change:+} points)"
        
        # P3-T1: Use TeamAdapter for cross-system URL generation
        from apps.organizations.adapters import TeamAdapter
        try:
            adapter = TeamAdapter()
            url = adapter.get_team_url(team.id)
        except Exception:
            # Fallback to organizations URL if adapter fails
            url = reverse('organizations:team_detail', kwargs={'team_slug': team.slug})
        
        # Get all team members
        team_members = [member.user for member in team.members.all() if member.user]
        
        return NotificationService._send_notification_multi_channel(
            users=team_members,
            notification_type='ranking_changed',
            title=title,
            body=body,
            url=url
        )
    
    @staticmethod
    def notify_sponsor_approved(sponsor):
        """
        Notify team when sponsor is approved.
        
        Args:
            sponsor: TeamSponsor object
        """
        from django.urls import reverse
        
        title = f"Sponsor Approved: {sponsor.sponsor_name}"
        body = f"Your sponsorship with {sponsor.sponsor_name} has been approved!"
        
        # Sponsor dashboard URL (constructed manually since no dedicated route)
        url = f"/teams/{sponsor.team.slug}/"
        
        # Notify captain and co-captains
        captains = [sponsor.team.captain.user] if sponsor.team.captain else []
        
        return NotificationService._send_notification_multi_channel(
            users=captains,
            notification_type='sponsor_approved',
            title=title,
            body=body,
            url=url
        )
    
    @staticmethod
    def notify_promotion_started(promotion):
        """
        Notify team when promotion starts.
        
        Args:
            promotion: TeamPromotion object
        """
        from django.urls import reverse
        
        title = f"Promotion Started: {promotion.promotion_type}"
        body = f"Your team promotion ({promotion.get_promotion_type_display()}) is now active!"
        
        # P3-T1: Use TeamAdapter for cross-system URL generation
        from apps.organizations.adapters import TeamAdapter
        try:
            adapter = TeamAdapter()
            url = adapter.get_team_url(promotion.team.id)
        except Exception:
            # Fallback to organizations URL if adapter fails
            url = reverse('organizations:team_detail', kwargs={'team_slug': promotion.team.slug})
        
        # Notify captain
        captains = [promotion.team.captain.user] if promotion.team.captain else []
        
        return NotificationService._send_notification_multi_channel(
            users=captains,
            notification_type='promotion_started',
            title=title,
            body=body,
            url=url
        )
    
    @staticmethod
    def notify_payout_received(team, amount, reason):
        """
        Notify team when they receive a payout.
        
        Args:
            team: Team object
            amount: Amount of coins received
            reason: Reason for payout
        """
        from django.urls import reverse
        
        title = f"ðŸ’° Payout Received: {amount} coins"
        body = f"Your team received {amount} coins! Reason: {reason}"
        url = reverse('organizations:team_detail', kwargs={'team_slug': team.slug})
        
        # Get all team members
        team_members = [member.user for member in team.members.all() if member.user]
        
        return NotificationService._send_notification_multi_channel(
            users=team_members,
            notification_type='payout_received',
            title=title,
            body=body,
            url=url
        )
    
    @staticmethod
    def notify_achievement_earned(team, achievement):
        """
        Notify team when they earn an achievement.
        
        Args:
            team: Team object
            achievement: TeamAchievement object
        """
        from django.urls import reverse
        
        title = f"ðŸ† Achievement Unlocked: {achievement.title}"
        body = f"Your team earned: {achievement.description}"
        url = reverse('organizations:team_detail', kwargs={'team_slug': team.slug})
        
        # Get all team members
        team_members = [member.user for member in team.members.all() if member.user]
        
        return NotificationService._send_notification_multi_channel(
            users=team_members,
            notification_type='achievement_earned',
            title=title,
            body=body,
            url=url
        )
    
    @staticmethod
    def notify_bracket_ready(tournament):
        """
        Notify all registered teams when tournament bracket is ready.
        
        Args:
            tournament: Tournament object
        """
        from django.urls import reverse
        from django.apps import apps
        
        # Get Registration model via apps registry
        Registration = apps.get_model('tournaments', 'Registration')
        
        title = f"Bracket Ready: {tournament.name}"
        body = f"The tournament bracket has been generated. Check your matches!"
        url = reverse('tournaments:detail', kwargs={'slug': tournament.slug})
        
        # Get all registered teams' members
        registrations = Registration.objects.filter(
            tournament=tournament,
            status='approved'
        ).select_related('team')
        
        all_members = []
        for reg in registrations:
            team_members = [member.user for member in reg.team.members.all() if member.user]
            all_members.extend(team_members)
        
        # Remove duplicates
        all_members = list(set(all_members))
        
        return NotificationService._send_notification_multi_channel(
            users=all_members,
            notification_type='bracket_ready',
            title=title,
            body=body,
            url=url,
            tournament=tournament
        )
    
    @staticmethod
    def notify_user_followed(follower_user, followee_user):
        """
        Notify user when someone follows them (public account).
        
        Args:
            follower_user: User who followed (follower)
            followee_user: User being followed (followee)
            
        Returns:
            List of created notifications
            
        Example:
            >>> NotificationService.notify_user_followed(
            ...     follower_user=request.user,
            ...     followee_user=target_user
            ... )
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            from apps.user_profile.utils import get_user_profile_safe
            
            # Get follower profile for display name
            follower_profile = get_user_profile_safe(follower_user)
            display_name = follower_profile.display_name or follower_user.username
            
            # Create notification
            notification = _create_notification_with_dedupe_fallback(
                recipient=followee_user,
                type=Notification.Type.USER_FOLLOWED,
                event='user_followed',
                title=f"@{follower_user.username} followed you",
                body=f"{display_name} started following you.",
                url=f"/@{follower_user.username}/",
                action_label="View Profile",
                action_url=f"/@{follower_user.username}/",
                category="social",
                message=f"{display_name} started following you.",
                dedupe_key=f"user_followed:{followee_user.id}:{follower_user.id}:{timezone.now().strftime('%Y%m%d%H%M%S%f')}"
            )
            
            logger.info(
                f"Follow notification created: follower={follower_user.username} â†’ "
                f"followee={followee_user.username} (notif_id={notification.id})"
            )
            
            return [notification]
            
        except Exception as e:
            logger.error(
                f"Failed to create follow notification: follower={follower_user.username} â†’ "
                f"followee={followee_user.username}, error: {e}",
                exc_info=True
            )
            return []




