from typing import Union, Optional
from django.core.mail import send_mail

Recipient = Union[str, "django.contrib.auth.models.User"]


def _to_email(recipient: Recipient) -> Optional[str]:
    if isinstance(recipient, str):
        return recipient
    return getattr(recipient, "email", None)


def _fmt(obj, *attrs, default: str = "-"):
    val = obj
    for a in attrs:
        val = getattr(val, a, None)
        if val is None:
            return default
    return val


def send_dispute_opened(recipient: Recipient, dispute) -> bool:
    to = _to_email(recipient)
    if not to:
        return False
    subject = f"[DeltaCrown] Dispute opened — #{_fmt(dispute, 'id')}"
    body = (
        f"A dispute has been opened for match #{_fmt(dispute, 'match', 'id')}.\n"
        f"Reason: {_fmt(dispute, 'reason', default='(no reason provided)')}\n"
    )
    send_mail(subject, body, None, [to], fail_silently=True)
    return True


def send_dispute_resolved(recipient: Recipient, dispute) -> bool:
    to = _to_email(recipient)
    if not to:
        return False
    subject = f"[DeltaCrown] Dispute resolved — #{_fmt(dispute, 'id')}"
    body = (
        f"Your dispute for match #{_fmt(dispute, 'match', 'id')} has been resolved.\n"
        f"Outcome: {_fmt(dispute, 'status', default='resolved')}\n"
    )
    send_mail(subject, body, None, [to], fail_silently=True)
    return True
