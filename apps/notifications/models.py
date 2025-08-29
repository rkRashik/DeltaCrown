from django.db import models
from apps.user_profile.models import UserProfile

class Notification(models.Model):
    class Type(models.TextChoices):
        REG_CONFIRM = "reg_confirm", "Registration confirmed"
        TEAM_INVITE = "team_invite", "Team invite"
        MATCH_SCHEDULED = "match_scheduled", "Match scheduled"
        CHECKIN_OPEN = "checkin_open", "Check-in window opened"

    recipient = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=32, choices=Type.choices)
    title = models.CharField(max_length=120)
    body = models.TextField(blank=True)
    url = models.URLField(blank=True)

    tournament = models.ForeignKey("tournaments.Tournament", null=True, blank=True, on_delete=models.CASCADE)
    match = models.ForeignKey("tournaments.Match", null=True, blank=True, on_delete=models.CASCADE)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["recipient", "is_read", "created_at"]),
            models.Index(fields=["type", "created_at"]),
        ]
        unique_together = (("recipient", "type", "match"),)

    def __str__(self):
        return f"{self.get_type_display()} → {self.recipient}"
