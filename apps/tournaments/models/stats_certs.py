"""
TOC Sprint 9 — Stats, Certificates & Trust Index Models

§9.1 CertificateTemplate  — tournament certificate HTML templates
§9.1 CertificateRecord    — issued certificate per user
§9.3 ProfileTrophy        — trophy/achievement definitions
§9.3 UserTrophy           — trophy awarded to user  
§9.5 TrustEvent           — trust index events (+/- delta)
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


# ---------------------------------------------------------------------------
# S9-M1: CertificateTemplate
# ---------------------------------------------------------------------------

class CertificateTemplate(models.Model):
    """
    HTML-based certificate template for a tournament.
    Variables like {{player_name}}, {{placement}}, {{tournament_name}}
    are replaced at generation time.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="certificate_templates",
        verbose_name=_("Tournament"),
    )
    name = models.CharField(max_length=200, verbose_name=_("Template Name"))
    template_html = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Template HTML"),
        help_text=_("HTML with {{variable}} placeholders."),
    )
    variables = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Available Variables"),
        help_text=_("List of variable names available for substitution."),
    )
    is_default = models.BooleanField(default=False, verbose_name=_("Default Template"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "toc_certificate_template"
        verbose_name = _("Certificate Template")
        verbose_name_plural = _("Certificate Templates")
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.name} — {self.tournament}"


# ---------------------------------------------------------------------------
# S9-M2: CertificateRecord
# ---------------------------------------------------------------------------

class CertificateRecord(models.Model):
    """
    Issued certificate for a user in a tournament.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="certificate_records",
        verbose_name=_("User"),
    )
    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="certificate_records",
        verbose_name=_("Tournament"),
    )
    template = models.ForeignKey(
        CertificateTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="records",
        verbose_name=_("Template"),
    )
    rendered_html = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Rendered HTML"),
    )
    generated_pdf = models.FileField(
        upload_to="certificates/",
        blank=True,
        null=True,
        verbose_name=_("Generated PDF"),
    )
    context_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Context Data"),
        help_text=_("Snapshot of variables used for rendering."),
    )
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "toc_certificate_record"
        verbose_name = _("Certificate Record")
        verbose_name_plural = _("Certificate Records")
        ordering = ["-issued_at"]
        unique_together = [("user", "tournament", "template")]

    def __str__(self):
        return f"Certificate {self.user} — {self.tournament}"


# ---------------------------------------------------------------------------
# S9-M3: ProfileTrophy
# ---------------------------------------------------------------------------

class ProfileTrophy(models.Model):
    """
    Trophy/achievement definition — awardable to users.
    """

    class Rarity(models.TextChoices):
        COMMON = "common", _("Common")
        UNCOMMON = "uncommon", _("Uncommon")
        RARE = "rare", _("Rare")
        EPIC = "epic", _("Epic")
        LEGENDARY = "legendary", _("Legendary")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=150, unique=True, verbose_name=_("Name"))
    icon = models.CharField(
        max_length=100,
        blank=True,
        default="trophy",
        verbose_name=_("Icon"),
        help_text=_("Lucide icon name or URL."),
    )
    description = models.TextField(blank=True, default="", verbose_name=_("Description"))
    criteria = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Criteria"),
        help_text=_("Auto-award criteria (e.g. {type: 'wins', threshold: 10})."),
    )
    rarity = models.CharField(
        max_length=20,
        choices=Rarity.choices,
        default=Rarity.COMMON,
        verbose_name=_("Rarity"),
    )

    class Meta:
        db_table = "toc_profile_trophy"
        verbose_name = _("Profile Trophy")
        verbose_name_plural = _("Profile Trophies")
        ordering = ["name"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# S9-M4: UserTrophy
# ---------------------------------------------------------------------------

class UserTrophy(models.Model):
    """
    Trophy awarded to a specific user, optionally tied to a tournament.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trophies",
        verbose_name=_("User"),
    )
    trophy = models.ForeignKey(
        ProfileTrophy,
        on_delete=models.CASCADE,
        related_name="awards",
        verbose_name=_("Trophy"),
    )
    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_trophies",
        verbose_name=_("Tournament"),
    )
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "toc_user_trophy"
        verbose_name = _("User Trophy")
        verbose_name_plural = _("User Trophies")
        ordering = ["-earned_at"]
        unique_together = [("user", "trophy", "tournament")]

    def __str__(self):
        return f"{self.user} — {self.trophy.name}"


# ---------------------------------------------------------------------------
# S9-M5: TrustEvent
# ---------------------------------------------------------------------------

class TrustEvent(models.Model):
    """
    Player Trust Index event — tracks positive/negative trust changes.
    """

    class EventType(models.TextChoices):
        MATCH_PLAYED = "match_played", _("Match Played")
        MATCH_WON = "match_won", _("Match Won")
        FORFEIT = "forfeit", _("Forfeit")
        NO_SHOW = "no_show", _("No Show")
        DISPUTE_FILED = "dispute_filed", _("Dispute Filed")
        DISPUTE_LOST = "dispute_lost", _("Dispute Lost")
        DISPUTE_WON = "dispute_won", _("Dispute Won")
        CHEATING = "cheating", _("Cheating Confirmed")
        GOOD_CONDUCT = "good_conduct", _("Good Conduct")
        MANUAL = "manual", _("Manual Adjustment")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trust_events",
        verbose_name=_("User"),
    )
    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices,
        verbose_name=_("Event Type"),
    )
    delta = models.IntegerField(
        default=0,
        verbose_name=_("Delta"),
        help_text=_("Positive = trust increase, negative = decrease."),
    )
    reason = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Reason"),
    )
    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trust_events",
        verbose_name=_("Tournament"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "toc_trust_event"
        verbose_name = _("Trust Event")
        verbose_name_plural = _("Trust Events")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        sign = "+" if self.delta >= 0 else ""
        return f"{self.user} {sign}{self.delta} ({self.event_type})"
