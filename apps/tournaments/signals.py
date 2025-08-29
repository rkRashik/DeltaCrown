# apps/tournaments/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.tournaments.models import Tournament, TournamentSettings


@receiver(post_save, sender=Tournament)
def ensure_settings_for_free_tournaments(sender, instance: Tournament, created, **kwargs):
    """
    Auto-create default settings ONLY for free tournaments.
    Paid tournaments are configured manually in tests (and in admin),
    so we must not create a duplicate TournamentSettings row.
    """
    if not created:
        return

    # If paid (entry_fee_bdt > 0), do not auto-create.
    try:
        fee = instance.entry_fee_bdt or 0
    except Exception:
        fee = 0

    if fee > 0:
        return

    # Free tournament → ensure settings exist
    TournamentSettings.objects.get_or_create(tournament=instance)
