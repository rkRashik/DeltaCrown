from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import uuid

REGION_CHOICES = [
    ("BD", "Bangladesh"),
    ("SA", "South Asia"),
    ("AS", "Asia (Other)"),
    ("EU", "Europe"),
    ("NA", "North America"),
]

KYC_STATUS_CHOICES = [
    ("unverified", "Unverified"),
    ("pending", "Pending Review"),
    ("verified", "Verified"),
    ("rejected", "Rejected"),
]

GENDER_CHOICES = [
    ("male", "Male"),
    ("female", "Female"),
    ("other", "Other"),
    ("prefer_not_to_say", "Prefer not to say"),
]

def user_avatar_path(instance, filename):
    return f"user_avatars/{instance.user_id}/{filename}"

def user_banner_path(instance, filename):
    return f"user_banners/{instance.user_id}/{filename}"


class UserProfile(models.Model):
    # ===== SYSTEM IDENTITY (Immutable) =====
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, help_text="Public unique identifier")
    public_id = models.CharField(
        max_length=15,
        unique=True,
        null=True,  # Will be False after backfill migration
        blank=True,
        db_index=True,
        help_text="Human-readable public identifier (DC-YY-NNNNNN format, e.g., DC-25-000042)"
    )
    updated_at = models.DateTimeField(auto_now=True, help_text="Last profile update timestamp")
    
    # ===== LEGAL IDENTITY (Locked after KYC) =====
    real_full_name = models.CharField(
        max_length=200, 
        blank=True, 
        default="",
        help_text="Full legal name for official tournament registration and certificates"
    )
    date_of_birth = models.DateField(
        null=True, 
        blank=True,
        help_text="Date of birth for age verification and tournament eligibility"
    )
    nationality = models.CharField(
        max_length=100, 
        blank=True, 
        default="",
        help_text="Nationality/citizenship (may differ from country of residence)"
    )
    kyc_status = models.CharField(
        max_length=20,
        choices=KYC_STATUS_CHOICES,
        default="unverified",
        help_text="KYC verification status"
    )
    kyc_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when KYC was verified"
    )
    
    # ===== PUBLIC IDENTITY (User Customizable) =====
    display_name = models.CharField(max_length=80)
    slug = models.SlugField(
        max_length=64,
        unique=True,
        blank=True,
        default="",
        help_text="Custom URL slug (e.g., deltacrown.com/u/legend)"
    )
    avatar = models.ImageField(upload_to=user_avatar_path, blank=True, null=True)
    banner = models.ImageField(upload_to=user_banner_path, blank=True, null=True, help_text="Profile banner image")
    bio = models.TextField(blank=True, help_text="Profile bio/headline")
    
    # ===== LOCATION =====
    country = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Country of residence (for regional tournaments)"
    )
    region = models.CharField(max_length=2, choices=REGION_CHOICES, default="BD")
    city = models.CharField(max_length=100, blank=True, default="", help_text="City of residence")
    postal_code = models.CharField(max_length=20, blank=True, default="", help_text="Postal/ZIP code")
    address = models.TextField(
        max_length=300,
        blank=True,
        default="",
        help_text="Street address for correspondence and prize shipping"
    )
    
    # ===== DEMOGRAPHICS =====
    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES,
        blank=True,
        default="",
        help_text="Gender identity (optional, for demographics and gender-specific events)"
    )
    
    # ===== CONTACT INFORMATION =====
    phone = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Primary phone number (international format preferred: +8801XXXXXXXXX)"
    )
    whatsapp = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="WhatsApp number (can be different from phone, international format)"
    )
    secondary_email = models.EmailField(
        blank=True,
        default="",
        help_text="Public/secondary email for contact (primary email stays private)"
    )
    secondary_email_verified = models.BooleanField(
        default=False,
        help_text="Whether secondary email has been verified via OTP"
    )
    preferred_contact_method = models.CharField(
        max_length=20,
        blank=True,
        default="",
        choices=[
            ('email', 'Email'),
            ('phone', 'Phone'),
            ('whatsapp', 'WhatsApp'),
            ('discord', 'Discord'),
            ('facebook', 'Facebook'),
        ],
        help_text="User's preferred method of contact"
    )
    
    # ===== EMERGENCY CONTACT (LAN Events) =====
    emergency_contact_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Emergency contact full name"
    )
    emergency_contact_phone = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Emergency contact phone number"
    )
    emergency_contact_relation = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Relationship to emergency contact (e.g., Parent, Spouse, Guardian)"
    )
    
    # ===== COMPETITIVE CAREER =====
    reputation_score = models.IntegerField(
        default=100,
        help_text="Fair play karma rating (anti-toxicity)"
    )
    skill_rating = models.IntegerField(
        default=1000,
        help_text="Platform-calculated ELO/MMR for dynamic seeding"
    )
    
    # ===== GAMIFICATION =====
    level = models.IntegerField(default=1, help_text="User level based on platform activity")
    xp = models.IntegerField(default=0, help_text="Experience points")
    pinned_badges = models.JSONField(
        default=list,
        blank=True,
        help_text="List of pinned badge IDs for showcase (max 5)"
    )
    inventory_items = models.JSONField(
        default=list,
        blank=True,
        help_text="Digital assets (profile frames, chat colors, etc.)"
    )
    
    # ===== ECONOMY =====
    deltacoin_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Current DeltaCoin balance (read-only, managed by wallet)"
    )
    lifetime_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total value of prizes won (bragging rights)"
    )
    
    # ===== SOCIAL LINKS (REMOVED - Use SocialLink model instead) =====
    # UP.2 C2 CLEANUP (2026-01-15): Legacy fields removed after backfill migration
    # All social media links now managed via SocialLink model
    # Migration: 0XXX_remove_legacy_social_fields.py
    # Backfill command: python manage.py backfill_social_links (COMPLETED)
    
    stream_status = models.BooleanField(
        default=False,
        help_text="Indicates if user is currently streaming (grants XP bonuses)"
    )
    
    # ===== PROFILE CUSTOMIZATION (Phase 3) =====
    pronouns = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Pronouns (e.g., he/him, she/her, they/them)"
    )
    
    preferred_games = models.JSONField(default=list, blank=True, null=True)
    
    # ===== GAME PROFILES (Future-Proof Pluggable System) =====
    # GP-CLEAN-02: DEPRECATED - Use GameProfile model instead
    game_profiles = models.JSONField(
        default=list,
        blank=True,
        help_text="DEPRECATED: Use GameProfile model and GamePassportService instead. See GP-0 documentation."
    )
    
    # ===== LEGACY GAME IDs REMOVED =====
    # NOTE: Legacy game ID fields (riot_id, riot_tagline, efootball_id, steam_id, mlbb_id, 
    # mlbb_server_id, pubg_mobile_id, free_fire_id, ea_id, codm_uid) were removed in 
    # migration 0011_remove_legacy_game_id_fields after data migration to game_profiles.
    # Use get_game_profile(game) and set_game_profile(game, data) methods instead.

    # ===== PRIVACY SETTINGS =====
    # REMOVED: Legacy privacy fields (is_private, show_email, show_phone, show_socials, 
    # show_address, show_age, show_gender, show_country, show_real_name) have been removed
    # in migration 0029_remove_legacy_privacy_fields.
    # All privacy settings are now managed via the PrivacySettings model.
    # Use PrivacySettingsService or profile.privacy_settings to access privacy configuration.
    
    # ===== PLATFORM PREFERENCES (Phase 6 Part C) =====
    preferred_language = models.CharField(
        max_length=10,
        default='en',
        choices=[
            ('en', 'English'),
            ('bn', 'Bengali (Coming Soon)'),
        ],
        help_text="Preferred UI language"
    )
    timezone_pref = models.CharField(
        max_length=50,
        default='Asia/Dhaka',
        help_text="User's preferred timezone for displaying times (e.g., 'Asia/Dhaka', 'UTC')"
    )
    time_format = models.CharField(
        max_length=10,
        default='12h',
        choices=[
            ('12h', '12-hour (3:00 PM)'),
            ('24h', '24-hour (15:00)'),
        ],
        help_text="Preferred time display format"
    )
    theme_preference = models.CharField(
        max_length=10,
        default='dark',
        choices=[
            ('light', 'Light'),
            ('dark', 'Dark'),
            ('system', 'System'),
        ],
        help_text="UI theme preference"
    )
    
    # ===== ABOUT SECTION FIELDS (Phase 4) =====
    device_platform = models.CharField(
        max_length=20,
        blank=True,
        default="",
        choices=[
            ('PC', 'PC'),
            ('CONSOLE_PS', 'PlayStation'),
            ('CONSOLE_XBOX', 'Xbox'),
            ('MOBILE_ANDROID', 'Mobile (Android)'),
            ('MOBILE_IOS', 'Mobile (iOS)'),
        ],
        help_text="Primary gaming platform/device"
    )
    
    play_style = models.CharField(
        max_length=20,
        blank=True,
        default="",
        choices=[
            ('CASUAL', 'Casual Player'),
            ('COMPETITIVE', 'Competitive'),
            ('PROFESSIONAL', 'Professional'),
            ('CONTENT_CREATOR', 'Content Creator'),
        ],
        help_text="Player's competitive intent and play style"
    )
    
    lan_availability = models.BooleanField(
        default=False,
        help_text="Available for LAN tournaments and offline events"
    )
    
    main_role = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Primary competitive role (e.g., 'Entry Fragger', 'Support', 'IGL')"
    )
    
    secondary_role = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Secondary competitive role for flexibility"
    )
    
    communication_languages = models.JSONField(
        default=list,
        blank=True,
        help_text="List of languages for team communication (e.g., ['en', 'bn', 'hi'])"
    )
    
    active_hours = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Typical active gaming hours (e.g., '14:00-22:00 UTC' or '6PM-2AM local')"
    )
    
    # ===== METADATA (Future-Proof Extensibility) =====
    attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Flexible metadata for future features (jersey size, dietary restrictions for LANs, etc.)"
    )
    system_settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="User preferences (theme, notifications, language)"
    )


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["region"]),
            models.Index(fields=["public_id"], name='idx_profile_public_id'),
        ]
        verbose_name = "User Profile"

    def __str__(self):
        if self.public_id:
            return f"{self.display_name or self.user.username} ({self.public_id})"
        return self.display_name or getattr(self.user, "username", str(self.user_id))
    
    def clean(self):
        """Validate fields before saving"""
        super().clean()
        
        # Validate public_id format if present
        if self.public_id:
            from apps.user_profile.services.public_id import PublicIDGenerator
            if not PublicIDGenerator.validate_format(self.public_id):
                raise ValidationError(
                    f"Invalid public_id format: {self.public_id}. "
                    "Must be DC-YY-NNNNNN (e.g., DC-25-000042)"
                )
    
    # ===== COMPUTED PROPERTIES =====
    
    @property
    def age(self):
        """Calculate age from date of birth."""
        if not self.date_of_birth:
            return None
        today = timezone.now().date()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    @property
    def is_kyc_verified(self):
        """Check if profile is KYC verified."""
        return self.kyc_status == "verified"
    
    @property
    def full_name(self):
        """Return real_full_name if set, otherwise fall back to User.get_full_name()."""
        if self.real_full_name:
            return self.real_full_name
        return self.user.get_full_name() if hasattr(self.user, 'get_full_name') else ""
    
    # ===== MEDIA HELPER METHODS =====
    
    def get_avatar_url(self):
        """Get avatar URL or return None if no avatar set."""
        if self.avatar:
            return self.avatar.url
        return None
    
    def get_banner_url(self):
        """Get banner URL or return None if no banner set."""
        if self.banner:
            return self.banner.url
        return None
    
    # ===== TEAM HELPER METHODS =====
    
    def get_active_teams(self):
        """Get all teams where user is an active member."""
        return [
            membership.team 
            for membership in self.team_memberships.filter(status='ACTIVE')
        ]
    
    def is_team_member(self, team):
        """Check if user is an active member of a specific team."""
        return self.team_memberships.filter(team=team, status='ACTIVE').exists()
    
    def is_team_captain(self, team):
        """Check if user is the captain of a specific team."""
        return self.captain_teams.filter(id=team.id).exists()
    
    def can_register_for_team_tournament(self, team):
        """Check if user has permission to register team for tournaments."""
        return self.is_team_captain(team) or self.team_memberships.filter(
            team=team, 
            status='ACTIVE',
            role__in=['CAPTAIN', 'MANAGER']
        ).exists()
    
    # ===== GAME PROFILE METHODS (Modern Unified System) =====
    # GP-CLEAN-02: DEPRECATED - Use GamePassportService instead
    
    def get_game_profile(self, game_code):
        """
        DEPRECATED: Use GamePassportService.get_passport() instead.
        
        Get game profile for a specific game from the game_profiles JSON field.
        
        Args:
            game_code: Game slug (e.g., 'valorant', 'cs2', 'dota2', 'mlbb')
        
        Returns:
            dict: Game profile data or None if not found
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"DEPRECATED: get_game_profile() called for user_id={self.user.id}. "
            "Use GamePassportService.get_passport() instead."
        )
        if not isinstance(self.game_profiles, list):
            return None
            
        game_code_lower = game_code.lower()
        for profile in self.game_profiles:
            if isinstance(profile, dict) and profile.get('game', '').lower() == game_code_lower:
                return profile
        return None
    
    def set_game_profile(self, game_code, data):
        """
        BLOCKED: JSON writes forbidden per GP-STABILIZE-01.
        Use GamePassportService.create_passport() or update_passport() instead.
        
        This method now raises RuntimeError to prevent accidental JSON writes.
        All game profile data must go through GameProfile model.
        
        Args:
            game_code: Game slug (e.g., 'valorant', 'cs2')
            data: dict with keys: ign, role (optional), rank (optional), platform (optional), metadata (optional)
        
        Raises:
            RuntimeError: Always - JSON writes blocked
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            f"BLOCKED: set_game_profile() called for user_id={self.user.id}. "
            "JSON writes are forbidden. Use GamePassportService instead."
        )
        raise RuntimeError(
            "set_game_profile() is blocked. Use GamePassportService.create_passport() "
            "or update_passport() instead. See GP-STABILIZE-01 for migration guide."
        )
    
    def add_game_profile(self, game_code, ign, role='', rank='', platform='PC', metadata=None):
        """
        BLOCKED: JSON writes forbidden per GP-STABILIZE-01.
        Use GamePassportService.create_passport() instead.
        
        Example:
            >>> profile.add_game_profile('valorant', 'TenZ#1234', role='Duelist', rank='Radiant')
        """
        return self.set_game_profile(game_code, {
            'ign': ign,
            'role': role,
            'rank': rank,
            'platform': platform,
            'metadata': metadata or {}
        })
    
    def remove_game_profile(self, game_code):
        """
        BLOCKED: JSON writes forbidden per GP-STABILIZE-01.
        Use GamePassportService.delete_passport() instead.
        
        Args:
            game_code: Game slug to remove
        
        Raises:
            RuntimeError: Always - JSON writes blocked
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            f"BLOCKED: remove_game_profile() called for user_id={self.user.id}. "
            "JSON writes are forbidden. Use GamePassportService.delete_passport() instead."
        )
        raise RuntimeError(
            "remove_game_profile() is blocked. Use GamePassportService.delete_passport() instead."
        )
    
    def get_game_id(self, game_code):
        """
        Get the game ID/IGN for a specific game (shorthand for getting 'ign' field).
        
        Args:
            game_code: Game slug
        
        Returns:
            str: The IGN/game ID or empty string
            
        Example:
            >>> profile.get_game_id('valorant')
            'TenZ#1234'
        """
        game_profile = self.get_game_profile(game_code)
        if game_profile:
            return game_profile.get('ign', '')
        return ''
    
    def set_game_id(self, game_code, ign):
        """
        Set the game ID/IGN for a specific game (shorthand for setting 'ign' field).
        
        Args:
            game_code: Game slug
            ign: The in-game name/ID
        
        Returns:
            bool: True if successful
            
        Example:
            >>> profile.set_game_id('valorant', 'TenZ#1234')
        """
        game_profile = self.get_game_profile(game_code)
        if game_profile:
            # Update existing profile
            game_profile['ign'] = ign
            self.save(update_fields=['game_profiles'])
            return True
        else:
            # Create new profile with just the IGN
            return self.set_game_profile(game_code, {'ign': ign})
    
    def get_all_game_profiles(self):
        """
        Get all game profiles for this user.
        
        Returns:
            list: List of game profile dicts
        """
        if not isinstance(self.game_profiles, list):
            return []
        return [p for p in self.game_profiles if isinstance(p, dict) and p.get('game')]
    
    def has_game_profile(self, game_code):
        """Check if user has a profile for a specific game."""
        return self.get_game_profile(game_code) is not None
    
    # ===== XP AND BADGE METHODS =====
    
    def add_xp(self, amount, reason='', context=None):
        """
        Award XP to this profile
        
        Args:
            amount: XP to award
            reason: Why XP was awarded
            context: Optional metadata dict
        
        Returns:
            dict with xp_awarded, new_total, old_level, new_level, leveled_up
        """
        from apps.user_profile.services import award_xp
        return award_xp(self.user, amount, reason, context)
    
    def earn_badge(self, badge_slug, context=None):
        """
        Award a badge to this profile
        
        Args:
            badge_slug: Badge slug or Badge instance
            context: Optional metadata dict
        
        Returns:
            UserBadge instance or None
        """
        from apps.user_profile.services import award_badge
        return award_badge(self.user, badge_slug, context)
    
    def get_pinned_badges(self):
        """Get Badge instances for pinned badge IDs"""
        if not self.pinned_badges:
            return []
        
        badge_ids = [bid for bid in self.pinned_badges if isinstance(bid, int)]
        if not badge_ids:
            return []
        
        return Badge.objects.filter(id__in=badge_ids).order_by('order')
    
    def pin_badge(self, badge):
        """
        Pin a badge to profile showcase (max 5)
        
        Args:
            badge: Badge instance or badge ID
        
        Returns:
            bool - True if pinned, False if already pinned or limit reached
        """
        badge_id = badge.id if hasattr(badge, 'id') else badge
        
        if badge_id in self.pinned_badges:
            return False  # Already pinned
        
        if len(self.pinned_badges) >= 5:
            return False  # Max limit reached
        
        self.pinned_badges.append(badge_id)
        self.save(update_fields=['pinned_badges', 'updated_at'])
        
        # Update UserBadge is_pinned flag
        UserBadge.objects.filter(user=self.user, badge_id=badge_id).update(is_pinned=True)
        
        return True
    
    def unpin_badge(self, badge):
        """
        Unpin a badge from profile showcase
        
        Args:
            badge: Badge instance or badge ID
        
        Returns:
            bool - True if unpinned, False if wasn't pinned
        """
        badge_id = badge.id if hasattr(badge, 'id') else badge
        
        if badge_id not in self.pinned_badges:
            return False
        
        self.pinned_badges.remove(badge_id)
        self.save(update_fields=['pinned_badges', 'updated_at'])
        
        # Update UserBadge is_pinned flag
        UserBadge.objects.filter(user=self.user, badge_id=badge_id).update(is_pinned=False)
        
        return True
    
    @property
    def xp_to_next_level(self):
        """Calculate XP needed for next level"""
        from apps.user_profile.services.xp_service import XPService
        return XPService.xp_to_next_level(self.xp, self.level)
    
    @property
    def level_progress_percentage(self):
        """Calculate percentage progress to next level (0-100)"""
        from apps.user_profile.services.xp_service import XPService
        current_level_xp = XPService.xp_for_level(self.level)
        next_level_xp = XPService.xp_for_level(self.level + 1)
        
        if next_level_xp == current_level_xp:
            return 100
        
        progress = ((self.xp - current_level_xp) / (next_level_xp - current_level_xp)) * 100
        return max(0, min(100, progress))
    
    # ===== PHASE 3: PROFILE STATS METHODS =====
    
    def calculate_win_rate(self):
        """Calculate overall win rate percentage from match history"""
        try:
            total_matches = self.user.matches.count()
            if total_matches == 0:
                return 0
            wins = self.user.matches.filter(result='win').count()
            return int((wins / total_matches) * 100)
        except Exception:
            return 0
    
    @property
    def total_earnings(self):
        """Get total earnings from wallet/economy system"""
        try:
            from apps.economy.models import DeltaCrownWallet
            wallet = DeltaCrownWallet.objects.filter(profile=self).first()
            if wallet:
                # Return lifetime earnings if tracked, otherwise current balance
                return getattr(wallet, 'lifetime_earnings', wallet.cached_balance)
            return self.lifetime_earnings
        except Exception:
            return self.lifetime_earnings
    
    @property
    def wallet(self):
        """Get user's wallet instance"""
        try:
            from apps.economy.models import DeltaCrownWallet
            wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=self)
            return wallet
        except Exception:
            return None
    
    @property
    def followers(self):
        """Get followers queryset (placeholder for future social system)"""
        # TODO: Implement follower system
        return self.user.followers if hasattr(self.user, 'followers') else self.user.objects.none()
    
    @property
    def following(self):
        """Get following queryset (placeholder for future social system)"""
        # TODO: Implement following system
        return self.user.following if hasattr(self.user, 'following') else self.user.objects.none()
    
    @property
    def tournament_participations(self):
        """Get tournament participations (placeholder)"""
        # TODO: Link to tournament system when available
        return self.user.objects.none()
    
    @property
    def team_memberships(self):
        """Get team memberships"""
        try:
            from apps.teams.models import TeamMembership
            return TeamMembership.objects.filter(profile=self)
        except Exception:
            return self.user.objects.none()
    
    def save(self, *args, **kwargs):
        """Auto-generate unique slug from display_name or username."""
        if not self.slug or self.slug.strip() == "":
            # Generate base slug from display_name or username
            base_slug = slugify(self.display_name or getattr(self.user, 'username', 'user'))
            
            # Ensure uniqueness by appending number if needed
            original_slug = base_slug
            counter = 1
            while UserProfile.objects.filter(slug=base_slug).exclude(pk=self.pk).exists():
                base_slug = f"{original_slug}-{counter}"
                counter += 1
            
            self.slug = base_slug
        
        super().save(*args, **kwargs)


