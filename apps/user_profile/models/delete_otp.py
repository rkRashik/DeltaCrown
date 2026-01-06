# Phase 9A-27: Game Passport Delete OTP Model

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random
import string

User = get_user_model()


class GamePassportDeleteOTP(models.Model):
    """
    One-time password for confirming game passport deletion.
    High-risk action requires email verification.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='passport_delete_otps',
        help_text="User requesting deletion"
    )
    passport = models.ForeignKey(
        'user_profile.GameProfile',
        on_delete=models.CASCADE,
        related_name='delete_otps',
        help_text="Passport to be deleted"
    )
    code = models.CharField(
        max_length=6,
        help_text="6-digit OTP code"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="OTP expires 10 minutes after creation"
    )
    used = models.BooleanField(
        default=False,
        help_text="Has this OTP been used?"
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When was OTP used"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of request"
    )
    
    class Meta:
        db_table = 'user_profile_gamepassport_delete_otp'
        verbose_name = 'Game Passport Delete OTP'
        verbose_name_plural = 'Game Passport Delete OTPs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'passport', '-created_at']),
            models.Index(fields=['code', 'expires_at']),
        ]
    
    def __str__(self):
        return f"OTP for {self.user.username} - {self.passport.game} (expires {self.expires_at})"
    
    def save(self, *args, **kwargs):
        # Auto-set expiry if not provided
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Check if OTP is valid (not used, not expired)"""
        return (
            not self.used
            and timezone.now() < self.expires_at
        )
    
    def mark_used(self):
        """Mark OTP as used"""
        self.used = True
        self.used_at = timezone.now()
        self.save(update_fields=['used', 'used_at'])
    
    @classmethod
    def generate_code(cls):
        """Generate random 6-digit code"""
        return ''.join(random.choices(string.digits, k=6))
    
    @classmethod
    def create_for_passport(cls, user, passport, ip_address=None):
        """Create new OTP for passport deletion"""
        # Invalidate any existing OTPs for this passport
        cls.objects.filter(
            user=user,
            passport=passport,
            used=False
        ).update(used=True)
        
        # Generate new OTP
        code = cls.generate_code()
        otp = cls.objects.create(
            user=user,
            passport=passport,
            code=code,
            ip_address=ip_address
        )
        
        return otp
    
    @classmethod
    def verify_code(cls, user, passport, code):
        """Verify OTP code for passport deletion"""
        try:
            otp = cls.objects.get(
                user=user,
                passport=passport,
                code=code,
                used=False
            )
            
            if not otp.is_valid():
                return False, "OTP has expired. Request a new one."
            
            return True, otp
        except cls.DoesNotExist:
            return False, "Invalid OTP code."
