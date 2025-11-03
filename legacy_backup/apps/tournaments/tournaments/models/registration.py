# apps/tournaments/models/registration.py
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils import timezone


class Registration(models.Model):
    # Parent
    tournament = models.ForeignKey("Tournament", on_delete=models.CASCADE, related_name="registrations")

    # Either solo user OR team
    user = models.ForeignKey(
        "user_profile.UserProfile",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="solo_registrations",
    )
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="team_registrations",
    )

    # Payment info
    payment_method = models.CharField(max_length=32, blank=True, default="")
    payment_sender = models.CharField(max_length=64, blank=True, default="")
    payment_reference = models.CharField("Transaction ID", max_length=64, blank=True, default="")
    payment_status = models.CharField(
        max_length=16,
        choices=[("pending", "Pending"), ("verified", "Verified"), ("rejected", "Rejected")],
        default="pending",
    )

    # Registration status
    status = models.CharField(
        max_length=16,
        choices=[("PENDING", "Pending"), ("CONFIRMED", "Confirmed"), ("CANCELLED", "Cancelled")],
        default="PENDING",
    )

    # Ops verification
    payment_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    payment_verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tournament", "status"]),
            models.Index(fields=["payment_status"]),
        ]
        # Prevent duplicate registrations at the DB level (solo or team)
        constraints = [
            # Unique (tournament, user) when user is set
            UniqueConstraint(
                fields=["tournament", "user"],
                condition=Q(user__isnull=False),
                name="uq_registration_tournament_user_not_null",
            ),
            # Unique (tournament, team) when team is set
            UniqueConstraint(
                fields=["tournament", "team"],
                condition=Q(team__isnull=False),
                name="uq_registration_tournament_team_not_null",
            ),
        ]

    def __str__(self):
        who = getattr(self.user, "display_name", None) or getattr(self.team, "tag", None) or "Reg"
        return f"{who} → {getattr(self.tournament, 'name', '')}"

    def clean(self):
        # Must have either user OR team
        if not self.user and not self.team:
            raise ValidationError("Registration must have either a user or a team.")
        if self.user and self.team:
            raise ValidationError("Registration cannot have both a user and a team.")

        # No duplicate registrations for the same tournament
        try:
            if self.user_id:
                exists = (
                    Registration.objects.filter(
                        tournament=self.tournament, user_id=self.user_id
                    )
                    .exclude(pk=self.pk)
                    .exists()
                )
                if exists:
                    raise ValidationError({
                        "user": "You are already registered for this tournament."
                    })
            if self.team_id:
                exists = (
                    Registration.objects.filter(
                        tournament=self.tournament, team_id=self.team_id
                    )
                    .exclude(pk=self.pk)
                    .exists()
                )
                if exists:
                    raise ValidationError({
                        "team": "This team is already registered for this tournament."
                    })
        except ValidationError:
            raise
        except Exception:
            # Fail-soft: rely on DB constraints if available
            pass
