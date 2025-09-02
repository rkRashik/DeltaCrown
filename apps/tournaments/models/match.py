# apps/tournaments/models/match.py
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.teams.models import Team

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
