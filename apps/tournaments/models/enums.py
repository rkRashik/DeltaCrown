# apps/tournaments/models/enums.py
from django.db import models

class BracketVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    PARTICIPANTS = "participants", "Participants Only"
    PRIVATE = "private", "Private"
