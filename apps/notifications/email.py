from typing import Union, Optional
from django.core.mail import send_mail

Recipient = Union[str, "django.contrib.auth.models.User"]


def _to_email(recipient: Recipient) -> Optional[str]:
    # Accept either a user object with an email or a raw email string.
    if isinstance(recipient, str):
        return recipient
    return getattr(recipient, "email", None)


def _fmt(obj, *attrs, default: str = "-"):
    """
    Safe attribute access for objects we don't strictly type here.
    Example: _fmt(match, "tournament", "name") to try match.tournament.name
    """
    cur = obj
    for a in attrs:
        cur = getattr(cur, a, None)
        if cur is None:
            return default
    return str(cur)


def send_match_scheduled(recipient: Recipient, match) -> bool:
    to = _to_email(recipient)
    if not to:
        return False
    subject = f"[DeltaCrown] Match scheduled — #{_fmt(match, 'id')}"
    tournament = _fmt(match, "tournament", "name", default="Tournament")
    body = (
        f"Your match #{_fmt(match, 'id')} in {tournament} is scheduled.\n"
        f"Round: {_fmt(match, 'round_no')}\n"
        f"Participants: "
        f"{_fmt(match, 'user_a', 'display_name', default=_fmt(match, 'team_a', 'tag', default='TBD'))} vs "
        f"{_fmt(match, 'user_b', 'display_name', default=_fmt(match, 'team_b', 'tag', default='TBD'))}\n"
    )
    send_mail(subject, body, None, [to], fail_silently=False)
    return True


def send_match_verified(recipient: Recipient, match) -> bool:
    to = _to_email(recipient)
    if not to:
        return False
    subject = f"[DeltaCrown] Match verified — #{_fmt(match, 'id')}"
    tournament = _fmt(match, "tournament", "name", default="Tournament")
    body = (
        f"Your match #{_fmt(match, 'id')} in {tournament} has been verified.\n"
        f"Final score: {_fmt(match, 'score_a', default='-')} – {_fmt(match, 'score_b', default='-')}\n"
    )
    send_mail(subject, body, None, [to], fail_silently=False)
    return True


def send_dispute_opened(recipient: Recipient, dispute) -> bool:
    to = _to_email(recipient)
    if not to:
        return False
    subject = f"[DeltaCrown] Dispute opened — #{_fmt(dispute, 'id')}"
    body = (
        f"A dispute has been opened for match #{_fmt(dispute, 'match', 'id')}.\n"
        f"Reason: {_fmt(dispute, 'reason', default='(not provided)')}\n"
    )
    send_mail(subject, body, None, [to], fail_silently=False)
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
    send_mail(subject, body, None, [to], fail_silently=False)
    return True
