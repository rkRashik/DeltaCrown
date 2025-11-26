from django.db import models
from django.conf import settings
from django.utils import timezone
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

