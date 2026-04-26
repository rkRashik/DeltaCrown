import re
import logging
from email.utils import formataddr

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def normalize_from_email(value: str | None = None) -> str:
    raw = (value or getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(
        settings, "EMAIL_HOST_USER", None
    ) or "noreply@deltacrown.xyz").strip()
    addresses = re.findall(r"[-A-Za-z0-9._%+]+@[-A-Za-z0-9.]+\.[A-Za-z]{2,}", raw)
    address = addresses[-1] if addresses else raw
    return formataddr(("DeltaCrown", address))


def send_otp_email(user, code, *, expires_in_minutes: int = 10):
    """
    Send OTP verification email with HTML + plain text multipart.

    Uses EmailMultiAlternatives for better deliverability:
    - HTML + text/plain multipart (reduces spam score)
    - Proper From name for trust signals
    - List-Unsubscribe header to satisfy spam filters
    """
    subject = f"Your DeltaCrown Verification Code: {code}"
    from_email = normalize_from_email()

    context = {
        "code": code,
        "user": user,
        "expires_in_minutes": expires_in_minutes,
    }

    # Render both templates
    text_body = render_to_string("account/otp_email.txt", context)
    html_body = render_to_string("account/otp_email.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=[user.email],
        headers={
            "X-Priority": "1",
            "X-Mailer": "DeltaCrown Esports Platform",
            "List-Unsubscribe": "<mailto:unsubscribe@deltacrown.com>",
        },
    )
    msg.attach_alternative(html_body, "text/html")
    sent_count = msg.send(fail_silently=False)
    logger.info(
        "OTP email send result: sent=%s backend=%s from=%s to_domain=%s target=%s",
        sent_count,
        getattr(settings, "EMAIL_BACKEND", ""),
        from_email,
        (user.email or "").split("@")[-1],
        getattr(user, "id", None) or getattr(user, "email", ""),
    )
    return sent_count
