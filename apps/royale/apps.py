from django.apps import AppConfig


class RoyaleConfig(AppConfig):
    """Crown Royale — scheduled paid Battle Royale lobbies.

    Backed by ``apps.tournaments.Tournament`` for admin tools, brackets,
    and check-in flows.  This app owns the slot reservation and payout
    layer; bracket / match / scoring stays in the tournaments engine.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.royale"
    verbose_name = "Crown Royale"
