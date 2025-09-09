from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta
import secrets

class EmailOTP(models.Model):
    PURPOSE_CHOICES = (("signup", "signup"),)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=16, choices=PURPOSE_CHOICES, default="signup")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    is_used = models.BooleanField(default=False)

    @classmethod
    def create_for_user(cls, user, minutes=10):
        code = f"{secrets.randbelow(10**6):06d}"
        now = timezone.now()
        return cls.objects.create(
            user=user,
            code=code,
            expires_at=now + timedelta(minutes=minutes),
        )

    def verify(self, code: str) -> bool:
        self.attempts += 1
        self.save(update_fields=["attempts"])
        if self.is_used or timezone.now() > self.expires_at:
            return False
        if code == self.code:
            self.is_used = True
            self.save(update_fields=["is_used"])
            return True
        return False
