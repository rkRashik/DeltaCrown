# apps/tournaments/models/bracket.py
from django.db import models

class Bracket(models.Model):
    tournament = models.OneToOneField("Tournament", on_delete=models.CASCADE, related_name="bracket")
    is_locked = models.BooleanField(default=False)
    data = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tournament_id"]

    def __str__(self):
        return f"Bracket for {getattr(self.tournament, 'name', '')}"
