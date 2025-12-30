"""
Profile Showcase Model
Phase 14C: Facebook-style About section with user-controlled toggles

Allows users to customize their About section by:
- Enabling/disabling subsections
- Featuring a team or game passport
- Adding highlights (tournament wins, achievements, etc.)
"""

from django.db import models
from django.contrib.postgres.fields import ArrayField
from apps.user_profile.models_main import UserProfile


class ProfileShowcase(models.Model):
    """
    User-controlled About section configuration.
    
    Similar to Facebook's About page where users can toggle what sections appear
    and in what order.
    """
    
    user_profile = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='showcase'
    )
    
    # Section toggles (list of enabled section slugs)
    enabled_sections = models.JSONField(
        default=list,
        help_text="List of enabled About subsections: ['identity', 'demographics', 'contact', 'gaming', 'social', 'competitive']"
    )
    
    # Featured content
    featured_team_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID of featured team (if user wants to highlight their current team)"
    )
    
    featured_team_role = models.CharField(
        max_length=50,
        blank=True,
        help_text="Role in featured team (e.g., 'Team Captain', 'IGL', 'Fragger')"
    )
    
    featured_passport_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID of featured game passport (user's main game)"
    )
    
    # Highlights (flexible JSON array)
    highlights = models.JSONField(
        default=list,
        help_text="List of highlight items: [{'type': 'tournament', 'id': 123, 'label': 'Champions 2024 Winner', 'icon': '🏆'}]"
    )
    
    # Display order (for future use if user can reorder sections)
    section_order = models.JSONField(
        default=list,
        blank=True,
        help_text="Custom section order if user wants non-default arrangement"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Profile Showcase"
        verbose_name_plural = "Profile Showcases"
        db_table = "user_profile_showcase"
    
    def __str__(self):
        return f"Showcase for {self.user_profile.display_name}"
    
    def get_enabled_sections(self):
        """Get list of enabled section slugs."""
        if not self.enabled_sections:
            return self.get_default_sections()
        return self.enabled_sections
    
    @staticmethod
    def get_default_sections():
        """Default sections shown when user hasn't customized."""
        return ['identity', 'gaming', 'social', 'competitive']
    
    @staticmethod
    def get_all_available_sections():
        """All possible sections a user can enable."""
        return {
            'identity': {
                'label': 'Identity',
                'icon': '👤',
                'description': 'Display name, bio, pronouns',
                'fields': ['display_name', 'bio', 'pronouns']
            },
            'demographics': {
                'label': 'Demographics',
                'icon': '📋',
                'description': 'Age, gender, nationality',
                'fields': ['date_of_birth', 'gender', 'nationality']
            },
            'contact': {
                'label': 'Contact',
                'icon': '📧',
                'description': 'Email, phone (respects privacy settings)',
                'fields': ['email', 'phone', 'country', 'city']
            },
            'gaming': {
                'label': 'Gaming',
                'icon': '🎮',
                'description': 'Game passports, preferred games',
                'fields': ['game_passports', 'preferred_games']
            },
            'social': {
                'label': 'Social Links',
                'icon': '🔗',
                'description': 'Twitch, YouTube, Discord, etc.',
                'fields': ['social_links']
            },
            'competitive': {
                'label': 'Competitive Career',
                'icon': '🏆',
                'description': 'Skill rating, reputation, achievements',
                'fields': ['skill_rating', 'reputation_score', 'level', 'xp']
            },
            'teams': {
                'label': 'Teams',
                'icon': '👥',
                'description': 'Current and past team memberships',
                'fields': ['team_memberships']
            },
            'economy': {
                'label': 'Economy Summary',
                'icon': '💰',
                'description': 'DeltaCoin balance, lifetime earnings (if not private)',
                'fields': ['deltacoin_balance', 'lifetime_earnings']
            }
        }
    
    def is_section_enabled(self, section_slug):
        """Check if a specific section is enabled."""
        return section_slug in self.get_enabled_sections()
    
    def toggle_section(self, section_slug):
        """Toggle a section on/off."""
        sections = self.get_enabled_sections()
        if section_slug in sections:
            sections.remove(section_slug)
        else:
            sections.append(section_slug)
        self.enabled_sections = sections
        self.save()
    
    def set_featured_team(self, team_id, role=''):
        """Set featured team."""
        self.featured_team_id = team_id
        self.featured_team_role = role
        self.save()
    
    def set_featured_passport(self, passport_id):
        """Set featured game passport."""
        self.featured_passport_id = passport_id
        self.save()
    
    def add_highlight(self, highlight_type, item_id, label, icon='✨', metadata=None):
        """
        Add a highlight to the profile.
        
        Args:
            highlight_type: 'tournament', 'achievement', 'milestone', 'custom'
            item_id: ID of the related object (tournament, achievement, etc.)
            label: Display text (e.g., "Champions 2024 Winner")
            icon: Emoji or icon class
            metadata: Additional data (placement, prize, date, etc.)
        """
        highlight = {
            'type': highlight_type,
            'id': item_id,
            'label': label,
            'icon': icon
        }
        if metadata:
            highlight['metadata'] = metadata
        
        highlights = self.highlights or []
        highlights.append(highlight)
        self.highlights = highlights
        self.save()
    
    def remove_highlight(self, item_id):
        """Remove a highlight by ID."""
        self.highlights = [h for h in self.highlights if h.get('id') != item_id]
        self.save()
