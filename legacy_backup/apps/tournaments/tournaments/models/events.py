# apps/tournaments/models/events.py
from django.db import models

class MatchEvent(models.Model):
    match = models.ForeignKey("Match", on_delete=models.CASCADE, related_name="events")
    type = models.CharField(max_length=32)
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["match", "created_at"]),
            models.Index(fields=["type"]),
        ]

    def __str__(self):
        return f"Event {self.type} on match #{self.match_id}"


class MatchComment(models.Model):
    match = models.ForeignKey("Match", on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey("user_profile.UserProfile", on_delete=models.SET_NULL, null=True, blank=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["match", "created_at"])]

    def __str__(self):
        return f"Comment by {getattr(self.author, 'id', None)} on match #{self.match_id}"
