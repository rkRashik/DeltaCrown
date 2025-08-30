from django.apps import apps
from django.db.models.signals import post_save
from django.dispatch import receiver

Notification = apps.get_model("notifications", "Notification")
UserProfile  = apps.get_model("user_profile", "UserProfile")
Registration = apps.get_model("tournaments", "Registration")
Bracket      = apps.get_model("tournaments", "Bracket")
Match        = apps.get_model("tournaments", "Match")


def _profile_from_team(team):
    return getattr(team, "captain", None)


@receiver(post_save, sender=Registration)
def on_registration_saved(sender, instance, created, **kwargs):
    # Notify when a registration is confirmed (idempotent)
    if getattr(instance, "status", "") != "CONFIRMED":
        return

    if instance.user_id:
        recipient = instance.user
    elif instance.team_id:
        recipient = _profile_from_team(instance.team)
    else:
        return

    if not recipient:
        return

    Notification.notify_once(
        recipient=recipient,
        type=Notification.Type.REG_CONFIRMED,
        title=f"Registration confirmed — {instance.tournament.name}",
        url=f"/tournaments/{instance.tournament.slug}/",
        tournament=instance.tournament,
    )


@receiver(post_save, sender=Bracket)
def on_bracket_created(sender, instance, created, **kwargs):
    if not created:
        return
    t = instance.tournament
    for r in Registration.objects.filter(tournament=t, status="CONFIRMED").select_related(
        "user__user", "team__captain__user"
    ):
        recipient = r.user or _profile_from_team(r.team)
        if not recipient:
            continue
        Notification.notify_once(
            recipient=recipient,
            type=Notification.Type.BRACKET_READY,
            title=f"Bracket ready — {t.name}",
            url=f"/tournaments/{t.slug}/",
            tournament=t,
        )


@receiver(post_save, sender=Match)
def on_match_saved(sender, instance, created, **kwargs):
    if created:
        for side in ("a", "b"):
            user = getattr(instance, f"user_{side}", None)
            team = getattr(instance, f"team_{side}", None)
            recipient = user or _profile_from_team(team) if team else user
            if recipient:
                Notification.notify_once(
                    recipient=recipient,
                    type=Notification.Type.MATCH_SCHEDULED,
                    title=f"Match scheduled — Round {instance.round_no}",
                    url=f"/tournaments/match/{instance.id}/report/",
                    match=instance,
                    tournament=instance.tournament,
                )
        return

    if getattr(instance, "state", "") == "VERIFIED":
        winner = getattr(instance, "winner_user", None) or _profile_from_team(
            getattr(instance, "winner_team", None)
        )
        if winner:
            Notification.notify_once(
                recipient=winner,
                type=Notification.Type.RESULT_VERIFIED,
                title="Result verified — you advance to next round",
                url=f"/tournaments/match/{instance.id}/report/",
                match=instance,
                tournament=instance.tournament,
            )
