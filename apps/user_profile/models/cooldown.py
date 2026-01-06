# Phase 9A-27: Game Passport Cooldown System

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class GamePassportCooldown(models.Model):
    """
    Cooldown restrictions for game passport actions.
    
    Types:
    - POST_DELETE: 90-day cooldown after deleting a passport
    - IDENTITY_LOCK: 30-day lock after creating a passport (identity immutable)
    - ADMIN_OVERRIDE: Admin-imposed cooldown
    """
    
    COOLDOWN_TYPES = [
        ('POST_DELETE', 'Post-Deletion Cooldown'),
        ('IDENTITY_LOCK', 'Identity Lock'),
        ('ADMIN_OVERRIDE', 'Admin Override'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='passport_cooldowns',
        help_text="User with cooldown restriction"
    )
    game = models.ForeignKey(
        'games.Game',
        on_delete=models.CASCADE,
        related_name='passport_cooldowns',
        help_text="Game affected by cooldown"
    )
    cooldown_type = models.CharField(
        max_length=20,
        choices=COOLDOWN_TYPES,
        default='POST_DELETE',
        help_text="Type of cooldown restriction"
    )
    reason = models.TextField(
        blank=True,
        help_text="Reason for cooldown (admin notes)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="When cooldown expires"
    )
    overridden = models.BooleanField(
        default=False,
        help_text="Has this cooldown been overridden by admin?"
    )
    overridden_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='overridden_cooldowns',
        help_text="Admin who overrode cooldown"
    )
    overridden_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When was cooldown overridden"
    )
    override_reason = models.TextField(
        blank=True,
        help_text="Reason for overriding cooldown"
    )
    
    class Meta:
        db_table = 'user_profile_gamepassport_cooldown'
        verbose_name = 'Game Passport Cooldown'
        verbose_name_plural = 'Game Passport Cooldowns'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'game', '-created_at']),
            models.Index(fields=['expires_at', 'overridden']),
        ]
        # One active cooldown per user/game/type
        unique_together = ['user', 'game', 'cooldown_type']
    
    def __str__(self):
        return f"{self.user.username} - {self.game.slug} - {self.get_cooldown_type_display()} (expires {self.expires_at})"
    
    def is_active(self):
        """Check if cooldown is currently active"""
        return (
            not self.overridden
            and timezone.now() < self.expires_at
        )
    
    def days_remaining(self):
        """Calculate days remaining in cooldown"""
        if self.overridden:
            return 0
        
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)
    
    def override(self, admin_user, reason):
        """Override cooldown (admin action)"""
        self.overridden = True
        self.overridden_by = admin_user
        self.overridden_at = timezone.now()
        self.override_reason = reason
        self.save(update_fields=['overridden', 'overridden_by', 'overridden_at', 'override_reason'])
    
    @classmethod
    def create_post_delete_cooldown(cls, user, game, days=90):
        """Create 90-day cooldown after passport deletion"""
        # Remove any existing cooldown
        cls.objects.filter(
            user=user,
            game=game,
            cooldown_type='POST_DELETE'
        ).delete()
        
        cooldown = cls.objects.create(
            user=user,
            game=game,
            cooldown_type='POST_DELETE',
            reason=f"Passport deleted. Cannot re-add for {days} days.",
            expires_at=timezone.now() + timedelta(days=days)
        )
        
        return cooldown
    
    @classmethod
    def create_identity_lock(cls, user, game, days=30):
        """Create 30-day identity lock after passport creation"""
        # Remove any existing lock
        cls.objects.filter(
            user=user,
            game=game,
            cooldown_type='IDENTITY_LOCK'
        ).delete()
        
        cooldown = cls.objects.create(
            user=user,
            game=game,
            cooldown_type='IDENTITY_LOCK',
            reason=f"Identity locked for {days} days after creation.",
            expires_at=timezone.now() + timedelta(days=days)
        )
        
        return cooldown
    
    @classmethod
    def check_cooldown(cls, user, game, cooldown_type='POST_DELETE'):
        """Check if user has active cooldown for game"""
        try:
            cooldown = cls.objects.get(
                user=user,
                game=game,
                cooldown_type=cooldown_type
            )
            
            if cooldown.is_active():
                return True, cooldown
            else:
                # Expired or overridden
                return False, None
        except cls.DoesNotExist:
            return False, None
