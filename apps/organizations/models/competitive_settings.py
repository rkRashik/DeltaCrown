"""
Team-level competitive policy settings.

These settings control who can start reward-backed competitive operations for
a team and which guardrails apply before escrow-sensitive services run.
"""

from django.db import models


class TeamCompetitiveSettings(models.Model):
    class AuthorityPolicy(models.TextChoices):
        OWNER_MANAGER = "owner_manager", "Owner / Manager"
        OWNER_MANAGER_CAPTAIN = "owner_manager_captain", "Owner / Manager / Captain"

    team = models.OneToOneField(
        "organizations.Team",
        on_delete=models.CASCADE,
        related_name="competitive_settings",
    )
    showdown_create_policy = models.CharField(
        max_length=32,
        choices=AuthorityPolicy.choices,
        default=AuthorityPolicy.OWNER_MANAGER_CAPTAIN,
    )
    bounty_create_policy = models.CharField(
        max_length=32,
        choices=AuthorityPolicy.choices,
        default=AuthorityPolicy.OWNER_MANAGER_CAPTAIN,
    )
    max_showdown_entry_fee_dc = models.PositiveIntegerField(default=1000)
    max_bounty_reward_dc = models.PositiveIntegerField(default=10000)
    bounty_approval_required_above_dc = models.PositiveIntegerField(
        default=0,
        help_text="0 disables threshold blocking. Captains above this amount require manager action.",
    )
    allowed_games = models.ManyToManyField(
        "games.Game",
        blank=True,
        related_name="team_competitive_settings",
        help_text="Empty means all active competitive games are allowed.",
    )
    allow_public_scrim_availability = models.BooleanField(default=True)
    allow_public_tryout_applications = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations_team_competitive_settings"
        verbose_name = "Team Competitive Settings"
        verbose_name_plural = "Team Competitive Settings"

    def __str__(self):
        return f"Competitive settings for {self.team}"

    def captain_can_create_showdowns(self):
        return self.showdown_create_policy == self.AuthorityPolicy.OWNER_MANAGER_CAPTAIN

    def captain_can_place_bounties(self):
        return self.bounty_create_policy == self.AuthorityPolicy.OWNER_MANAGER_CAPTAIN

    def allows_game(self, game):
        if game is None:
            return True
        allowed = self.allowed_games.all()
        if not allowed.exists():
            return True
        return allowed.filter(pk=game.pk).exists()
