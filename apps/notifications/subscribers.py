from __future__ import annotations

from django.apps import apps
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification
from .services import notify

UserProfile  = apps.get_model("user_profile", "UserProfile")
Registration = apps.get_model("tournaments", "Registration")
Tournament   = apps.get_model("tournaments", "Tournament")
Match        = apps.get_model("tournaments", "Match")


def _profile_from_team(team):
    # Team model: assume `captain` is a UserProfile (as in your codebase)
    return getattr(team, "captain", None)


@receiver(post_save, sender=Registration)
def registration_confirmed(sender, instance: "Registration", created, **kwargs):
    """
    When a registration is CONFIRMED, notify the participant.
    Works for solo (user) and team (captain) flows.
    """
    if getattr(instance, "status", "") != "CONFIRMED":
        return

    recipients = []

    # Solo
    if getattr(instance, "user_id", None):
        p = getattr(instance, "user", None)
        if p:
            recipients.append(p)

    # Team
    if getattr(instance, "team_id", None):
        cap = _profile_from_team(getattr(instance, "team", None))
        if cap:
            recipients.append(cap)

    if recipients:
        notify(
            recipients,
            Notification.Type.REG_CONFIRMED,
            title=f"Registration confirmed · {instance.tournament.name}",
            body="You're in! Watch for scheduling updates.",
            url=f"/t/{getattr(instance.tournament, 'slug', '')}/",
            tournament=getattr(instance, "tournament", None),
            dedupe=True,
            email_subject=f"[DeltaCrown] Registration confirmed – {instance.tournament.name}",
            email_template="reg_confirmed",
            email_ctx={"t": instance.tournament, "r": instance},
        )


@receiver(post_save, sender=Match)
def match_events(sender, instance: "Match", created, **kwargs):
    """
    Lightweight hooks:
    - when start_at is set (or changed) -> MATCH_SCHEDULED
    - when instance.state becomes VERIFIED -> RESULT_VERIFIED (if your model has such a state)
    """
    t = getattr(instance, "tournament", None)

    # Scheduled
    if getattr(instance, "start_at", None):
        recipients = []
        a = getattr(instance, "user_a", None) or _profile_from_team(getattr(instance, "team_a", None))
        b = getattr(instance, "user_b", None) or _profile_from_team(getattr(instance, "team_b", None))
        if a: recipients.append(a)
        if b: recipients.append(b)
        if recipients:
            notify(
                recipients,
                Notification.Type.MATCH_SCHEDULED,
                title=f"Match scheduled · {getattr(t, 'name', 'Tournament')}",
                body=f"Round {getattr(instance, 'round_no', '-')}, Position {getattr(instance, 'position', '-')}.",
                url=f"/t/{getattr(t, 'slug', '')}/",
                tournament=t,
                match=instance,
                dedupe=True,
                email_subject=f"[DeltaCrown] Match scheduled – {getattr(t, 'name', '')}",
                email_template="match_scheduled",
                email_ctx={"t": t, "m": instance},
            )

    # Result verified (only if your model uses such a state)
    if getattr(instance, "state", "") == "VERIFIED":
        winner = getattr(instance, "winner_user", None) or _profile_from_team(getattr(instance, "winner_team", None))
        if winner:
            notify(
                [winner],
                Notification.Type.RESULT_VERIFIED,
                title="Result verified — you advance to next round",
                url=f"/t/{getattr(t, 'slug', '')}/",
                tournament=t,
                match=instance,
                dedupe=True,
                email_subject=f"[DeltaCrown] Result verified – {getattr(t, 'name', '')}",
                email_template="result_verified",
                email_ctx={"t": t, "m": instance},
            )
