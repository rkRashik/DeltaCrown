"""
Trophy Showcase Config Models - Equipped Cosmetics (P0)

Models:
- TrophyShowcaseConfig: User's equipped cosmetics (border, frame, pinned badges)

Design:
- Stores only what's equipped, not what's unlocked
- Unlocked cosmetics computed from achievements/badges
- Minimal MVP: border/frame/badges selection only

Related Models:
- Badge: Achievement badges (apps.user_profile.models_main)
- UserBadge: User's earned badges (apps.user_profile.models_main)
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# ============================================================================
# TROPHY SHOWCASE CONFIG MODEL
# ============================================================================

class TrophyShowcaseConfig(models.Model):
    """
    User's equipped cosmetics for profile showcase.
    
    Stores what cosmetics the user has selected to display:
    - Profile border (earned from achievements)
    - Profile frame (earned from tournaments)
    - Pinned badges (up to 5 badges to showcase)
    
    This model only stores selections, not unlocks.
    Unlocked cosmetics are computed from:
    - Badge.rarity (determines available borders)
    - UserBadge.is_pinned (which badges user has earned)
    - Tournament wins (determines available frames)
    
    Privacy:
    - No separate privacy control (respects profile privacy)
    - If profile private, showcase hidden
    
    Usage:
    - Display in profile header (border/frame)
    - Display in "Trophies" tab (pinned badges)
    - Allow user to change selections in settings
    """
    
    class BorderStyle(models.TextChoices):
        """
        Profile border styles (unlocked via achievements).
        
        Unlock criteria:
        - NONE: Default (always available)
        - BRONZE: Earn any Common badge
        - SILVER: Earn any Rare badge
        - GOLD: Earn any Epic badge
        - PLATINUM: Earn any Legendary badge
        - DIAMOND: Earn 10+ Legendary badges
        - MASTER: Win a major tournament
        """
        NONE = 'none', _('No Border')
        BRONZE = 'bronze', _('Bronze Border')
        SILVER = 'silver', _('Silver Border')
        GOLD = 'gold', _('Gold Border')
        PLATINUM = 'platinum', _('Platinum Border')
        DIAMOND = 'diamond', _('Diamond Border')
        MASTER = 'master', _('Master Border')
    
    class FrameStyle(models.TextChoices):
        """
        Profile frame styles (unlocked via tournaments).
        
        Unlock criteria:
        - NONE: Default (always available)
        - COMPETITOR: Participate in any tournament
        - FINALIST: Reach tournament finals
        - CHAMPION: Win a tournament
        - GRAND_CHAMPION: Win 3+ tournaments
        - LEGEND: Win 10+ tournaments
        """
        NONE = 'none', _('No Frame')
        COMPETITOR = 'competitor', _('Competitor Frame')
        FINALIST = 'finalist', _('Finalist Frame')
        CHAMPION = 'champion', _('Champion Frame')
        GRAND_CHAMPION = 'grand_champion', _('Grand Champion Frame')
        LEGEND = 'legend', _('Legend Frame')
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trophy_showcase'
    )
    
    # Equipped cosmetics
    border = models.CharField(
        max_length=20,
        choices=BorderStyle.choices,
        default=BorderStyle.NONE,
        help_text="Selected profile border (must be unlocked)"
    )
    
    frame = models.CharField(
        max_length=20,
        choices=FrameStyle.choices,
        default=FrameStyle.NONE,
        help_text="Selected profile frame (must be unlocked)"
    )
    
    # Pinned badges (reference to UserBadge IDs)
    pinned_badge_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="List of UserBadge IDs to display (max 5)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profile_trophy_showcase'
        verbose_name = 'Trophy Showcase Config'
        verbose_name_plural = 'Trophy Showcase Configs'
    
    def __str__(self):
        return f"{self.user.username} - Trophy Showcase"
    
    def clean(self):
        """Validate equipped cosmetics."""
        super().clean()
        
        # Normalize None to empty list (for existing DB rows)
        if self.pinned_badge_ids is None:
            self.pinned_badge_ids = []
        
        # Validate pinned_badge_ids is a list
        if not isinstance(self.pinned_badge_ids, list):
            raise ValidationError({
                'pinned_badge_ids': 'Must be a list of UserBadge IDs'
            })
        
        # Validate max 5 pinned badges
        if len(self.pinned_badge_ids) > 5:
            raise ValidationError({
                'pinned_badge_ids': 'Cannot pin more than 5 badges'
            })
        
        # Validate pinned badges belong to user
        if self.pinned_badge_ids and self.user_id:
            from apps.user_profile.models_main import UserBadge
            
            user_badge_ids = set(
                UserBadge.objects
                .filter(user=self.user)
                .values_list('id', flat=True)
            )
            
            for badge_id in self.pinned_badge_ids:
                if badge_id not in user_badge_ids:
                    raise ValidationError({
                        'pinned_badge_ids': f'Badge ID {badge_id} does not belong to this user'
                    })
    
    def save(self, *args, **kwargs):
        """Override save to enforce validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_pinned_badges(self):
        """
        Get UserBadge objects for pinned badges.
        
        Returns:
            QuerySet of UserBadge objects in pinned order
        """
        if not self.pinned_badge_ids:
            return []
        
        from apps.user_profile.models_main import UserBadge
        
        # Preserve order from pinned_badge_ids
        badges = UserBadge.objects.filter(
            id__in=self.pinned_badge_ids
        ).select_related('badge')
        
        # Sort by pinned_badge_ids order
        badge_dict = {badge.id: badge for badge in badges}
        return [badge_dict[badge_id] for badge_id in self.pinned_badge_ids if badge_id in badge_dict]
    
    def pin_badge(self, user_badge_id):
        """
        Pin a badge to showcase (add to front of list).
        
        Args:
            user_badge_id: ID of UserBadge to pin
        
        Raises:
            ValidationError: If badge doesn't belong to user or max pinned
        """
        # Check if already pinned
        if user_badge_id in self.pinned_badge_ids:
            return  # Already pinned, no-op
        
        # Check max pinned
        if len(self.pinned_badge_ids) >= 5:
            raise ValidationError('Cannot pin more than 5 badges')
        
        # Check badge belongs to user
        from apps.user_profile.models_main import UserBadge
        if not UserBadge.objects.filter(id=user_badge_id, user=self.user).exists():
            raise ValidationError('Badge does not belong to this user')
        
        # Add to front of list
        self.pinned_badge_ids = [user_badge_id] + self.pinned_badge_ids
        self.save()
    
    def unpin_badge(self, user_badge_id):
        """
        Unpin a badge from showcase.
        
        Args:
            user_badge_id: ID of UserBadge to unpin
        """
        if user_badge_id in self.pinned_badge_ids:
            self.pinned_badge_ids = [
                bid for bid in self.pinned_badge_ids 
                if bid != user_badge_id
            ]
            self.save()
    
    def reorder_pinned_badges(self, new_order):
        """
        Reorder pinned badges.
        
        Args:
            new_order: List of UserBadge IDs in desired order
        
        Raises:
            ValidationError: If IDs don't match current pinned badges
        """
        # Validate same IDs, just reordered
        if set(new_order) != set(self.pinned_badge_ids):
            raise ValidationError('New order must contain same badge IDs')
        
        self.pinned_badge_ids = new_order
        self.save()