def kyc_document_path(instance, filename):
    """Upload path for KYC documents"""
    return f"kyc_documents/{instance.user_profile.user_id}/{filename}"


class PrivacySettings(models.Model):
    """
    Granular privacy settings for UserProfile.
    Separate model for better organization and future extensibility.
    """
    
    # Visibility Presets
    PRESET_PUBLIC = 'PUBLIC'
    PRESET_PROTECTED = 'PROTECTED'
    PRESET_PRIVATE = 'PRIVATE'
    
    PRESET_CHOICES = [
        (PRESET_PUBLIC, 'Public - Everyone can see everything'),
        (PRESET_PROTECTED, 'Protected - Show limited info to non-friends'),
        (PRESET_PRIVATE, 'Private - Minimal public visibility'),
    ]
    
    user_profile = models.OneToOneField(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='privacy_settings',
        help_text="User profile these settings belong to"
    )
    
    # ===== VISIBILITY PRESET =====
    visibility_preset = models.CharField(
        max_length=20,
        choices=PRESET_CHOICES,
        default=PRESET_PUBLIC,
        help_text="Quick privacy preset that sets multiple toggles"
    )
    
    # ===== PROFILE VISIBILITY =====
    show_real_name = models.BooleanField(
        default=False,
        help_text="Show real full name on public profile"
    )
    show_phone = models.BooleanField(
        default=False,
        help_text="Show phone number on public profile"
    )
    show_email = models.BooleanField(
        default=False,
        help_text="Show email address on public profile"
    )
    show_age = models.BooleanField(
        default=True,
        help_text="Show age (calculated from date of birth)"
    )
    show_gender = models.BooleanField(
        default=False,
        help_text="Show gender on public profile"
    )
    show_country = models.BooleanField(
        default=True,
        help_text="Show country of residence"
    )
    show_address = models.BooleanField(
        default=False,
        help_text="Show full address on public profile"
    )
    
    # ===== GAMING & ACTIVITY =====
    show_game_ids = models.BooleanField(
        default=True,
        help_text="Show gaming IDs (Riot ID, Steam ID, etc.)"
    )
    show_match_history = models.BooleanField(
        default=True,
        help_text="Show tournament match history"
    )
    show_teams = models.BooleanField(
        default=True,
        help_text="Show team memberships"
    )
    show_achievements = models.BooleanField(
        default=True,
        help_text="Show badges and achievements"
    )
    show_activity_feed = models.BooleanField(
        default=True,
        help_text="Show activity feed on profile"
    )
    show_tournaments = models.BooleanField(
        default=True,
        help_text="Show tournament participation history"
    )
    
    # ===== ECONOMY & INVENTORY =====
    show_inventory_value = models.BooleanField(
        default=False,
        help_text="Show total inventory/cosmetics value"
    )
    show_level_xp = models.BooleanField(
        default=True,
        help_text="Show player level and XP"
    )
    
    # UP-PHASE2B: Inventory Visibility Control
    INVENTORY_VISIBILITY_CHOICES = [
        ('PUBLIC', 'Everyone'),
        ('FRIENDS', 'Friends Only'),
        ('PRIVATE', 'Only Me'),
    ]
    inventory_visibility = models.CharField(
        max_length=20,
        choices=INVENTORY_VISIBILITY_CHOICES,
        default='PUBLIC',
        help_text='Who can see your inventory and cosmetics collection'
    )
    
    # ===== SOCIAL =====
    show_social_links = models.BooleanField(
        default=True,
        help_text="Show social media links (Facebook, Instagram, etc.)"
    )
    show_followers_count = models.BooleanField(
        default=True,
        help_text="Show follower count on profile"
    )
    show_following_count = models.BooleanField(
        default=True,
        help_text="Show following count on profile"
    )
    show_followers_list = models.BooleanField(
        default=True,
        help_text="Allow viewing list of followers"
    )
    show_following_list = models.BooleanField(
        default=True,
        help_text="Allow viewing list of users being followed"
    )
    
    # ===== INTERACTION PERMISSIONS =====
    allow_team_invites = models.BooleanField(
        default=True,
        help_text="Allow receiving team invitations"
    )
    allow_friend_requests = models.BooleanField(
        default=True,
        help_text="Allow receiving friend requests"
    )
    allow_direct_messages = models.BooleanField(
        default=True,
        help_text="Allow receiving direct messages from other users"
    )
    
    # ===== PHASE 6A: PRIVATE ACCOUNT =====
    is_private_account = models.BooleanField(
        default=False,
        help_text="When enabled, people must request to follow you (follow requests require approval)"
    )
    
    # ===== PHASE 4: ABOUT SECTION PRIVACY =====
    show_pronouns = models.BooleanField(
        default=True,
        help_text="Show pronouns on public profile"
    )
    show_nationality = models.BooleanField(
        default=True,
        help_text="Show nationality on public profile"
    )
    show_device_platform = models.BooleanField(
        default=True,
        help_text="Show gaming device/platform (PC, Console, Mobile)"
    )
    show_play_style = models.BooleanField(
        default=True,
        help_text="Show play style (Casual, Competitive, Professional)"
    )
    show_roles = models.BooleanField(
        default=True,
        help_text="Show competitive roles (main/secondary)"
    )
    show_active_hours = models.BooleanField(
        default=True,
        help_text="Show active gaming hours"
    )
    show_preferred_contact = models.BooleanField(
        default=False,
        help_text="Show preferred contact method publicly"
    )
    
    # ===== METADATA =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Privacy Settings"
        verbose_name_plural = "Privacy Settings"
    
    def __str__(self):
        return f"Privacy Settings for {self.user_profile.display_name}"
    
    def allows_viewing(self, viewer, field_name):
        """
        Check if viewer can see a specific field.
        
        Args:
            viewer: User object or None (anonymous)
            field_name: Name of the privacy setting (e.g., 'show_real_name')
        
        Returns:
            bool: True if viewer can see the field
        """
        # Owner can always see their own data
        if viewer and viewer.is_authenticated and viewer == self.user_profile.user:
            return True
        
        # Staff can always see everything
        if viewer and viewer.is_authenticated and viewer.is_staff:
            return True
        
        # Check specific privacy setting
        return getattr(self, field_name, False)


