# apps/economy/models/config.py
from __future__ import annotations

from decimal import Decimal

from django.db import models


class EconomyConfig(models.Model):
    """
    Singleton admin-configurable economy settings.

    Only one row ever exists (pk=1). Use EconomyConfig.get_solo() everywhere.

    Key rate: bdt_per_dc = 0.10 means 1 DC costs BDT 0.10, i.e. 1 BDT buys 10 DC.
    """

    bdt_per_dc = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal("0.1000"),
        help_text="BDT value of 1 DeltaCoin. Default 0.10 → 1 BDT = 10 DC.",
    )
    top_up_min_dc = models.PositiveIntegerField(
        default=10,
        help_text="Minimum DeltaCoins a user can top up in a single request.",
    )
    withdrawal_min_dc = models.PositiveIntegerField(
        default=50,
        help_text="Minimum DeltaCoins a user can withdraw in a single request.",
    )
    withdrawal_fee_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("2.00"),
        help_text="Processing fee charged on withdrawals, as a percentage (e.g. 2.00 = 2%).",
    )
    fortress_pin_hash = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=(
            "Hashed Fortress master PIN (use 'Set PIN' action in admin to change). "
            "If blank, the Fortress is locked and no PIN will be accepted."
        ),
    )
    fortress_pin_max_attempts = models.PositiveSmallIntegerField(
        default=5,
        help_text="Maximum consecutive wrong-PIN attempts before a 60-second cooldown.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Economy Configuration"
        verbose_name_plural = "Economy Configuration"

    def __str__(self) -> str:
        return f"EconomyConfig [1 DC = BDT {self.bdt_per_dc}]"

    # ------------------------------------------------------------------
    # Singleton accessor — always call this, never .objects.get(pk=1)
    # ------------------------------------------------------------------

    @classmethod
    def get_solo(cls) -> "EconomyConfig":
        """Get or create the single EconomyConfig row (pk=1)."""
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "bdt_per_dc": Decimal("0.10"),
                "top_up_min_dc": 10,
                "withdrawal_min_dc": 50,
                "withdrawal_fee_pct": Decimal("2.00"),
            },
        )
        return obj

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------

    @property
    def dc_per_bdt(self) -> Decimal:
        """How many DC does 1 BDT buy? (inverse of bdt_per_dc)"""
        if not self.bdt_per_dc:
            return Decimal("0")
        return (Decimal("1") / self.bdt_per_dc).quantize(Decimal("0.01"))

    # ------------------------------------------------------------------
    # Fortress PIN helpers
    # ------------------------------------------------------------------

    def set_fortress_pin(self, plain_pin: str) -> None:
        """Hash and store a new fortress PIN. Call save() after."""
        from django.contrib.auth.hashers import make_password
        self.fortress_pin_hash = make_password(plain_pin)

    def check_fortress_pin(self, plain_pin: str) -> bool:
        """Return True if plain_pin matches the stored hash."""
        if not self.fortress_pin_hash:
            return False
        from django.contrib.auth.hashers import check_password
        return check_password(plain_pin, self.fortress_pin_hash)


# ---------------------------------------------------------------------------
# Sidebar proxy — gives Django admin a dedicated "Economy Dashboard" menu entry
# ---------------------------------------------------------------------------

class EconomyDashboard(EconomyConfig):
    """
    Proxy of EconomyConfig used solely to inject a clickable
    "Economy Dashboard" link into the Django admin sidebar.

    No additional DB table is created. The admin registration for this proxy
    immediately redirects to the real custom dashboard view.
    """

    class Meta:
        proxy = True
        app_label = "economy"
        verbose_name = "Economy Dashboard"
        verbose_name_plural = "Economy Dashboard"


# ---------------------------------------------------------------------------
# Financial Fortress proxy — superuser-only admin sidebar entry
# ---------------------------------------------------------------------------

class FinancialFortress(EconomyConfig):
    """
    Proxy of EconomyConfig used solely to inject the '🛡️ Financial Fortress'
    clickable link into the Django admin sidebar.

    No additional DB table is created (proxy=True).
    The admin registration for this proxy (FinancialFortressAdmin) immediately
    redirects to the dedicated fortress_dashboard view and is visible ONLY to
    is_superuser accounts.
    """

    class Meta:
        proxy = True
        app_label = "economy"
        verbose_name = "🛡️ Financial Fortress"
        verbose_name_plural = "🛡️ Financial Fortress"
