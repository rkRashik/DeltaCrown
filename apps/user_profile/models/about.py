"""
ProfileAboutItem Model - Facebook-style About section

Allows users to curate what appears in their "About" section:
- Team roles
- Game stats
- Custom text highlights
- Achievements
- Career milestones

Each item has:
- Type (team, role, game, stat, custom)
- Visibility (public, followers_only, private)
- Source reference (Team ID, GameProfile ID, etc.)
- Order index for display

Created: Phase 15 (2025-12-29)
"""
from django.db import models
from django.core.validators import MinValueValidator
from apps.common.models import TimestampedModel


class ProfileAboutItem(TimestampedModel):
    """
    User-curated About section items (Facebook-style).
    
    Users can choose what to highlight on their profile:
    - "Captain at Team Delta" (team role)
    - "Radiant - Valorant" (game rank)
    - "Tournament Winner - DC Open 2024" (achievement)
    - "Esports Analyst" (custom bio line)
    
    Architecture:
    - Generic source references (model + ID)
    - Per-item visibility control
    - User-defined ordering
    - Privacy enforcement at query time
    """
    
    # Item types
    TYPE_TEAM = 'team'
    TYPE_GAME = 'game'
    TYPE_ACHIEVEMENT = 'achievement'
    TYPE_STAT = 'stat'
    TYPE_BIO = 'bio'
    TYPE_CUSTOM = 'custom'
    
    TYPE_CHOICES = [
        (TYPE_TEAM, 'Team Role'),
        (TYPE_GAME, 'Game Passport'),
        (TYPE_ACHIEVEMENT, 'Achievement'),
        (TYPE_STAT, 'Stat Highlight'),
        (TYPE_BIO, 'Bio Line'),
        (TYPE_CUSTOM, 'Custom Text'),
    ]
    
    # Visibility levels
    VISIBILITY_PUBLIC = 'public'
    VISIBILITY_FOLLOWERS = 'followers_only'
    VISIBILITY_PRIVATE = 'private'
    
    VISIBILITY_CHOICES = [
        (VISIBILITY_PUBLIC, 'Public'),
        (VISIBILITY_FOLLOWERS, 'Followers Only'),
        (VISIBILITY_PRIVATE, 'Private (Only Me)'),
    ]
    
    # Core fields
    user_profile = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='about_items',
        help_text='Profile this About item belongs to'
    )
    
    item_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        help_text='Type of About item'
    )
    
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PUBLIC,
        help_text='Who can see this item'
    )
    
    # Generic source reference
    source_model = models.CharField(
        max_length=100,
        blank=True,
        help_text='Source model name (Team, GameProfile, UserBadge, etc.)'
    )
    
    source_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Source object ID'
    )
    
    # Display content
    display_text = models.CharField(
        max_length=200,
        help_text='Text to display (auto-generated or user-provided)'
    )
    
    icon_emoji = models.CharField(
        max_length=10,
        blank=True,
        help_text='Optional emoji icon (🎮, 🏆, 💼, etc.)'
    )
    
    # Ordering
    order_index = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Display order (0 = first)'
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this item is currently visible'
    )
    
    class Meta:
        db_table = 'user_profile_about_item'
        ordering = ['user_profile', 'order_index', '-created_at']
        verbose_name = 'Profile About Item'
        verbose_name_plural = 'Profile About Items'
        indexes = [
            models.Index(fields=['user_profile', 'is_active', 'order_index']),
            models.Index(fields=['user_profile', 'item_type']),
        ]
    
    def __str__(self):
        return f"{self.user_profile.user.username} - {self.item_type}: {self.display_text[:50]}"
    
    def can_be_viewed_by(self, viewer_user, is_follower):
        """
        Check if viewer can see this item.
        
        Args:
            viewer_user: User viewing the profile (None if anonymous)
            is_follower: Whether viewer follows this profile
            
        Returns:
            bool: True if viewer can see this item
        """
        # Owner always sees everything
        if viewer_user and viewer_user.id == self.user_profile.user_id:
            return True
        
        # Private items only for owner
        if self.visibility == self.VISIBILITY_PRIVATE:
            return False
        
        # Followers-only items
        if self.visibility == self.VISIBILITY_FOLLOWERS:
            return is_follower
        
        # Public items visible to all
        return True
