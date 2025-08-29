# apps/notifications/services.py
import os
from typing import Optional, Any, Dict

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from apps.notifications.models import Notification

FROM_EMAIL = os.getenv("DeltaCrownEmail", "no-reply@deltacrown.local")


def _resolve_email(target: Any) -> Optional[str]:
    """
    Try to get a usable email address from:
    - UserProfile: target.user.email
    - Django User:  target.email
    - str:          if it looks like an email
    """
    try:
        user = getattr(target, "user", None)
        if user and getattr(user, "email", None):
            return user.email
    except Exception:
        pass

    if hasattr(target, "email"):
        return getattr(target, "email")

    if isinstance(target, str) and "@" in target:
        return target
    return None


def _send_templated_email(to_email: Optional[str], subject: str, template_slug: str, ctx: Dict):
    """
    Renders:
      templates/emails/<template_slug>.txt
      templates/emails/<template_slug>.html
    """
    if not to_email:
        return
    txt_path = f"emails/{template_slug}.txt"
    html_path = f"emails/{template_slug}.html"
    text = render_to_string(txt_path, ctx)
    html = render_to_string(html_path, ctx)
    msg = EmailMultiAlternatives(subject, text, FROM_EMAIL, [to_email])
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=True)


def notify(
    recipient,                   # UserProfile | User | str(email)
    type: str,                   # Notification.Type.*
    title: str = "",
    body: str = "",
    url: str = "",
    tournament=None,             # Optional[Tournament]
    email_subject: Optional[str] = None,
    email_template: Optional[str] = None,
    email_ctx: Optional[Dict] = None,
    **extra,                     # e.g., match=<Match>, team=<Team>, etc.
):
    """
    Creates a Notification row (if possible) and optionally sends an email.

    Accepts extra keyword args that match Notification fields
    (e.g. match=<Match>) — safely filtered to actual model fields.
    """
    # Build the DB payload
    data = {
        "recipient": recipient if hasattr(recipient, "pk") else None,
        "type": type,
        "title": title or "",
        "body": body or "",
        "url": url or "",
        "tournament": tournament,
    }

    # Only include extras that are actual Notification fields
    notif_field_names = {f.name for f in Notification._meta.get_fields()}
    for k, v in extra.items():
        if k in notif_field_names:
            data[k] = v

    notif = None
    try:
        notif = Notification.objects.create(**data)
    except Exception:
        # If recipient isn't a UserProfile or other constraint fails,
        # still allow email-only notifications.
        pass

    # Email (optional)
    if email_template and email_subject:
        to_email = _resolve_email(recipient)
        ctx = dict(email_ctx or {})
        ctx.setdefault("title", title)
        ctx.setdefault("body", body)
        ctx.setdefault("url", url)
        ctx.setdefault("t", tournament)
        _send_templated_email(to_email, email_subject, email_template, ctx)

    return notif


# ---------- Email wrapper helpers expected by views/admin ----------

def send_payment_instructions_email(profile, tournament, method: str, receive_number: str, amount, trx_note: str = ""):
    """
    Sends the initial payment instruction email to a registrant.
    """
    subject = f"[DeltaCrown] Payment instructions – {tournament.name}"
    ctx = {
        "t": tournament,
        "profile": profile,
        "method": method,
        "receive_number": receive_number,
        "amount": amount,
        "trx_note": trx_note or "",
    }
    _send_templated_email(_resolve_email(profile), subject, "payment_instructions", ctx)


def send_payment_verified_email(profile, tournament, registration):
    """
    Sends the 'payment verified' email to the registrant.
    """
    subject = f"[DeltaCrown] Payment verified – {tournament.name}"
    ctx = {
        "t": tournament,
        "profile": profile,
        "registration": registration,
    }
    _send_templated_email(_resolve_email(profile), subject, "payment_verified", ctx)


def send_payment_rejected_email(profile, tournament, registration):
    """
    Sends the 'payment rejected' email to the registrant.
    """
    subject = f"[DeltaCrown] Payment issue – {tournament.name}"
    ctx = {
        "t": tournament,
        "profile": profile,
        "registration": registration,
    }
    _send_templated_email(_resolve_email(profile), subject, "payment_rejected", ctx)
