from django.contrib.auth import get_user_model
from django.db import models
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field
from django.core.exceptions import ValidationError

from apps.teams.models import Team
from django.utils import timezone


STATUS_CHOICES = [
    ("DRAFT", "Draft"),
    ("PUBLISHED", "Published"),
    ("RUNNING", "Running"),
    ("COMPLETED", "Completed"),
]

def tournament_banner_path(instance, filename):
    return f"tournaments/{instance.id}/banner/{filename}"

def rules_pdf_path(instance, filename):
    return f"tournaments/{instance.id}/rules/{filename}"

class Tournament(models.Model):
    class Game(models.TextChoices):
        VALORANT = "valorant", "Valorant"
        EFOOTBALL = "efootball", "eFootball Mobile"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open for Registration"
        ONGOING = "ongoing", "Ongoing"
        COMPLETED = "completed", "Completed"


    # Identity
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    game = models.CharField(max_length=32, blank=True, default="")
    short_description = models.CharField(max_length=280, blank=True)

    # Schedule (BST per settings)
    reg_open_at = models.DateTimeField()
    reg_close_at = models.DateTimeField()
    start_at = models.DateTimeField(null=True, blank=True)  # scheduled start time
    end_at   = models.DateTimeField()

    # Capacity & money
    slot_size = models.PositiveIntegerField()
    entry_fee_bdt = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prize_pool_bdt = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    prize_distribution_richtext = CKEditor5Field("Prize distribution", config_name="default", blank=True)

    # Media & links
    banner    = models.ImageField(upload_to=tournament_banner_path, blank=True, null=True)
    rules_pdf = models.FileField(upload_to=rules_pdf_path, blank=True, null=True)
    fb_stream = models.URLField(blank=True)
    yt_stream = models.URLField(blank=True)
    discord_link = models.URLField(blank=True)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="DRAFT")

    # Tournament-level rules/terms (rich text)
    rules_richtext = CKEditor5Field("Rules", config_name="default", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes  = [models.Index(fields=["status"]), models.Index(fields=["start_at"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name



PAYMENT_METHODS = [("bkash","bKash"),("nagad","Nagad"),("rocket","Rocket"),("bank","Bank Transfer")]
PAYMENT_STATUS  = [("pending","Pending"),("verified","Verified"),("rejected","Rejected")]

class Registration(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="registrations")

    # Either solo user OR team
    user = models.ForeignKey('user_profile.UserProfile', on_delete=models.CASCADE, null=True, blank=True, related_name="solo_registrations")
    team = models.ForeignKey(Team,        on_delete=models.CASCADE, null=True, blank=True, related_name="team_registrations")

    # Payment (manual verification MVP)
    payment_method    = models.CharField(max_length=10, choices=PAYMENT_METHODS, blank=True)
    payment_reference = models.CharField(max_length=120, blank=True)
    payment_status    = models.CharField(max_length=10, choices=PAYMENT_STATUS, default="pending")

    status = models.CharField(max_length=12, default="PENDING")  # PENDING|CONFIRMED|CHECKED_IN|WITHDRAWN
    created_at = models.DateTimeField(auto_now_add=True)

    # Extra payment capture fields
    payment_sender = models.CharField(max_length=32, blank=True, help_text="Payer account/phone")
    # payment_reference already exists (TRX ID etc.)
    payment_verified_by = models.ForeignKey(
        get_user_model(), null=True, blank=True, on_delete=models.SET_NULL, related_name="verified_registrations"
    )
    payment_verified_at = models.DateTimeField(null=True, blank=True)
    payment_note = models.TextField(blank=True)


    class Meta:
        unique_together = [("tournament","user"), ("tournament","team")]
        indexes = [
            models.Index(fields=["tournament","status"]),
            models.Index(fields=["payment_status"]),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}

        # XOR: exactly one of (user, team) must be set (not both, not neither)
        if bool(self.user_id) == bool(self.team_id):
            errors["user"] = "Select a user OR a team (not both)."
            errors["team"] = "Select a user OR a team (not both)."

        # Manual payment requirements for paid tournaments
        fee = self.tournament.entry_fee_bdt or 0
        pm = (self.payment_method or "").strip().lower()
        ref = (self.payment_reference or "").strip()
        # sender is intentionally optional at registration time to keep team flow simple
        # (admin can ask/enter it during verification)
        # snd = (self.payment_sender or "").strip()

        if fee and fee > 0:
            if not pm:
                errors["payment_method"] = "Select a payment method."
            if not ref:
                errors["payment_reference"] = "Enter the transaction/reference ID."
            # NOTE: Do NOT require payment_sender here. It’s optional at registration time.

        if errors:
            raise ValidationError(errors)


    def __str__(self):
        who = self.user.display_name if self.user_id else (self.team.tag if self.team_id else "Unknown")
        return f"{who} @ {self.tournament.name}"



class Bracket(models.Model):
    tournament = models.OneToOneField(Tournament, on_delete=models.CASCADE, related_name="bracket")
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bracket for {self.tournament.name}"

class Match(models.Model):
    STATE = [("SCHEDULED", "Scheduled"), ("REPORTED", "Reported"), ("VERIFIED", "Verified")]

    tournament = models.ForeignKey("Tournament", on_delete=models.CASCADE, related_name="matches")
    round_no = models.PositiveIntegerField()
    position = models.PositiveIntegerField(help_text="1-based index within round")

    # per-game
    best_of = models.PositiveIntegerField(default=1)

    # Side A
    user_a = models.ForeignKey('user_profile.UserProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name="matches_as_user_a")
    team_a = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL, related_name="matches_as_team_a")

    # Side B
    user_b = models.ForeignKey('user_profile.UserProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name="matches_as_user_b")
    team_b = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL, related_name="matches_as_team_b")

    score_a = models.PositiveIntegerField(default=0)
    score_b = models.PositiveIntegerField(default=0)

    # scheduled start time for this match
    start_at = models.DateTimeField(null=True, blank=True)

    # typed winner
    winner_user = models.ForeignKey('user_profile.UserProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name="wins_as_user")
    winner_team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL, related_name="wins_as_team")

    state = models.CharField(max_length=10, choices=STATE, default="SCHEDULED")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tournament", "round_no", "position")
        indexes = [models.Index(fields=["tournament", "round_no", "position"])]

    @property
    def is_team_match(self):
        return (self.team_a_id or self.team_b_id) and not (self.user_a_id or self.user_b_id)

    @property
    def is_solo_match(self):
        return (self.user_a_id or self.user_b_id) and not (self.team_a_id or self.team_b_id)

    def clean(self):
        # exactly one participant type per side
        if (self.user_a and self.team_a) or (self.user_b and self.team_b):
            raise ValidationError("Each side must be either a user or a team, not both.")
        if not ((self.user_a or self.team_a) and (self.user_b or self.team_b)):
            raise ValidationError("Both sides must be set.")
        # consistent type across sides
        if (self.user_a or self.user_b) and (self.team_a or self.team_b):
            raise ValidationError("Match must be solo-vs-solo OR team-vs-team.")

    def set_winner_by_scores(self):
        if self.score_a == self.score_b:
            raise ValidationError("No draws allowed.")
        if self.is_solo_match:
            self.winner_user = self.user_a if self.score_a > self.score_b else self.user_b
            self.winner_team = None
        else:
            self.winner_team = self.team_a if self.score_a > self.score_b else self.team_b
            self.winner_user = None
        self.state = "REPORTED"

    def set_winner_side(self, side: str):
        if side not in ("a", "b"):
            raise ValidationError("side must be 'a' or 'b'")
        if self.is_solo_match:
            self.winner_user = self.user_a if side == "a" else self.user_b
            self.winner_team = None
        else:
            self.winner_team = self.team_a if side == "a" else self.team_b
            self.winner_user = None
        self.state = "VERIFIED"


class BracketVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    CAPTAINS = "captains", "Team Captains Only"

def rules_upload_path(instance, filename):
    return f"tournaments/{instance.tournament_id}/rules/{filename}"

class TournamentSettings(models.Model):
    tournament = models.OneToOneField(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="settings",
    )
    round_duration_mins = models.PositiveIntegerField(default=45)  # each round duration
    round_gap_mins = models.PositiveIntegerField(default=10)  # gap between rounds

    # Toggles / options (generic across games)
    invite_only = models.BooleanField(default=False)
    auto_check_in = models.BooleanField(default=False)
    allow_substitutes = models.BooleanField(default=False)
    custom_format_enabled = models.BooleanField(default=False)
    automatic_scheduling_enabled = models.BooleanField(default=False)

    # Visibility & region
    bracket_visibility = models.CharField(
        max_length=16, choices=BracketVisibility.choices, default=BracketVisibility.PUBLIC
    )
    region_lock = models.CharField(
        max_length=64, blank=True,
        help_text="Optional region code/name to restrict participation (e.g., 'Bangladesh' or 'ASIA')."
    )

    # Check-in window (minutes relative to match start)
    check_in_open_mins = models.PositiveIntegerField(default=60, help_text="Open before start (minutes)")
    check_in_close_mins = models.PositiveIntegerField(default=15, help_text="Close before start (minutes)")

    # Media & rules
    rules_pdf = models.FileField(upload_to=rules_upload_path, blank=True, null=True)
    facebook_stream_url = models.URLField(blank=True)
    youtube_stream_url = models.URLField(blank=True)
    discord_link = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Payment receiving numbers the organizer sets per tournament
    bkash_receive_number = models.CharField(max_length=20, blank=True, help_text="Organizer bKash number")
    nagad_receive_number = models.CharField(max_length=20, blank=True, help_text="Organizer Nagad number")
    rocket_receive_number = models.CharField(max_length=20, blank=True, help_text="Organizer Rocket number")
    bank_instructions = models.TextField(blank=True, help_text="Bank account details or instructions (optional)")


    def __str__(self):
        return f"Settings for {self.tournament}"


# --- Match timeline & disputes -------------------------------------------------

class MatchEvent(models.Model):
    KIND = [
        ("REPORT", "Report submitted"),
        ("CONFIRM", "Opponent confirmed"),
        ("DISPUTE_OPENED", "Dispute opened"),
        ("DISPUTE_RESOLVED", "Dispute resolved"),
        ("COMMENT", "Comment"),
    ]
    match = models.ForeignKey("Match", on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey('user_profile.UserProfile', on_delete=models.SET_NULL, null=True, blank=True)
    kind = models.CharField(max_length=20, choices=KIND)
    note = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["match", "created_at"])]

    def __str__(self):
        return f"{self.get_kind_display()} on match #{self.match_id}"


class MatchDispute(models.Model):
    RESOLUTION = [
        ("KEEP_REPORTED", "Keep reported result"),
        ("SET_WINNER_A", "Set winner: Side A"),
        ("SET_WINNER_B", "Set winner: Side B"),
        ("VOID", "Void match"),
    ]
    match = models.OneToOneField("Match", on_delete=models.CASCADE, related_name="dispute", null=True, blank=True)
    opened_by = models.ForeignKey('user_profile.UserProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name="disputes_opened")
    reason = models.TextField()
    is_open = models.BooleanField(default=True)
    resolved_by = models.ForeignKey('user_profile.UserProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name="disputes_resolved")
    resolution = models.CharField(max_length=20, choices=RESOLUTION, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        state = "OPEN" if self.is_open else "RESOLVED"
        return f"Dispute {state} for match #{getattr(self.match,'id',None)}"
