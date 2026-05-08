from django.apps import AppConfig


class ContractsConfig(AppConfig):
    """Crown Contracts — admin-curated self-challenge missions.

    Players pay a small entry fee in DeltaCoin to unlock a Contract,
    attempt the goal within the time limit, and earn a larger DeltaCoin
    reward + an achievement badge on success.  Failure forfeits the
    entry fee to the platform treasury.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.contracts"
    verbose_name = "Crown Contracts"