class VerificationRecord(models.Model):
    """
    KYC (Know Your Customer) verification record for user identity verification.
    Required for high-value prize tournaments and payment withdrawals.
    """
    
    VERIFICATION_STATUS_CHOICES = [
        ('unverified', 'Unverified'),
        ('pending', 'Pending Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    user_profile = models.OneToOneField(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='verification_record',
        help_text="User profile being verified"
    )
    
    # ===== VERIFICATION DOCUMENTS =====
    id_document_front = models.ImageField(
        upload_to=kyc_document_path,
        null=True,
        blank=True,
        help_text="Front side of government-issued ID (NID, Passport, Driver's License)"
    )
    id_document_back = models.ImageField(
        upload_to=kyc_document_path,
        null=True,
        blank=True,
        help_text="Back side of government-issued ID"
    )
    selfie_with_id = models.ImageField(
        upload_to=kyc_document_path,
        null=True,
        blank=True,
        help_text="Selfie holding the ID document for liveness verification"
    )
    
    # ===== VERIFICATION STATUS =====
    status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default='unverified',
        help_text="Current verification status"
    )
    
    # ===== VERIFIED DATA (Extracted from documents) =====
    verified_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Full name as shown on ID document"
    )
    verified_dob = models.DateField(
        null=True,
        blank=True,
        help_text="Date of birth from ID document"
    )
    verified_nationality = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Nationality from ID document"
    )
    id_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="ID document number (encrypted in production)"
    )
    
    # ===== REVIEW METADATA =====
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user submitted documents for review"
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When staff reviewed the submission"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kyc_reviews_performed',
        help_text="Staff member who reviewed this verification"
    )
    rejection_reason = models.TextField(
        blank=True,
        default="",
        help_text="Reason for rejection (shown to user)"
    )
    
    # ===== AUDIT =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Verification Record"
        verbose_name_plural = "Verification Records"
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"KYC for {self.user_profile.display_name} - {self.get_status_display()}"
    
    @property
    def is_verified(self):
        """Check if user is KYC verified"""
        return self.status == 'verified'
    
    @property
    def is_pending(self):
        """Check if verification is pending review"""
        return self.status == 'pending'
    
    @property
    def can_submit(self):
        """Check if user can submit/resubmit documents"""
        return self.status in ['unverified', 'rejected']
    
    def submit_for_review(self):
        """Mark verification as submitted and pending review"""
        if not self.can_submit:
            raise ValueError(f"Cannot submit verification with status: {self.status}")
        
        if not (self.id_document_front and self.id_document_back and self.selfie_with_id):
            raise ValueError("All required documents must be uploaded")
        
        self.status = 'pending'
        self.submitted_at = timezone.now()
        self.save(update_fields=['status', 'submitted_at', 'updated_at'])
    
    def approve(self, reviewed_by, verified_name, verified_dob, verified_nationality, id_number=''):
        """Approve verification and update user profile"""
        self.status = 'verified'
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewed_by
        self.verified_name = verified_name
        self.verified_dob = verified_dob
        self.verified_nationality = verified_nationality
        self.id_number = id_number
        self.rejection_reason = ''
        self.save()
        
        # Update UserProfile with verified data and lock KYC status
        profile = self.user_profile
        profile.real_full_name = verified_name
        profile.date_of_birth = verified_dob
        profile.nationality = verified_nationality
        profile.kyc_status = 'verified'
        profile.kyc_verified_at = timezone.now()
        profile.save(update_fields=[
            'real_full_name', 'date_of_birth', 'nationality',
            'kyc_status', 'kyc_verified_at', 'updated_at'
        ])
    
    def reject(self, reviewed_by, reason):
        """Reject verification with reason"""
        self.status = 'rejected'
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewed_by
        self.rejection_reason = reason
        self.save()
        
        # Update UserProfile KYC status
        profile = self.user_profile
        profile.kyc_status = 'rejected'
        profile.save(update_fields=['kyc_status', 'updated_at'])


