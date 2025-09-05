from __future__ import annotations

import os
from typing import Iterable, Optional, Any, Dict

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.db import transaction

User = get_user_model()
FROM_EMAIL = os.getenv("DeltaCrownEmail", "no-reply@deltacrown.local")

Notification = apps.get_model("notifications", "Notification")


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
    """Return an email from auth.User / UserProfile / raw string."""
    if isinstance(target, str):
        return target
    u = getattr(target, "user", None)
    if u and getattr(u, "email", ""):
        return u.email
    if getattr(target, "email", ""):
        return target.email
    return None


def _to_auth_user(target: Any) -> Optional[User]:
    """Normalize target to auth.User (UserProfile → .user; User → itself)."""
    if getattr(target, "user", None) and getattr(getattr(target, "user"), "_meta", None):
        usr = target.user
        if getattr(usr._meta, "model_name", "") == "user":
            return usr
    if getattr(target, "_meta", None) and getattr(target._meta, "model_name", "") == "user":
        return target
    return None


def _send_templated_email(to_email: Optional[str], subject: str, template_slug: str, ctx: Dict[str, Any]) -> bool:
    """
    Render & send multipart email:
      notifications/email/{slug}.txt (required)
      notifications/email/{slug}.html (optional)
    If templates are missing, skip quietly (tests may omit them).
    """
    if not to_email:
        return False
    try:
        txt = render_to_string(f"notifications/email/{template_slug}.txt", ctx)
    except TemplateDoesNotExist:
        return False
    try:
        html = render_to_string(f"notifications/email/{template_slug}.html", ctx)
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
    match=None,
    dedupe: bool = True,
    fingerprint: Optional[str] = None,
    email_subject: Optional[str] = None,
    email_template: Optional[str] = None,
    email_ctx: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Create Notification rows for auth.User recipients and optionally send emails.
    RETURNS a dict: {"created": X, "skipped": Y, "email_sent": Z}
    """
    event_str = event or ntype or "generic"

    # Map to enum when possible; else fall back to "generic"
    enum_values = set(getattr(Notification, "Type").values) if hasattr(Notification, "Type") else set()
    type_str = event_str if event_str in enum_values else "generic"

    created = skipped = sent = 0

    # Detect presence of an optional fingerprint column on your Notification model
    has_fp = any(getattr(f, "name", None) == "fingerprint" for f in Notification._meta.get_fields())

    for target in recipients:
        user = _to_auth_user(target)

        if user is not None:
            with transaction.atomic():
                if has_fp and fingerprint:
                    obj, was_created = Notification.objects.get_or_create(
                        recipient=user,
                        fingerprint=fingerprint,
                        defaults={
                            "type": type_str,
                            "event": event_str,
                            "title": title or "",
                            "body": body or "",
                            "url": url or "",
                            "tournament": tournament,
                            "match": match,
                        },
                    )
                    if was_created:
                        created += 1
                    else:
                        skipped += 1
                else:
                    # Fallback dedupe tuple (works even when fingerprint column isn't present)
                    if dedupe:
                        exists = Notification.objects.filter(
                            recipient=user,
                            type=type_str,
                            event=event_str,
                            tournament=tournament,
                            match=match,
                        ).exists()
                        if exists:
                            skipped += 1
                        else:
                            Notification.objects.create(
                                recipient=user,
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
                        Notification.objects.create(
                            recipient=user,
                            type=type_str,
                            event=event_str,
                            title=title or "",
                            body=body or "",
                            url=url or "",
                            tournament=tournament,
                            match=match,
                        )
                        created += 1

        # Optional email (quiet if templates missing)
        if email_subject and email_template:
            if _send_templated_email(_resolve_email(target), email_subject, email_template, email_ctx or {}):
                sent += 1

    return {"created": created, "skipped": skipped, "email_sent": sent}


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


__all__ = ["notify", "emit", "EmitResult"]
