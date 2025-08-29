from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.notifications.services import notify
from apps.notifications.models import Notification
from apps.tournaments.models import Registration

@receiver(post_save, sender=Registration)
def on_registration_save(sender, instance: Registration, created, **kwargs):
    # fire only for confirmed
    if instance.status != "CONFIRMED":
        return

    # Solo
    if instance.user_id:
        p = instance.user
        if not Notification.objects.filter(recipient=p, type=Notification.Type.REG_CONFIRM, tournament=instance.tournament).exists():
            notify(
                p, Notification.Type.REG_CONFIRM,
                title=f"Registration confirmed: {instance.tournament.name}",
                body="You’re in! Good luck.",
                url=f"/t/{instance.tournament.slug}/",
                tournament=instance.tournament,
                email_subject=f"[DeltaCrown] Registration confirmed – {instance.tournament.name}",
                email_template="reg_confirm",
                email_ctx={"t": instance.tournament, "profile": p},
            )
        return

    # Team (notify captain if available)
    if instance.team_id and getattr(instance.team, "captain_id", None):
        cap = instance.team.captain
        if not Notification.objects.filter(recipient=cap, type=Notification.Type.REG_CONFIRM, tournament=instance.tournament).exists():
            notify(
                cap, Notification.Type.REG_CONFIRM,
                title=f"Team registered: {instance.team.tag} to {instance.tournament.name}",
                body="Your team is confirmed. See you on match day.",
                url=f"/t/{instance.tournament.slug}/",
                tournament=instance.tournament,
                email_subject=f"[DeltaCrown] Team registration confirmed – {instance.tournament.name}",
                email_template="reg_confirm",
                email_ctx={"t": instance.tournament, "team": instance.team, "profile": cap},
            )

# Optional: TeamInvite hook (only if your app defines TeamInvite)
try:
    from apps.teams.models import TeamInvite
except Exception:
    TeamInvite = None

if TeamInvite:
    @receiver(post_save, sender=TeamInvite)
    def on_team_invite_save(sender, instance: "TeamInvite", created, **kwargs):
        if not created:
            return
        p = instance.invited_user
        notify(
            p, Notification.Type.TEAM_INVITE,
            title=f"Team invite: {instance.team.name}",
            body=f"You’ve been invited by {instance.invited_by.display_name} to join {instance.team.tag}.",
            url=f"/teams/invites/",
            tournament=None,
            email_subject=f"[DeltaCrown] Team invite – {instance.team.name}",
            email_template="team_invite",
            email_ctx={"team": instance.team, "inviter": instance.invited_by, "profile": p},
        )