class Badge(models.Model):
    """
    Achievement badges that users can earn.
    
    Examples:
    - First Victory (win your first match)
    - Tournament Champion (win a tournament)
    - Veteran Player (play 100 matches)
    - Perfect Score (win without losing a round)
    - Community Leader (invite 10 friends)
    """
    
    class Rarity(models.TextChoices):
        COMMON = 'common', 'Common'
        RARE = 'rare', 'Rare'
        EPIC = 'epic', 'Epic'
        LEGENDARY = 'legendary', 'Legendary'
    
    class Category(models.TextChoices):
        ACHIEVEMENT = 'achievement', 'Achievement'
        TOURNAMENT = 'tournament', 'Tournament'
        MILESTONE = 'milestone', 'Milestone'
        SPECIAL = 'special', 'Special Event'
        COMMUNITY = 'community', 'Community'
    
    # Core Fields
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(help_text="What this badge represents")
    
    # Visual
    icon = models.CharField(
        max_length=50,
        default='🏆',
        help_text="Emoji or icon identifier"
    )
    color = models.CharField(
        max_length=7,
        default='#FFD700',
        help_text="Hex color code for badge display"
    )
    
    # Classification
    rarity = models.CharField(
        max_length=20,
        choices=Rarity.choices,
        default=Rarity.COMMON
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.ACHIEVEMENT
    )
    
    # Criteria & Rewards
    criteria = models.JSONField(
        default=dict,
        help_text="""
        Earning criteria:
        {
            "type": "match_wins",
            "threshold": 10,
            "game": "valorant"  // optional
        }
        """
    )
    xp_reward = models.IntegerField(
        default=0,
        help_text="XP awarded when badge is earned"
    )
    
    # Metadata
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this badge can still be earned"
    )
    is_hidden = models.BooleanField(
        default=False,
        help_text="Hidden badges don't show in badge list until earned"
    )
    order = models.IntegerField(
        default=0,
        help_text="Display order (lower = first)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['category', 'rarity']),
            models.Index(fields=['is_active', 'is_hidden']),
        ]
    
    def __str__(self):
        return f"{self.icon} {self.name}"


