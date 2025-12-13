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
    
    # ===== SOCIAL LINKS =====
    youtube_link = models.URLField(blank=True)
    twitch_link = models.URLField(blank=True)
    discord_id = models.CharField(max_length=64, blank=True)
    facebook = models.URLField(blank=True, default="")
    instagram = models.URLField(blank=True, default="")
    tiktok = models.URLField(blank=True, default="")
    twitter = models.URLField(blank=True, default="")
    stream_status = models.BooleanField(
        default=False,
        help_text="Automatically indicates if user is currently live on linked Twitch/YouTube"
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
    game_profiles = models.JSONField(
        default=list,
        blank=True,
        help_text="""
        JSON structure for infinite game support:
        [
            {
                "game": "valorant",
                "ign": "Player#TAG",
                "role": "Duelist",
                "rank": "Immortal 3",
                "platform": "PC",
                "is_verified": false,
                "metadata": {}
            }
        ]
        """
    )
    
    # ===== LEGACY GAME IDs (Kept for backwards compatibility, will migrate to game_profiles) =====
    riot_id = models.CharField(max_length=100, blank=True, help_text="Riot ID (Name#TAG) for Valorant")
    riot_tagline = models.CharField(max_length=50, blank=True, help_text="Riot Tagline (part after #)")
    efootball_id = models.CharField(max_length=100, blank=True, help_text="eFootball User ID")
    steam_id = models.CharField(max_length=100, blank=True, help_text="Steam ID for Dota 2, CS2")
    mlbb_id = models.CharField(max_length=100, blank=True, help_text="Mobile Legends Game ID")
    mlbb_server_id = models.CharField(max_length=50, blank=True, help_text="Mobile Legends Server ID")
    pubg_mobile_id = models.CharField(max_length=100, blank=True, help_text="PUBG Mobile Character/Player ID")
    free_fire_id = models.CharField(max_length=100, blank=True, help_text="Free Fire User/Player ID")
    ea_id = models.CharField(max_length=100, blank=True, help_text="EA ID for FC 24")
    codm_uid = models.CharField(max_length=100, blank=True, help_text="Call of Duty Mobile UID")

    # ===== PRIVACY SETTINGS (Will be moved to PrivacySettings model in Phase 2) =====
    is_private = models.BooleanField(default=False, help_text="Hide entire profile from public.")
    show_email = models.BooleanField(default=False, help_text="Allow showing my email on public profile.")
    show_phone = models.BooleanField(default=False, help_text="Allow showing my phone on public profile.")
    show_socials = models.BooleanField(default=True, help_text="Allow showing my social links/IDs on public profile.")
    show_address = models.BooleanField(default=False, help_text="Display address on public profile")
    show_age = models.BooleanField(default=True, help_text="Display age (calculated from DOB) on public profile")
    show_gender = models.BooleanField(default=False, help_text="Display gender on public profile")
    show_country = models.BooleanField(default=True, help_text="Display country on public profile")
    show_real_name = models.BooleanField(default=False, help_text="Display real full name on public profile")
    
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
        indexes = [models.Index(fields=["region"])]
        verbose_name = "User Profile"

    def __str__(self):
        return self.display_name or getattr(self.user, "username", str(self.user_id))
    
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
    
    # ===== GAME PROFILE METHODS (New Pluggable System) =====
    
    def get_game_profile(self, game_code):
        """Get game profile for a specific game."""
        for profile in self.game_profiles:
            if profile.get('game', '').lower() == game_code.lower():
                return profile
        return None
    
    def set_game_profile(self, game_code, data):
        """Set or update game profile for a specific game."""
        # Remove existing profile for this game
        self.game_profiles = [
            p for p in self.game_profiles 
            if p.get('game', '').lower() != game_code.lower()
        ]
        # Add new profile
        profile_data = {
            'game': game_code.lower(),
            'ign': data.get('ign', ''),
            'role': data.get('role', ''),
            'rank': data.get('rank', ''),
            'platform': data.get('platform', 'PC'),
            'is_verified': data.get('is_verified', False),
            'metadata': data.get('metadata', {})
        }
        self.game_profiles.append(profile_data)
        return True
    
    def add_game_profile(self, game_code, ign, role='', rank='', platform='PC', metadata=None):
        """Convenience method to add a game profile."""
        return self.set_game_profile(game_code, {
            'ign': ign,
            'role': role,
            'rank': rank,
            'platform': platform,
            'metadata': metadata or {}
        })
    
    # ===== LEGACY GAME ID METHODS (Backwards Compatibility) =====
    
    def get_game_id(self, game_code):
        """Get the appropriate game ID based on game code."""
        game_id_mapping = {
            'valorant': 'riot_id',
            'efootball': 'efootball_id',
            'dota2': 'steam_id',
            'cs2': 'steam_id',
            'mlbb': 'mlbb_id',
            'pubgm': 'pubg_mobile_id',
            'freefire': 'free_fire_id',
            'fc24': 'ea_id',
            'codm': 'codm_uid',
        }
        field_name = game_id_mapping.get(game_code.lower())
        if field_name:
            return getattr(self, field_name, '')
        return ''
    
    def set_game_id(self, game_code, value):
        """Set the appropriate game ID based on game code."""
        game_id_mapping = {
            'valorant': 'riot_id',
            'efootball': 'efootball_id',
            'dota2': 'steam_id',
            'cs2': 'steam_id',
            'mlbb': 'mlbb_id',
            'pubgm': 'pubg_mobile_id',
            'freefire': 'free_fire_id',
            'fc24': 'ea_id',
            'codm': 'codm_uid',
        }
        field_name = game_id_mapping.get(game_code.lower())
        if field_name:
            setattr(self, field_name, value)
            return True
        return False
    
    def get_game_id_label(self, game_code):
        """Get the label for the game ID field."""
        game_id_labels = {
            'valorant': 'Riot ID (Name#TAG)',
            'efootball': 'User ID',
            'dota2': 'Steam ID',
            'cs2': 'Steam ID',
            'mlbb': 'Game ID',
            'pubgm': 'Character ID',
            'freefire': 'Player ID',
            'fc24': 'EA ID',
            'codm': 'UID',
        }
        return game_id_labels.get(game_code.lower(), 'Game ID')
    
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
    user_profile = models.OneToOneField(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='privacy_settings',
        help_text="User profile these settings belong to"
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
    
    # ===== ECONOMY & INVENTORY =====
    show_inventory_value = models.BooleanField(
        default=False,
        help_text="Show total inventory/cosmetics value"
    )
    show_level_xp = models.BooleanField(
        default=True,
        help_text="Show player level and XP"
    )
    
    # ===== SOCIAL =====
    show_social_links = models.BooleanField(
        default=True,
        help_text="Show social media links (Facebook, Instagram, etc.)"
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
    Frontend component: _social_links.html
    """
    
    PLATFORM_CHOICES = [
        ('twitch', 'Twitch'),
        ('youtube', 'YouTube'),
        ('twitter', 'Twitter'),
        ('discord', 'Discord'),
        ('instagram', 'Instagram'),
        ('tiktok', 'TikTok'),
        ('facebook', 'Facebook'),
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
    User's game-specific profiles with stats and rank.
    Frontend component: _game_passport.html
    """
    
    GAME_CHOICES = [
        ('valorant', 'VALORANT'),
        ('csgo', 'CS:GO'),
        ('cs2', 'Counter-Strike 2'),
        ('lol', 'League of Legends'),
        ('dota2', 'Dota 2'),
        ('overwatch', 'Overwatch 2'),
        ('apex', 'Apex Legends'),
        ('fortnite', 'Fortnite'),
        ('pubg', 'PUBG'),
        ('r6', 'Rainbow Six Siege'),
        ('rocket_league', 'Rocket League'),
        ('mlbb', 'Mobile Legends'),
        ('codm', 'Call of Duty Mobile'),
        ('pubgm', 'PUBG Mobile'),
        ('freefire', 'Free Fire'),
        ('fc24', 'FC 24'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='game_profiles'
    )
    game = models.CharField(
        max_length=20,
        choices=GAME_CHOICES,
        help_text="Game identifier"
    )
    game_display_name = models.CharField(
        max_length=100,
        editable=False,
        help_text="Auto-filled from choices"
    )
    in_game_name = models.CharField(
        max_length=100,
        help_text="In-game username (e.g., Player#TAG)"
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
    
    # Verification
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether this profile has been verified via game API"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['user', 'game']]
        ordering = ['-updated_at']
        verbose_name = "Game Profile"
        verbose_name_plural = "Game Profiles"
        indexes = [
            models.Index(fields=['user', 'game']),
            models.Index(fields=['game', '-rank_tier']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_game_display()}"
    
    def save(self, *args, **kwargs):
        # Auto-populate display name from choices
        if not self.game_display_name:
            self.game_display_name = self.get_game_display()
        super().save(*args, **kwargs)
    
    @property
    def win_loss_record(self):
        """Calculate W-L record from win rate"""
        if self.matches_played == 0:
            return "0-0"
        wins = int(self.matches_played * (self.win_rate / 100))
        losses = self.matches_played - wins
        return f"{wins}-{losses}"


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



