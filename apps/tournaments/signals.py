from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Tournament, TournamentSettings

@receiver(post_save, sender=Tournament)
def ensure_settings(sender, instance, created, **kwargs):
    if created:
        TournamentSettings.objects.get_or_create(tournament=instance)
    else:
        # Safety: ensure it exists for legacy tournaments
        TournamentSettings.objects.get_or_create(tournament=instance)