class UserBadge(models.Model):
    """
    Junction table tracking which badges users have earned.
    Includes progress tracking for badges with requirements.
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_badges'
    )
    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE,
        related_name='earned_by'
    )
    
    # Progress Tracking
    earned_at = models.DateTimeField(auto_now_add=True)
    progress = models.JSONField(
        default=dict,
        help_text="""
        Progress toward earning badge:
        {
            "current": 5,
            "required": 10,
            "updated_at": "2025-11-26T12:00:00Z"
        }
        """
    )
    
    # Context
    context = models.JSONField(
        default=dict,
        blank=True,
        help_text="""
        Context about how badge was earned:
        {
            "tournament_id": 123,
            "match_id": 456,
            "game": "valorant"
        }
        """
    )
    
    # Display
    is_pinned = models.BooleanField(
        default=False,
        help_text="Whether this badge is pinned to profile showcase"
    )
    
    class Meta:
        unique_together = [['user', 'badge']]
        ordering = ['-earned_at']
        indexes = [
            models.Index(fields=['user', '-earned_at']),
            models.Index(fields=['badge', '-earned_at']),
            models.Index(fields=['user', 'is_pinned']),
        ]
    
    def __str__(self):
        return f"{self.user.username} earned {self.badge.name}"


# ============================================================================
# PHASE 3: PROFILE ENHANCEMENT MODELS
# ============================================================================

class SocialLink(models.Model):
    """
    User's connected social media platforms.
    Esports/Creator-first social links with gaming platforms.
    Frontend component: _social_links.html
    """
    
    PLATFORM_CHOICES = [
        # Streaming Platforms
        ('twitch', 'Twitch'),
        ('youtube', 'YouTube'),
        ('kick', 'Kick'),
        ('facebook_gaming', 'Facebook Gaming'),
        # Social Media
        ('twitter', 'Twitter/X'),
        ('discord', 'Discord'),
        ('instagram', 'Instagram'),
        ('tiktok', 'TikTok'),
        ('facebook', 'Facebook'),
        # Gaming Platforms
        ('steam', 'Steam'),
        ('riot', 'Riot Games'),
        # Development
        ('github', 'GitHub'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='social_links'
    )
    platform = models.CharField(
        max_length=20,
        choices=PLATFORM_CHOICES,
        help_text="Social media platform"
    )
    url = models.URLField(
        max_length=500,
        help_text="Full URL to profile"
    )
    handle = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Display name or handle (optional)"
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether this link has been verified by platform API"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['user', 'platform']]
        ordering = ['platform']
        verbose_name = "Social Link"
        verbose_name_plural = "Social Links"
    
    def __str__(self):
        return f"{self.user.username} - {self.get_platform_display()}"
    
    def clean(self):
        """Validate URL format for specific platforms"""
        url_validators = {
            'twitch': 'twitch.tv/',
            'youtube': ('youtube.com/', 'youtu.be/'),
            'twitter': ('twitter.com/', 'x.com/'),
            'discord': 'discord.gg/',
            'instagram': 'instagram.com/',
            'tiktok': 'tiktok.com/@',
            'facebook': 'facebook.com/',
            'facebook_gaming': 'facebook.com/gaming/',
            'kick': 'kick.com/',
            'steam': ('steamcommunity.com/', 'store.steampowered.com/'),
            'riot': ('tracker.gg/', 'riot.com/'),
            'github': 'github.com/',
        }
        
        if self.platform in url_validators:
            expected = url_validators[self.platform]
            if isinstance(expected, tuple):
                if not any(exp in self.url for exp in expected):
                    raise ValidationError(
                        f"{self.get_platform_display()} URL must contain one of: {', '.join(expected)}"
                    )
            else:
                if expected not in self.url:
                    raise ValidationError(
                        f"{self.get_platform_display()} URL must contain: {expected}"
                    )


class GameProfile(models.Model):
    """
    Game Passport: First-class game identity system (GP-0)
    
    Hybrid storage:
    - in_game_name: Primary identity (dedicated column)
    - identity_key: Normalized for uniqueness enforcement
    - metadata: Per-game extras (JSON)
    
    Features:
    - Global uniqueness per game (identity_key)
    - Identity change cooldown
    - Alias history tracking (GameProfileAlias)
    - Privacy levels (PUBLIC/PROTECTED/PRIVATE)
    - Pinning/ordering for showcase
    - Looking for team (is_lft) flag
    
    Frontend component: _game_passport.html
    """
    
    # Visibility choices
    VISIBILITY_PUBLIC = 'PUBLIC'
    VISIBILITY_PROTECTED = 'PROTECTED'
    VISIBILITY_PRIVATE = 'PRIVATE'
    
    VISIBILITY_CHOICES = [
        (VISIBILITY_PUBLIC, 'Public'),
        (VISIBILITY_PROTECTED, 'Protected'),
        (VISIBILITY_PRIVATE, 'Private'),
    ]
    
    # Status choices
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_SUSPENDED = 'SUSPENDED'
    
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_SUSPENDED, 'Suspended'),
    ]
    
    # Core Identity
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='game_profiles'
    )
    game = models.ForeignKey(
        'games.Game',
        on_delete=models.PROTECT,
        related_name='passports',
        help_text="Game from registry (source of truth)"
    )
    game_display_name = models.CharField(
        max_length=100,
        editable=False,
        help_text="Auto-filled from choices"
    )
    
    # GP-2A: Structured Identity Fields (First-Class Columns)
    ign = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text="In-game name / username (e.g., 'Player123' for Riot, 'SteamID64' for Steam)"
    )
    discriminator = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        db_index=True,
        help_text="Discriminator / Tag / Zone (e.g., '#NA1' for Riot, Zone ID for MLBB)"
    )
    platform = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        db_index=True,
        help_text="Platform identifier (e.g., 'PC', 'PS5', 'Xbox', platform-specific ID)"
    )
    
    # Legacy/Computed Fields
    in_game_name = models.CharField(
        max_length=100,
        help_text="Display name (computed from ign+discriminator, e.g., 'Player#TAG')"
    )
    identity_key = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Normalized identity for uniqueness (computed from ign+discriminator+region+platform, lowercase)"
    )
    
    # Rank Information
    rank_name = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Current rank (e.g., Diamond 2, Global Elite)"
    )
    rank_image = models.ImageField(
        upload_to='rank_images/',
        blank=True,
        null=True,
        help_text="Rank badge image"
    )
    rank_points = models.IntegerField(
        blank=True,
        null=True,
        help_text="LP/RR/MMR points"
    )
    rank_tier = models.IntegerField(
        default=0,
        help_text="Numeric rank tier (for sorting/comparison)"
    )
    peak_rank = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Highest rank achieved"
    )
    
    # Statistics
    matches_played = models.IntegerField(
        default=0,
        help_text="Total matches played"
    )
    win_rate = models.IntegerField(
        default=0,
        help_text="Win rate percentage (0-100)"
    )
    kd_ratio = models.FloatField(
        blank=True,
        null=True,
        help_text="Kill/Death ratio"
    )
    hours_played = models.IntegerField(
        blank=True,
        null=True,
        help_text="Total hours played"
    )
    
    # Role/Position
    main_role = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Main role/position (e.g., Duelist, Support, Mid)"
    )
    
    # Game Passport Features (GP-0)
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PUBLIC,
        help_text="Privacy level for this passport"
    )
    is_lft = models.BooleanField(
        default=False,
        help_text="Looking for team flag"
    )
    region = models.CharField(
        max_length=10,
        blank=True,
        default="",
        db_index=True,
        help_text="Player region (part of identity for some games, used for join gating)"
    )
    
    # Pinning/Ordering
    is_pinned = models.BooleanField(
        default=False,
        help_text="Whether this passport is pinned to profile"
    )
    pinned_order = models.SmallIntegerField(
        null=True,
        blank=True,
        help_text="Order for pinned passports (1-N)"
    )
    sort_order = models.SmallIntegerField(
        default=0,
        help_text="General sort order"
    )
    
    # Identity Lock (Cooldown)
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Identity cannot be changed until this date"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        help_text="Passport status"
    )
    
    # Per-game metadata (JSON)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="SHOWCASE/CONFIG ONLY - DO NOT store identity here (use ign/discriminator/region/platform columns)"
    )
    
    # Verification DEPRECATED (GP-0: Remove verification system)
    is_verified = models.BooleanField(
        default=False,
        editable=False,
        help_text="DEPRECATED: Use verification_status instead"
    )
    
    # Phase 8B: Verification status upgrade
    VERIFICATION_PENDING = 'PENDING'
    VERIFICATION_VERIFIED = 'VERIFIED'
    VERIFICATION_FLAGGED = 'FLAGGED'
    
    VERIFICATION_STATUS_CHOICES = [
        (VERIFICATION_PENDING, 'Pending Verification'),
        (VERIFICATION_VERIFIED, 'Verified'),
        (VERIFICATION_FLAGGED, 'Flagged for Review'),
    ]
    
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default=VERIFICATION_PENDING,
        db_index=True,
        help_text="Verification pipeline status: PENDING → VERIFIED or FLAGGED"
    )
    verification_notes = models.TextField(
        blank=True,
        default="",
        help_text="Admin notes for verification/flagging"
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when passport was verified"
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='verified_passports',
        help_text="Admin who verified this passport"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['user', 'game']]
        ordering = ['-is_pinned', '-pinned_order', 'sort_order', '-updated_at']
        verbose_name = "Game Passport"
        verbose_name_plural = "Game Passports"
        indexes = [
            models.Index(fields=['user', 'game']),
            models.Index(fields=['game', 'identity_key']),
            models.Index(fields=['game', '-rank_tier']),
            models.Index(fields=['-is_pinned', '-pinned_order']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['game', 'identity_key'],
                name='unique_game_identity'
            )
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.game.display_name}"
    
    @property
    def win_loss_record(self):
        """Calculate W-L record from win rate"""
        if self.matches_played == 0:
            return "0-0"
        wins = int(self.matches_played * (self.win_rate / 100))
        losses = self.matches_played - wins
        return f"{wins}-{losses}"
    
    def is_identity_locked(self) -> bool:
        """Check if identity changes are currently locked"""
        if not self.locked_until:
            return False
        return timezone.now() < self.locked_until
    
    @property
    def is_verified_computed(self) -> bool:
        """
        Phase 8B: Computed property for backward compatibility.
        Returns True if verification_status == VERIFIED.
        """
        return self.verification_status == self.VERIFICATION_VERIFIED
    
    def save(self, *args, **kwargs):
        """
        Phase 8B: Sync is_verified with verification_status.
        If is_verified is set manually (legacy code), update verification_status.
        """
        # Sync is_verified → verification_status (backward compatibility)
        if self.is_verified and self.verification_status == self.VERIFICATION_PENDING:
            self.verification_status = self.VERIFICATION_VERIFIED
            if not self.verified_at:
                self.verified_at = timezone.now()
        
        # Sync verification_status → is_verified
        self.is_verified = (self.verification_status == self.VERIFICATION_VERIFIED)
        
        # Auto-populate display name from Game model
        if not self.game_display_name and self.game:
            self.game_display_name = self.game.display_name
        
        # Auto-populate in_game_name from ign if not set
        if not self.in_game_name:
            if self.discriminator:
                self.in_game_name = f"{self.ign}{self.discriminator}"
            else:
                self.in_game_name = self.ign or ""
        
        # Generate identity_key if not set (should be set by service)
        if not self.identity_key:
            identity_key = self.in_game_name.lower().strip()
            if self.region:
                identity_key = f"{identity_key}:{self.region.lower()}"
            if self.platform:
                identity_key = f"{identity_key}:{self.platform.lower()}"
            self.identity_key = identity_key or "unknown"
        
        super().save(*args, **kwargs)


class GameProfileAlias(models.Model):
    """
    Alias history for game passport identity changes (GP-0, GP-2A)
    
    Tracks when a user changes their identity (ign/discriminator/platform/region)
    to maintain identity audit trail and prevent abuse.
    
    GP-2A: Extended to track structured identity fields.
    """
    
    game_profile = models.ForeignKey(
        GameProfile,
        on_delete=models.CASCADE,
        related_name='aliases'
    )
    
    # Legacy field (kept for backward compatibility, computed from structured fields)
    old_in_game_name = models.CharField(
        max_length=100,
        help_text="Previous in-game name (display format)"
    )
    
    # GP-2A: Structured Identity History
    old_ign = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Previous IGN/username"
    )
    old_discriminator = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text="Previous discriminator/tag/zone"
    )
    old_platform = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text="Previous platform"
    )
    old_region = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="Previous region"
    )
    
    changed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the identity was changed"
    )
    changed_by_user_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="User ID who made the change (nullable for system)"
    )
    request_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of change request"
    )
    reason = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Reason for identity change"
    )
    
    class Meta:
        ordering = ['-changed_at']
        verbose_name = "Game Profile Alias"
        verbose_name_plural = "Game Profile Aliases"
        indexes = [
            models.Index(fields=['game_profile', '-changed_at']),
        ]
    
    def __str__(self):
        return f"{self.game_profile.user.username} - {self.game_profile.game}: {self.old_in_game_name}"


class GameProfileConfig(models.Model):
    """
    Singleton configuration for Game Passport system (GP-0)
    
    Admin Command Center for managing passport behavior.
    Only one row should exist.
    """
    
    # Identity Management
    cooldown_days = models.IntegerField(
        default=30,
        help_text="Days before identity can be changed again"
    )
    allow_id_change = models.BooleanField(
        default=True,
        help_text="Whether users can change identities"
    )
    
    # Pinning Limits
    max_pinned_games = models.IntegerField(
        default=3,
        help_text="Maximum number of games a user can pin"
    )
    
    # Regional Settings
    require_region = models.BooleanField(
        default=False,
        help_text="Whether region is required for passports"
    )
    
    # Anti-Abuse (Future)
    enable_ip_smurf_detection = models.BooleanField(
        default=False,
        help_text="Enable IP-based smurf detection"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Game Passport Configuration"
        verbose_name_plural = "Game Passport Configuration"
    
    def __str__(self):
        return f"Game Passport Config (Cooldown: {self.cooldown_days} days)"
    
    @classmethod
    def get_config(cls):
        """Get or create singleton config"""
        config, created = cls.objects.get_or_create(pk=1)
        return config


class Achievement(models.Model):
    """
    Tournament achievements and trophies earned by users.
    Frontend component: _trophy_shelf.html
    """
    
    RARITY_CHOICES = [
        ('common', 'Common'),
        ('rare', 'Rare'),
        ('epic', 'Epic'),
        ('legendary', 'Legendary'),
    ]
    
    RARITY_COLORS = {
        'common': 'slate',
        'rare': 'indigo',
        'epic': 'purple',
        'legendary': 'amber',
    }
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='achievements'
    )
    name = models.CharField(
        max_length=100,
        help_text="Achievement name"
    )
    description = models.TextField(
        help_text="Achievement description"
    )
    emoji = models.CharField(
        max_length=10,
        default='🏆',
        help_text="Emoji icon for display"
    )
    icon_url = models.URLField(
        blank=True,
        default="",
        help_text="Optional custom icon URL"
    )
    rarity = models.CharField(
        max_length=20,
        choices=RARITY_CHOICES,
        default='common',
        help_text="Achievement rarity"
    )
    
    # Metadata
    earned_at = models.DateTimeField(auto_now_add=True)
    context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Context data (tournament_id, placement, etc.)"
    )
    
    class Meta:
        ordering = ['-earned_at']
        verbose_name = "Achievement"
        verbose_name_plural = "Achievements"
        indexes = [
            models.Index(fields=['user', '-earned_at']),
            models.Index(fields=['rarity', '-earned_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"
    
    @property
    def rarity_color(self):
        """Get Tailwind color for rarity"""
        return self.RARITY_COLORS.get(self.rarity, 'slate')


class Match(models.Model):
    """
    Match history records for user profiles.
    Frontend component: _match_history.html
    """
    
    RESULT_CHOICES = [
        ('win', 'Win'),
        ('loss', 'Loss'),
        ('draw', 'Draw'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='matches'
    )
    game_name = models.CharField(
        max_length=100,
        help_text="Game name"
    )
    mode = models.CharField(
        max_length=50,
        default="Competitive",
        help_text="Game mode (Competitive, Ranked, Casual)"
    )
    result = models.CharField(
        max_length=10,
        choices=RESULT_CHOICES,
        help_text="Match result"
    )
    
    # Score & Stats
    score = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Match score (e.g., 13-11)"
    )
    kda = models.CharField(
        max_length=30,
        blank=True,
        default="",
        help_text="Kill/Death/Assist (e.g., 24/12/8)"
    )
    duration = models.IntegerField(
        blank=True,
        null=True,
        help_text="Match duration in minutes"
    )
    
    # Timing
    played_at = models.DateTimeField(
        help_text="When the match was played"
    )
    
    # Context
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional match data (map, characters, tournament_id, etc.)"
    )
    
    class Meta:
        ordering = ['-played_at']
        verbose_name = "Match"
        verbose_name_plural = "Matches"
        indexes = [
            models.Index(fields=['user', '-played_at']),
            models.Index(fields=['game_name', '-played_at']),
            models.Index(fields=['result', '-played_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.game_name} ({self.result}) - {self.played_at.date()}"


class Certificate(models.Model):
    """
    Tournament certificates and awards.
    Frontend component: _certificates.html
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    title = models.CharField(
        max_length=200,
        help_text="Certificate title"
    )
    tournament_name = models.CharField(
        max_length=200,
        help_text="Tournament name"
    )
    tournament_id = models.IntegerField(
        blank=True,
        null=True,
        help_text="Tournament ID reference"
    )
    
    # Images
    image = models.ImageField(
        upload_to='certificates/',
        help_text="Full certificate image"
    )
    thumbnail_url = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Thumbnail URL (auto-generated if empty)"
    )
    
    # Verification
    issued_at = models.DateTimeField(
        help_text="When certificate was issued"
    )
    verification_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique verification code"
    )
    is_verified = models.BooleanField(
        default=True,
        help_text="Whether certificate is verified"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional certificate data (placement, prize, etc.)"
    )
    
    class Meta:
        ordering = ['-issued_at']
        verbose_name = "Certificate"
        verbose_name_plural = "Certificates"
        indexes = [
            models.Index(fields=['user', '-issued_at']),
            models.Index(fields=['verification_code']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    @property
    def tournament(self):
        """Fake tournament object for template compatibility"""
        class TournamentStub:
            def __init__(self, name):
                self.name = name
        return TournamentStub(self.tournament_name)
    
    def save(self, *args, **kwargs):
        # Generate verification code if not set
        if not self.verification_code:
            import secrets
            self.verification_code = secrets.token_urlsafe(16)
        super().save(*args, **kwargs)


# ============================================================================
# FOLLOW SYSTEM (Phase 4: Social Features)
# ============================================================================

class Follow(models.Model):
    """
    Instagram-style follower/following relationships.
    Frontend component: _followers_modal.html
    """
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='following',
        help_text="User who is following"
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='followers',
        help_text="User being followed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('follower', 'following')
        indexes = [
            models.Index(fields=['follower', 'created_at']),
            models.Index(fields=['following', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"
    
    def save(self, *args, **kwargs):
        # Prevent self-following
        if self.follower == self.following:
            raise ValueError("Users cannot follow themselves")
        super().save(*args, **kwargs)


class FollowRequest(models.Model):
    """
    Phase 6A: Follow request for private accounts.
    
    When a user tries to follow a private account, a FollowRequest is created
    with PENDING status. The target user can approve or reject the request.
    
    Workflow:
    1. User A wants to follow private User B → FollowRequest created (PENDING)
    2. User B approves → Follow relationship created, request marked APPROVED
    3. User B rejects → No Follow created, request marked REJECTED
    """
    
    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]
    
    requester = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='outgoing_follow_requests',
        help_text="User requesting to follow"
    )
    target = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='incoming_follow_requests',
        help_text="User whose approval is needed"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        help_text="Current status of the follow request"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the follow request was created"
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the request was approved or rejected"
    )
    
    class Meta:
        db_table = 'user_profile_follow_request'
        verbose_name = 'Follow Request'
        verbose_name_plural = 'Follow Requests'
        unique_together = [
            ('requester', 'target', 'status')  # Only one PENDING request per pair
        ]
        indexes = [
            models.Index(fields=['target', 'status', 'created_at']),  # List incoming requests
            models.Index(fields=['requester', 'status']),  # Track outgoing requests
            models.Index(fields=['status', 'created_at']),  # Admin queries
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(requester=models.F('target')),
                name='follow_request_no_self_request'
            )
        ]
    
    def __str__(self):
        return f"{self.requester.display_name} → {self.target.display_name} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Prevent self-follow requests
        if self.requester == self.target:
            raise ValueError("Users cannot request to follow themselves")
        super().save(*args, **kwargs)



