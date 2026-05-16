"""
Canonical Team HQ training models.

These models represent non-reward team operations. They intentionally do not
store DeltaCoin, escrow, payout, or settlement fields.
"""

from django.conf import settings
from django.db import models


class TrainingVisibility(models.TextChoices):
    TEAM_ONLY = "TEAM_ONLY", "Team only"
    PUBLIC = "PUBLIC", "Public"
    UNLISTED = "UNLISTED", "Unlisted"


class ScrimRequest(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        ACCEPTED = "ACCEPTED", "Accepted"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    class Format(models.TextChoices):
        BO1 = "BO1", "Best of 1"
        BO3 = "BO3", "Best of 3"
        BO5 = "BO5", "Best of 5"
        CUSTOM = "CUSTOM", "Custom"

    requesting_team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.CASCADE,
        related_name="scrim_requests",
    )
    accepted_team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_scrim_requests",
    )
    game = models.ForeignKey(
        "games.Game",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="scrim_requests",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_scrim_requests",
    )
    title = models.CharField(max_length=120, blank=True)
    format = models.CharField(max_length=12, choices=Format.choices, default=Format.BO3)
    skill_level = models.CharField(max_length=80, blank=True)
    server_region = models.CharField(max_length=80, blank=True)
    scheduled_at = models.DateTimeField(db_index=True)
    visibility = models.CharField(
        max_length=16,
        choices=TrainingVisibility.choices,
        default=TrainingVisibility.PUBLIC,
        db_index=True,
    )
    notes = models.TextField(blank=True, max_length=1200)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations_scrim_request"
        ordering = ["-scheduled_at", "-created_at"]
        indexes = [
            models.Index(fields=["requesting_team", "status"], name="scrim_req_team_status_idx"),
            models.Index(fields=["game", "status", "scheduled_at"], name="scrim_req_game_status_idx"),
        ]

    def __str__(self):
        return f"{self.requesting_team} scrim ({self.status})"


class ScrimBooking(models.Model):
    class Status(models.TextChoices):
        ACCEPTED = "ACCEPTED", "Accepted"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    scrim_request = models.OneToOneField(
        ScrimRequest,
        on_delete=models.CASCADE,
        related_name="booking",
    )
    requesting_team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.CASCADE,
        related_name="home_scrim_bookings",
    )
    accepted_team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.CASCADE,
        related_name="away_scrim_bookings",
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_scrim_bookings",
    )
    scheduled_at = models.DateTimeField(db_index=True)
    room_details = models.TextField(blank=True, max_length=1000)
    match = models.ForeignKey(
        "tournaments.Match",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="training_scrim_bookings",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACCEPTED,
        db_index=True,
    )
    result_notes = models.TextField(blank=True, max_length=1200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations_scrim_booking"
        ordering = ["-scheduled_at", "-created_at"]
        indexes = [
            models.Index(fields=["requesting_team", "status"], name="scrim_booking_home_idx"),
            models.Index(fields=["accepted_team", "status"], name="scrim_booking_away_idx"),
        ]

    def __str__(self):
        return f"{self.requesting_team} vs {self.accepted_team}"


class TryoutApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        REVIEWING = "REVIEWING", "Reviewing"
        INVITED = "INVITED", "Invited"
        SCHEDULED = "SCHEDULED", "Scheduled"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        OBSERVATION = "OBSERVATION", "Observation"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.CASCADE,
        related_name="tryout_applications",
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tryout_applications",
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_tryout_invites",
    )
    game = models.ForeignKey(
        "games.Game",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tryout_applications",
    )
    ign = models.CharField(max_length=100, blank=True)
    preferred_role = models.CharField(max_length=80, blank=True)
    rank_tier = models.CharField(max_length=80, blank=True)
    availability = models.CharField(max_length=240, blank=True)
    profile_links = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True, max_length=1200)
    review_notes = models.TextField(blank=True, max_length=1600)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_tryout_applications",
    )
    join_request = models.ForeignKey(
        "organizations.TeamJoinRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tryout_applications",
        help_text="Roster pipeline item created or linked when a tryout becomes a join offer.",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations_tryout_application"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "applicant"],
                condition=models.Q(status__in=["PENDING", "REVIEWING", "INVITED", "SCHEDULED", "OBSERVATION"]),
                name="unique_active_tryout_application",
            ),
        ]

    def __str__(self):
        return f"{self.applicant} -> {self.team} ({self.status})"


class TryoutSession(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    application = models.ForeignKey(
        TryoutApplication,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.CASCADE,
        related_name="tryout_sessions",
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tryout_sessions",
    )
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheduled_tryout_sessions",
    )
    scheduled_at = models.DateTimeField(db_index=True)
    format = models.CharField(max_length=80, blank=True)
    room_details = models.TextField(blank=True, max_length=1000)
    match = models.ForeignKey(
        "tournaments.Match",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="training_tryout_sessions",
    )
    review_notes = models.TextField(blank=True, max_length=1600)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations_tryout_session"
        ordering = ["-scheduled_at", "-created_at"]

    def __str__(self):
        return f"Tryout: {self.applicant} with {self.team}"


class PracticeSession(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.CASCADE,
        related_name="practice_sessions",
    )
    game = models.ForeignKey(
        "games.Game",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="practice_sessions",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_practice_sessions",
    )
    title = models.CharField(max_length=140)
    session_type = models.CharField(max_length=40, default="PRACTICE")
    scheduled_at = models.DateTimeField(db_index=True)
    duration_minutes = models.PositiveSmallIntegerField(default=60)
    focus = models.CharField(max_length=160, blank=True)
    goals = models.TextField(blank=True, max_length=1200)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="practice_session_assignments",
    )
    match = models.ForeignKey(
        "tournaments.Match",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="training_practice_sessions",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True,
    )
    notes = models.TextField(blank=True, max_length=1600)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations_practice_session"
        ordering = ["-scheduled_at", "-created_at"]
        indexes = [
            models.Index(fields=["team", "status", "scheduled_at"], name="practice_team_status_idx"),
        ]

    def __str__(self):
        return f"{self.team}: {self.title}"


class VodReview(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        REVIEWED = "REVIEWED", "Reviewed"
        ARCHIVED = "ARCHIVED", "Archived"

    team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.CASCADE,
        related_name="vod_reviews",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vod_reviews_authored",
    )
    assigned_players = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="assigned_vod_reviews",
    )
    title = models.CharField(max_length=160)
    external_url = models.URLField(max_length=500)
    category = models.CharField(max_length=40, default="analysis")
    notes = models.TextField(blank=True, max_length=2400)
    linked_match = models.ForeignKey(
        "tournaments.Match",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="training_vod_reviews",
    )
    visibility = models.CharField(
        max_length=16,
        choices=TrainingVisibility.choices,
        default=TrainingVisibility.TEAM_ONLY,
        db_index=True,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations_vod_review"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["team", "status"], name="vod_review_team_status_idx"),
        ]

    def __str__(self):
        return f"{self.team}: {self.title}"
