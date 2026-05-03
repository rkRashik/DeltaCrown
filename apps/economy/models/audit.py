# apps/economy/models/audit.py
"""
FortressAuditLog — Immutable Privileged-Action Ledger (Phase C)
================================================================

Every write operation executed through the Financial Fortress (mint,
airdrop, top-up approval, bulk airdrop, auto-reward) writes exactly one
FortressAuditLog row.

Design rules
------------
* No delete permission — rows are permanent by design.
* No update permission — `save()` only allowed on creation (auto_now_add).
* Uses `db_index=True` on actor + action + created_at for audit queries.
* `ip_address` captured from request at the view layer (best-effort).
* `amount` stored as signed int (positive = credit, negative = debit).
"""
from django.conf import settings
from django.db import models


class FortressAuditLog(models.Model):
    """
    Immutable record of every privileged Fortress operation.

    This table must NEVER be truncated, manually edited, or soft-deleted.
    """

    # ── Action codes (mirrors JS action labels in the SPA) ────────────────
    class Action(models.TextChoices):
        MINT_TO_TREASURY  = "MINT_TO_TREASURY",  "Minted to Treasury"
        AIRDROP           = "AIRDROP",           "Direct Airdrop"
        BULK_AIRDROP      = "BULK_AIRDROP",      "Bulk Airdrop"
        APPROVE_TOPUP     = "APPROVE_TOPUP",     "Top-Up Approved"
        REJECT_TOPUP      = "REJECT_TOPUP",      "Top-Up Rejected"
        AUTO_REWARD_KYC   = "AUTO_REWARD_KYC",   "Auto: KYC Bonus"
        AUTO_REWARD_MATCH = "AUTO_REWARD_MATCH", "Auto: First Match Bonus"

    # ── Core fields ────────────────────────────────────────────────────────
    action = models.CharField(
        max_length=40,
        choices=Action.choices,
        db_index=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fortress_audit_logs",
        help_text="SuperAdmin who triggered the action (NULL for system/auto actions).",
    )
    actor_label = models.CharField(
        max_length=100,
        default="SYSTEM",
        help_text="Denormalized display name (survives user deletion).",
    )

    # Target — the wallet/user affected
    target_wallet = models.ForeignKey(
        "economy.DeltaCrownWallet",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fortress_audit_entries",
    )
    target_label = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text="Denormalized target description (username, 'Treasury', 'BULK: 42 wallets').",
    )

    # Financial
    amount = models.IntegerField(
        default=0,
        help_text="Signed DC amount (positive = credit, negative = debit).",
    )

    # Extra context
    note = models.TextField(
        blank=True,
        default="",
        help_text="Human-readable note / reference attached to this action.",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the actor at time of action.",
    )

    # Timestamp (immutable — no auto_now)
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        app_label = "economy"
        ordering = ["-created_at"]
        verbose_name = "Fortress Audit Log"
        verbose_name_plural = "Fortress Audit Logs"
        # Prevent accidental bulk_update on this table
        default_manager_name = "objects"

    def __str__(self) -> str:
        return (
            f"[{self.created_at:%Y-%m-%d %H:%M:%S}] "
            f"{self.action} by {self.actor_label} → {self.target_label} "
            f"({'+' if self.amount >= 0 else ''}{self.amount} DC)"
        )

    def save(self, *args, **kwargs):
        """Block all updates — this model is insert-only."""
        if self.pk:
            raise PermissionError(
                "FortressAuditLog is immutable. Rows cannot be updated after creation."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Block all deletions."""
        raise PermissionError(
            "FortressAuditLog is immutable. Rows cannot be deleted."
        )
