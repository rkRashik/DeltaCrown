"""
Tournament Hosting Configuration Model — Advanced Edition.

Singleton model that gives admins complete control over:
  - Base hosting fee (DC) and on/off toggle
  - Startup / growth promotions (time-limited, first-N users, first-N tournaments)
  - Regular user permission caps (official tag, DC prizes, slot limits, etc.)
  - Staff / official organiser privileges
  - Promo usage auto-tracking (read-only counters)

Only ONE row is ever created (enforced in save() and admin).

Used by:
  apps.tournaments.services.hosting_fee   — get_hosting_fee(), can_afford_hosting()
  apps.tournaments.views.create           — TournamentCreatePageView context
"""

import json
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

class PromoType(models.TextChoices):
    NONE        = "none",        "No promotion active"
    TIME_BASED  = "time",        "Free until a specific date"
    FIRST_N_USERS = "first_users", "Free for the first N registered users"
    FIRST_N_TOURNAMENTS = "first_tournaments", "Free for the first N tournaments created"
    ALWAYS_FREE = "always_free", "Always free (Beta / Launch mode)"


# ---------------------------------------------------------------------------
# Main Model
# ---------------------------------------------------------------------------

class TournamentHostingConfig(models.Model):
    """
    Singleton: all hosting, pricing, promotion and organiser-permission
    settings in one place. Admins edit this from:

        Admin → Tournament Config → Hosting & Pricing
    """

    # ════════════════════════════════════════════════════════════════
    # SECTION 1 — BASE HOSTING FEE
    # ════════════════════════════════════════════════════════════════

    hosting_fee_enabled = models.BooleanField(
        default=True,
        verbose_name="Hosting Fee Enabled",
        help_text=(
            "Master switch. Uncheck to make tournament creation free for EVERYONE, "
            "ignoring the DC amount and all promotions."
        ),
    )
    hosting_fee_dc = models.PositiveIntegerField(
        default=500,
        validators=[MinValueValidator(0)],
        verbose_name="Base Hosting Fee (DeltaCoin)",
        help_text=(
            "Amount charged when no promotion applies. "
            "Staff/superuser are always exempt when Staff Bypass is on. "
            "Set to 0 for free hosting without turning off the fee engine."
        ),
    )
    staff_bypass_enabled = models.BooleanField(
        default=True,
        verbose_name="Staff / Superuser Bypass",
        help_text="When on, staff and superuser accounts always host for free.",
    )

    # ════════════════════════════════════════════════════════════════
    # SECTION 2 — STARTUP PROMOTIONS
    # ════════════════════════════════════════════════════════════════

    # ── Promo type selector ──
    active_promo = models.CharField(
        max_length=24,
        choices=PromoType.choices,
        default=PromoType.NONE,
        verbose_name="Active Promotion",
        help_text=(
            "Choose which promotion is active. Only one promo runs at a time. "
            "Each type has its own configuration section below."
        ),
    )
    promo_label = models.CharField(
        max_length=128,
        blank=True,
        default="🎉 Beta Launch — Host Free!",
        verbose_name="Promo Banner Label",
        help_text="Short headline shown on the tournament creation wizard (e.g. '🎉 Beta Launch — Host Free!').",
    )
    promo_description = models.TextField(
        blank=True,
        default="We're in beta — host your first tournament completely free. Limited spots.",
        verbose_name="Promo Description",
        help_text="Longer text shown below the banner. Explain the promo to potential organisers.",
    )

    # ── Time-based promo ──
    promo_free_until = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Free Until (date/time)",
        help_text=(
            "[Time-Based Promo] Tournament creation is free for EVERYONE until this "
            "date and time. Leave blank if not using time-based promo."
        ),
    )

    # ── First-N users promo ──
    promo_first_n_users_limit = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1)],
        verbose_name="First-N Users Limit",
        help_text=(
            "[First-N Users] The first this-many users who create a tournament get it free. "
            "Tracking counter is below (read-only)."
        ),
    )
    promo_first_n_users_used = models.PositiveIntegerField(
        default=0,
        verbose_name="First-N Users Used (auto-tracked)",
        help_text="Auto-incremented each time a user gets a free hosting under this promo. Do not edit manually.",
    )

    # ── First-N tournaments promo ──
    promo_first_n_tournaments_limit = models.PositiveIntegerField(
        default=500,
        validators=[MinValueValidator(1)],
        verbose_name="First-N Tournaments Limit",
        help_text=(
            "[First-N Tournaments] The first this-many tournaments ever created on the "
            "platform are free (regardless of who creates them)."
        ),
    )
    promo_first_n_tournaments_used = models.PositiveIntegerField(
        default=0,
        verbose_name="First-N Tournaments Used (auto-tracked)",
        help_text="Auto-incremented each time a tournament is created under this promo.",
    )

    # ── Signup bonus DC ──
    signup_bonus_dc_enabled = models.BooleanField(
        default=False,
        verbose_name="New User Signup Bonus Enabled",
        help_text="Award DeltaCoin to every new user on their first tournament creation.",
    )
    signup_bonus_dc_amount = models.PositiveIntegerField(
        default=500,
        verbose_name="Signup Bonus Amount (DC)",
        help_text="DC credited to new organisers on their first tournament creation (if bonus is enabled).",
    )

    # ════════════════════════════════════════════════════════════════
    # SECTION 3 — REGULAR USER RESTRICTIONS
    # ════════════════════════════════════════════════════════════════

    # Official tag / badge
    user_can_create_official = models.BooleanField(
        default=False,
        verbose_name="Regular Users Can Mark as Official",
        help_text=(
            "Allow regular (non-staff) users to tick the 'Official Tournament' checkbox. "
            "Keep OFF to reserve the Official badge for staff-created events."
        ),
    )

    # Featured listing
    user_can_feature_tournament = models.BooleanField(
        default=False,
        verbose_name="Regular Users Can Feature Their Tournament",
        help_text="Allow regular users to set is_featured=True on their tournaments.",
    )

    # DeltaCoin prize pool
    user_can_set_deltacoin_prize = models.BooleanField(
        default=True,
        verbose_name="Regular Users Can Set a DeltaCoin Prize Pool",
        help_text=(
            "Allow regular organisers to add a DC prize pool to their tournament. "
            "Turn OFF to reserve prize-pool tournaments for official events."
        ),
    )
    user_max_deltacoin_prize = models.PositiveIntegerField(
        default=0,
        verbose_name="Max DeltaCoin Prize Pool for Regular Users",
        help_text="Cap on DC prize pool for non-staff organisers. 0 = unlimited.",
    )

    # Participant cap
    user_max_participants = models.PositiveIntegerField(
        default=0,
        verbose_name="Max Participants Cap (Regular Users)",
        help_text=(
            "Hard cap on max_participants for non-staff tournament creation. "
            "0 = no cap (unlimited). e.g. 128 to cap community events."
        ),
    )

    # Concurrent tournaments
    user_max_active_tournaments = models.PositiveIntegerField(
        default=3,
        verbose_name="Max Active Tournaments Per User",
        help_text=(
            "Max number of non-completed, non-cancelled tournaments a regular user "
            "can have at once. 0 = unlimited."
        ),
    )

    # Allowed formats
    user_allowed_formats_json = models.TextField(
        blank=True,
        default='["single_elimination","double_elimination","round_robin","swiss","group_playoff"]',
        verbose_name="Allowed Formats for Regular Users (JSON list)",
        help_text=(
            'JSON list of allowed format values. e.g. ["single_elimination","round_robin"]. '
            'Leave as full list to allow all formats. '
            'Available: single_elimination, double_elimination, round_robin, swiss, group_playoff.'
        ),
    )

    # Entry fee in real currency
    user_can_charge_entry_fee = models.BooleanField(
        default=True,
        verbose_name="Regular Users Can Charge Real-Money Entry Fee",
        help_text="Allow non-staff organisers to set a real-currency entry fee (bKash, Nagad, etc.).",
    )

    # ════════════════════════════════════════════════════════════════
    # SECTION 4 — STAFF / OFFICIAL PRIVILEGES
    # ════════════════════════════════════════════════════════════════

    staff_can_waive_fee = models.BooleanField(
        default=True,
        verbose_name="Staff Can Waive Fee for Any User",
        help_text="Allow staff to manually grant a free hosting pass to a specific user.",
    )
    official_tournaments_require_staff = models.BooleanField(
        default=True,
        verbose_name="Official Tournaments Require Staff Account",
        help_text=(
            "Enforce that only staff/superuser accounts can publish under the "
            "'Official Tournament' badge. Mirrors user_can_create_official."
        ),
    )
    staff_max_slots_override = models.PositiveIntegerField(
        default=0,
        verbose_name="Staff Slot Override (0 = unlimited)",
        help_text="Max participants staff accounts can set. 0 = no limit.",
    )

    # ════════════════════════════════════════════════════════════════
    # SECTION 5 — ORGANISER ACCESS
    # ════════════════════════════════════════════════════════════════

    organizer_access_days = models.PositiveIntegerField(
        default=90,
        validators=[MinValueValidator(1)],
        verbose_name="Organiser TOC Access Duration (days)",
        help_text=(
            "Days after tournament end that the organiser retains full TOC access. "
            "After this, the console switches to read-only mode."
        ),
    )

    # ════════════════════════════════════════════════════════════════
    # SECTION 6 — PRICING TIER LABELS (marketing / display only)
    # ════════════════════════════════════════════════════════════════

    tier_free_label       = models.CharField(max_length=64, default="Starter", blank=True)
    tier_free_description = models.TextField(
        default="Community tournament — up to 32 slots, basic bracket, public listing.",
        blank=True,
    )
    tier_standard_label       = models.CharField(max_length=64, default="Standard", blank=True)
    tier_standard_description = models.TextField(
        default="Up to 128 slots, all formats, prize pool support, custom branding & 90-day TOC access.",
        blank=True,
    )
    tier_premium_label       = models.CharField(max_length=64, default="Premium", blank=True)
    tier_premium_description = models.TextField(
        default="Unlimited slots, featured listing, dedicated support, sponsor integration.",
        blank=True,
    )
    tier_premium_dc = models.PositiveIntegerField(
        default=2000,
        verbose_name="Premium Tier Fee (DC) — display only",
        help_text="Future premium tier price — not yet enforced.",
    )

    # ════════════════════════════════════════════════════════════════
    # SECTION 7 — AUDIT
    # ════════════════════════════════════════════════════════════════

    admin_notes = models.TextField(
        blank=True,
        verbose_name="Admin Notes (internal)",
        help_text="Never shown to users.",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "accounts.User",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Last Updated By",
    )

    # ════════════════════════════════════════════════════════════════
    # Meta
    # ════════════════════════════════════════════════════════════════

    class Meta:
        app_label = "tournaments"
        verbose_name = "Hosting & Pricing Configuration"
        verbose_name_plural = "Hosting & Pricing Configuration"

    def __str__(self):
        fee = self.effective_fee()
        promo = f" | Promo: {self.get_active_promo_display()}" if self.active_promo != PromoType.NONE else ""
        return f"Hosting Config — {fee} DC base{promo}"

    # ────────────────────────────────────────────────────────────────
    # Singleton enforcement
    # ────────────────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        if not self.pk and TournamentHostingConfig.objects.exists():
            raise ValidationError(
                "Only one Hosting & Pricing Configuration record is allowed. "
                "Edit the existing one."
            )
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls) -> "TournamentHostingConfig":
        """Return the single config row, creating defaults if absent."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    # ────────────────────────────────────────────────────────────────
    # Fee / promo logic
    # ────────────────────────────────────────────────────────────────

    def effective_fee(self) -> int:
        """
        Return the base hosting fee (DC).
        0  = free (fee disabled or always-free promo).

        Note: promo eligibility per-user/per-tournament is checked in
        get_hosting_fee_for_user() below.
        """
        if not self.hosting_fee_enabled:
            return 0
        if self.active_promo == PromoType.ALWAYS_FREE:
            return 0
        return self.hosting_fee_dc

    def is_promo_active(self) -> bool:
        """Return True if any promotion is currently active."""
        if self.active_promo == PromoType.NONE:
            return False
        if self.active_promo == PromoType.ALWAYS_FREE:
            return True
        if self.active_promo == PromoType.TIME_BASED:
            return bool(self.promo_free_until and timezone.now() < self.promo_free_until)
        if self.active_promo == PromoType.FIRST_N_USERS:
            return self.promo_first_n_users_used < self.promo_first_n_users_limit
        if self.active_promo == PromoType.FIRST_N_TOURNAMENTS:
            return self.promo_first_n_tournaments_used < self.promo_first_n_tournaments_limit
        return False

    def get_hosting_fee_for_user(self, user) -> int:
        """
        Full fee calculation for a specific user taking all promos into account.

        Returns:
            int: DC amount the user must pay (0 = free).
        """
        if not self.hosting_fee_enabled:
            return 0

        # Staff bypass
        if self.staff_bypass_enabled and (user.is_staff or user.is_superuser):
            return 0

        # Always-free promo
        if self.active_promo == PromoType.ALWAYS_FREE:
            return 0

        # Time-based promo
        if self.active_promo == PromoType.TIME_BASED:
            if self.promo_free_until and timezone.now() < self.promo_free_until:
                return 0

        # First-N users promo
        if self.active_promo == PromoType.FIRST_N_USERS:
            if self.promo_first_n_users_used < self.promo_first_n_users_limit:
                return 0  # caller must call consume_promo_slot() after creating

        # First-N tournaments promo
        if self.active_promo == PromoType.FIRST_N_TOURNAMENTS:
            if self.promo_first_n_tournaments_used < self.promo_first_n_tournaments_limit:
                return 0

        return self.hosting_fee_dc

    def consume_promo_slot(self) -> bool:
        """
        Atomically increment the promo usage counter for first-N promos.
        Call this AFTER a tournament is successfully created.
        Returns True if a slot was consumed.
        """
        if self.active_promo == PromoType.FIRST_N_USERS:
            updated = TournamentHostingConfig.objects.filter(
                pk=self.pk,
                promo_first_n_users_used__lt=models.F("promo_first_n_users_limit"),
            ).update(promo_first_n_users_used=models.F("promo_first_n_users_used") + 1)
            return bool(updated)

        if self.active_promo == PromoType.FIRST_N_TOURNAMENTS:
            updated = TournamentHostingConfig.objects.filter(
                pk=self.pk,
                promo_first_n_tournaments_used__lt=models.F("promo_first_n_tournaments_limit"),
            ).update(promo_first_n_tournaments_used=models.F("promo_first_n_tournaments_used") + 1)
            return bool(updated)

        return False

    def get_allowed_formats(self) -> list:
        """Parse and return the allowed formats list for regular users."""
        try:
            return json.loads(self.user_allowed_formats_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def promo_slots_remaining(self) -> int | None:
        """Return remaining promo slots, or None if not applicable."""
        if self.active_promo == PromoType.FIRST_N_USERS:
            return max(0, self.promo_first_n_users_limit - self.promo_first_n_users_used)
        if self.active_promo == PromoType.FIRST_N_TOURNAMENTS:
            return max(0, self.promo_first_n_tournaments_limit - self.promo_first_n_tournaments_used)
        return None
