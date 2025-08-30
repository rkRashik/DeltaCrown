from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        REG_CONFIRMED    = "reg_confirmed",    "Registration confirmed"
        BRACKET_READY    = "bracket_ready",    "Bracket generated"
        MATCH_SCHEDULED  = "match_scheduled",  "Match scheduled"
        RESULT_VERIFIED  = "result_verified",  "Result verified"
        PAYMENT_VERIFIED = "payment_verified", "Payment verified"
        CHECKIN_OPEN     = "checkin_open",     "Check-in window open"

    # Who receives
    recipient = models.ForeignKey(
        "user_profile.UserProfile",
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    # What happened (now lower-case values)
    type  = models.CharField(max_length=40, choices=Type.choices, db_index=True)
    title = models.CharField(max_length=140)
    body  = models.TextField(blank=True)

    # Optional deep link
    url = models.CharField(max_length=300, blank=True)

    # Optional associations for filtering/dedup
    tournament = models.ForeignKey(
        "tournaments.Tournament", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="notifications"
    )
    match = models.ForeignKey(
        "tournaments.Match", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="notifications"
    )

    # Read state & timestamps
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["recipient", "is_read", "created_at"]),
            models.Index(fields=["recipient", "type", "tournament", "match"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_type_display()} → {self.recipient}"

    @staticmethod
    def _normalize_type(value: str) -> str:
        # Accept enum values or arbitrary strings; store lower-case
        return (str(value) if value is not None else "").lower()

    @classmethod
    def notify_once(
        cls, *, recipient, type=None, title="", body="", url="",
        tournament=None, match=None, verb=None
    ):
        """
        Idempotent create based on (recipient, type, tournament, match).
        Accepts legacy `verb` and maps to `type`. Always stores lower-case.
        """
        raw_type = type or verb
        norm = cls._normalize_type(raw_type)
        if not norm:
            raise ValueError("Notification.notify_once requires `type` or `verb`.")

        exists = cls.objects.filter(
            recipient=recipient, type=norm,
            tournament=tournament, match=match
        ).exists()
        if exists:
            return None

        return cls.objects.create(
            recipient=recipient,
            type=norm,
            title=title or "",
            body=body or "",
            url=url or "",
            tournament=tournament,
            match=match,
        )
