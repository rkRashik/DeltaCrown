# apps/tournaments/models/userprefs.py
from __future__ import annotations

import secrets
from datetime import datetime
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower

User = get_user_model()

class CalendarFeedToken(models.Model):
    """
    One token per user to generate a private ICS feed URL for "My Matches".
    Safe to expose as a long random string; user can rotate by deleting row.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="calendar_feed_token")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def issue_for(user: User) -> "CalendarFeedToken":
        obj, _ = CalendarFeedToken.objects.get_or_create(
            user=user,
            defaults={"token": secrets.token_urlsafe(32)},
        )
        return obj


class SavedMatchFilter(models.Model):
    """
    Per-user saved filter for My Matches. A single 'is_default' allowed.
    """
    STATE_CHOICES = [
        ("", "Any"),
        ("scheduled", "Scheduled"),
        ("reported", "Reported"),
        ("verified", "Verified"),
        ("live", "Live"),
        ("completed", "Completed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_match_filters")
    name = models.CharField(max_length=48, default="Default")
    is_default = models.BooleanField(default=False)

    # Filter fields (all optional)
    game = models.CharField(max_length=20, blank=True)        # 'efootball'|'valorant'|''
    state = models.CharField(max_length=20, blank=True, choices=STATE_CHOICES)
    tournament_id = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    start_date = models.DateField(null=True, blank=True)      # inclusive
    end_date = models.DateField(null=True, blank=True)        # inclusive

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["user", "name"], name="uq_saved_match_filter_user_name"),
        ]


class PinnedTournament(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pinned_tournaments")
    # FK kept as IntegerField to avoid tight coupling; optionally change to FK later.
    tournament_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["user", "tournament_id"], name="uq_pin_user_tournament"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} → {self.tournament_id}"
