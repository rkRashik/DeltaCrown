"""
Tournament Form Configuration Model

Stores the registration form setup for each tournament, including:
- Form type selection (default solo/team or custom)
- Toggleable field configurations
- Dynamic communication channels (organizer-defined)
- Coordinator role configuration
- Member information requirements
- Roster display options
- Custom form reference
"""

from django.db import models
from django.core.exceptions import ValidationError
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.form_template import RegistrationFormTemplate


class TournamentFormConfiguration(models.Model):
    """
    Configuration for tournament registration form.

    Drives the SmartRegistrationView's field visibility, required/optional
    status, and dynamic channel/question rendering.  Organizers can
    customise every aspect of the registration experience via the admin
    inline or (future) Organizer Console.
    """

    # Form Type Choices
    FORM_TYPE_DEFAULT_SOLO = 'default_solo'
    FORM_TYPE_DEFAULT_TEAM = 'default_team'
    FORM_TYPE_CUSTOM = 'custom'

    FORM_TYPE_CHOICES = [
        (FORM_TYPE_DEFAULT_SOLO, 'Default Solo Registration'),
        (FORM_TYPE_DEFAULT_TEAM, 'Default Team Registration'),
        (FORM_TYPE_CUSTOM, 'Custom Registration Form'),
    ]

    # ═══════════════════════════════════════════════
    # RELATIONSHIPS
    # ═══════════════════════════════════════════════

    tournament = models.OneToOneField(
        Tournament,
        on_delete=models.CASCADE,
        related_name='form_configuration',
        help_text='Tournament this form configuration belongs to',
    )

    custom_form = models.ForeignKey(
        RegistrationFormTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tournament_configurations',
        help_text='Custom form template (if form_type is custom)',
    )

    form_type = models.CharField(
        max_length=20,
        choices=FORM_TYPE_CHOICES,
        default=FORM_TYPE_DEFAULT_SOLO,
        help_text='Type of registration form to use',
    )

    # ═══════════════════════════════════════════════
    # COORDINATOR ROLE CONFIGURATION
    # ═══════════════════════════════════════════════

    COORDINATOR_ROLE_CHOICES = [
        ('captain', 'Team Captain / IGL'),
        ('manager', 'Team Manager'),
        ('coach', 'Coach'),
        ('other', 'Other'),
    ]

    enable_coordinator_role = models.BooleanField(
        default=True,
        help_text='Show coordinator role selector (IGL, Captain, Manager, etc.)',
    )
    coordinator_role_choices = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Custom role options. '
            'Schema: [{"key":"captain","label":"Captain / IGL","description":"Leads in-game strategy"}]. '
            'Leave empty to use defaults.'
        ),
    )
    coordinator_help_text = models.TextField(
        blank=True,
        default='',
        help_text='Custom help text explaining what a Match Coordinator does. Shown as an info tooltip.',
    )

    # ═══════════════════════════════════════════════
    # DYNAMIC COMMUNICATION CHANNELS
    # ═══════════════════════════════════════════════

    communication_channels = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Organizer-defined communication channels for the registration form. '
            'Schema: [{"key":"discord","label":"Discord ID","placeholder":"Username#0000",'
            '"icon":"discord","required":true,"type":"text"}]. '
            'Leave empty to use built-in defaults (Phone + Discord).'
        ),
    )
    enable_preferred_communication = models.BooleanField(
        default=False,
        help_text='Show "Preferred Communication Method" dropdown in the form.',
    )

    # ═══════════════════════════════════════════════
    # TEAM INFO CONFIGURATION
    # ═══════════════════════════════════════════════

    enable_team_logo_upload = models.BooleanField(
        default=False,
        help_text='Allow team to upload/replace logo during registration.',
    )
    enable_team_banner_upload = models.BooleanField(
        default=False,
        help_text='Allow team to upload/replace banner during registration.',
    )
    enable_team_bio = models.BooleanField(
        default=False,
        help_text='Show team bio/motto text field.',
    )

    # ═══════════════════════════════════════════════
    # MEMBER / ROSTER INFO REQUIREMENTS
    # ═══════════════════════════════════════════════

    require_member_real_name = models.BooleanField(
        default=False,
        help_text='Require real name for each roster member.',
    )
    require_member_photo = models.BooleanField(
        default=False,
        help_text='Require photo for each roster member (common for LAN/official).',
    )
    require_member_email = models.BooleanField(
        default=False,
        help_text='Require email address for each roster member.',
    )
    require_member_age = models.BooleanField(
        default=False,
        help_text='Require age / date of birth for each roster member.',
    )
    require_member_national_id = models.BooleanField(
        default=False,
        help_text='Require national ID / passport number for each member (LAN tournaments).',
    )
    member_custom_fields = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Additional per-member fields defined by organizer. '
            'Schema: [{"key":"jersey_number","label":"Jersey Number","type":"text","required":false}].'
        ),
    )
    allow_roster_editing = models.BooleanField(
        default=True,
        help_text='Allow the coordinator to edit lineup (swap starters/subs, reorder) during registration.',
    )
    show_member_ranks = models.BooleanField(
        default=True,
        help_text='Display each member\'s current rank in the roster panel.',
    )
    show_member_game_ids = models.BooleanField(
        default=True,
        help_text='Display each member\'s game ID in the roster panel.',
    )
    
    # ═══════════════════════════════════════════════
    # LEGACY TOGGLEABLE FIELDS — SOLO
    # (Kept for backward compat; prefer communication_channels)
    # ═══════════════════════════════════════════════
    
    # Personal Details (Toggleable)
    enable_age_field = models.BooleanField(
        default=False,
        help_text='Ask for participant age (13+ validation)'
    )
    
    enable_country_field = models.BooleanField(
        default=False,
        help_text='Ask for country/region selection'
    )
    
    # Game Details (Toggleable)
    enable_platform_field = models.BooleanField(
        default=False,
        help_text='Ask for platform/server (e.g., APAC, NA, EU)'
    )
    
    enable_rank_field = models.BooleanField(
        default=False,
        help_text='Ask for current game rank (optional)'
    )
    
    # Contact Information (Toggleable)
    enable_phone_field = models.BooleanField(
        default=False,
        help_text='Ask for WhatsApp/phone number'
    )
    
    enable_discord_field = models.BooleanField(
        default=False,
        help_text='Ask for Discord username'
    )
    
    enable_preferred_contact_field = models.BooleanField(
        default=False,
        help_text='Ask for preferred contact method'
    )
    
    # ===========================================
    # LEGACY TOGGLEABLE FIELDS FOR TEAM REGISTRATION
    # ===========================================
    
    # Team Overview (Toggleable)
    enable_team_logo_field = models.BooleanField(
        default=False,
        help_text='Allow team logo upload'
    )
    
    enable_team_region_field = models.BooleanField(
        default=False,
        help_text='Ask for team region'
    )
    
    # Captain Information (Toggleable)
    enable_captain_display_name_field = models.BooleanField(
        default=False,
        help_text='Ask for captain nickname/display name'
    )
    
    enable_captain_whatsapp_field = models.BooleanField(
        default=False,
        help_text='Ask for captain WhatsApp number'
    )
    
    enable_captain_phone_field = models.BooleanField(
        default=False,
        help_text='Ask for captain phone number'
    )
    
    enable_captain_discord_field = models.BooleanField(
        default=False,
        help_text='Ask for captain Discord username'
    )
    
    # Team Roster (Toggleable)
    enable_roster_display_names = models.BooleanField(
        default=False,
        help_text='Ask for display names for all team members'
    )
    
    enable_roster_emails = models.BooleanField(
        default=False,
        help_text='Ask for email addresses for all team members'
    )
    
    # Payment (Toggleable)
    enable_payment_mobile_number_field = models.BooleanField(
        default=False,
        help_text='Ask for mobile number used for payment'
    )
    
    enable_payment_screenshot_field = models.BooleanField(
        default=True,  # Default enabled for manual payments
        help_text='Allow payment screenshot upload'
    )
    
    enable_payment_notes_field = models.BooleanField(
        default=False,
        help_text='Allow optional payment notes'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Tournament Form Configuration'
        verbose_name_plural = 'Tournament Form Configurations'
        db_table = 'tournaments_form_configuration'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.tournament.name} - {self.get_form_type_display()}"
    
    def clean(self):
        """Validate form configuration"""
        super().clean()
        
        # If custom form selected, custom_form must be set
        if self.form_type == self.FORM_TYPE_CUSTOM and not self.custom_form:
            raise ValidationError({
                'custom_form': 'Custom form template is required when form type is Custom.'
            })
        
        # If not custom, custom_form should be None
        if self.form_type != self.FORM_TYPE_CUSTOM and self.custom_form:
            raise ValidationError({
                'custom_form': 'Custom form should only be set when form type is Custom.'
            })
    
    def get_enabled_solo_fields(self):
        """Get list of enabled optional fields for solo registration"""
        enabled_fields = []
        
        # Personal Details
        if self.enable_age_field:
            enabled_fields.append('age')
        if self.enable_country_field:
            enabled_fields.append('country')
        
        # Game Details
        if self.enable_platform_field:
            enabled_fields.append('platform')
        if self.enable_rank_field:
            enabled_fields.append('rank')
        
        # Contact Information
        if self.enable_phone_field:
            enabled_fields.append('phone')
        if self.enable_discord_field:
            enabled_fields.append('discord')
        if self.enable_preferred_contact_field:
            enabled_fields.append('preferred_contact')
        
        return enabled_fields
    
    def get_enabled_team_fields(self):
        """Get list of enabled optional fields for team registration"""
        enabled_fields = []
        
        # Team Overview
        if self.enable_team_logo_field:
            enabled_fields.append('team_logo')
        if self.enable_team_region_field:
            enabled_fields.append('team_region')
        
        # Captain Information
        if self.enable_captain_display_name_field:
            enabled_fields.append('captain_display_name')
        if self.enable_captain_whatsapp_field:
            enabled_fields.append('captain_whatsapp')
        if self.enable_captain_phone_field:
            enabled_fields.append('captain_phone')
        if self.enable_captain_discord_field:
            enabled_fields.append('captain_discord')
        
        # Roster
        if self.enable_roster_display_names:
            enabled_fields.append('roster_display_names')
        if self.enable_roster_emails:
            enabled_fields.append('roster_emails')
        
        return enabled_fields
    
    def get_enabled_payment_fields(self):
        """Get list of enabled optional payment fields"""
        enabled_fields = []
        
        if self.enable_payment_mobile_number_field:
            enabled_fields.append('payment_mobile_number')
        if self.enable_payment_screenshot_field:
            enabled_fields.append('payment_screenshot')
        if self.enable_payment_notes_field:
            enabled_fields.append('payment_notes')
        
        return enabled_fields
    
    @classmethod
    def get_or_create_for_tournament(cls, tournament):
        """
        Get existing configuration or create default one.

        Determines default form type based on tournament participation type.
        """
        config, created = cls.objects.get_or_create(
            tournament=tournament,
            defaults={
                'form_type': cls.FORM_TYPE_DEFAULT_TEAM if tournament.participation_type == 'team' else cls.FORM_TYPE_DEFAULT_SOLO,
            },
        )
        return config

    # ───────────────────────────────────────────────
    # Dynamic Helpers
    # ───────────────────────────────────────────────

    DEFAULT_COMMUNICATION_CHANNELS = [
        {
            'key': 'phone',
            'label': 'Phone / WhatsApp',
            'placeholder': 'Your phone number',
            'icon': 'phone',
            'required': True,
            'type': 'tel',
        },
        {
            'key': 'discord',
            'label': 'Discord ID',
            'placeholder': 'Username#0000',
            'icon': 'discord',
            'required': False,
            'type': 'text',
        },
    ]

    DEFAULT_COORDINATOR_ROLES = [
        {'key': 'captain', 'label': 'Captain / IGL', 'description': 'In-game leader who calls strategies and coordinates the team during matches.'},
        {'key': 'manager', 'label': 'Team Manager', 'description': 'Manages team logistics, scheduling, and communication with tournament admins.'},
        {'key': 'coach', 'label': 'Coach', 'description': 'Analyses gameplay and guides the team — may not play in matches.'},
        {'key': 'other', 'label': 'Other', 'description': 'A designated person responsible for tournament coordination.'},
    ]

    def get_communication_channels(self):
        """Return resolved communication channels (custom or defaults)."""
        if self.communication_channels:
            return self.communication_channels
        return list(self.DEFAULT_COMMUNICATION_CHANNELS)

    def get_coordinator_roles(self):
        """Return coordinator role options (custom or defaults)."""
        if self.coordinator_role_choices:
            return self.coordinator_role_choices
        return list(self.DEFAULT_COORDINATOR_ROLES)

    def get_coordinator_help(self):
        """Return coordinator help text (custom or default)."""
        if self.coordinator_help_text:
            return self.coordinator_help_text
        return (
            'The Match Coordinator is the primary contact person for this registration. '
            'They will receive match schedules, communicate with tournament admins, '
            'and are responsible for ensuring the team is ready for each match.'
        )

    def get_member_custom_fields_list(self):
        """Return per-member custom fields."""
        return self.member_custom_fields or []

    def to_template_context(self):
        """
        Serialize the full form configuration as a template-friendly dict.
        Used by SmartRegistrationView._build_context().
        """
        return {
            'form_type': self.form_type,
            # Coordinator
            'enable_coordinator_role': self.enable_coordinator_role,
            'coordinator_roles': self.get_coordinator_roles(),
            'coordinator_help': self.get_coordinator_help(),
            # Communication
            'channels': self.get_communication_channels(),
            'enable_preferred_communication': self.enable_preferred_communication,
            # Team info
            'enable_team_logo_upload': self.enable_team_logo_upload,
            'enable_team_banner_upload': self.enable_team_banner_upload,
            'enable_team_bio': self.enable_team_bio,
            # Member requirements
            'require_member_real_name': self.require_member_real_name,
            'require_member_photo': self.require_member_photo,
            'require_member_email': self.require_member_email,
            'require_member_age': self.require_member_age,
            'require_member_national_id': self.require_member_national_id,
            'member_custom_fields': self.get_member_custom_fields_list(),
            'allow_roster_editing': self.allow_roster_editing,
            'show_member_ranks': self.show_member_ranks,
            'show_member_game_ids': self.show_member_game_ids,
            # Legacy toggles
            'enable_age_field': self.enable_age_field,
            'enable_country_field': self.enable_country_field,
            'enable_platform_field': self.enable_platform_field,
            'enable_rank_field': self.enable_rank_field,
            'enable_phone_field': self.enable_phone_field,
            'enable_discord_field': self.enable_discord_field,
            'enable_preferred_contact_field': self.enable_preferred_contact_field,
            'enable_team_logo_field': self.enable_team_logo_field,
            'enable_team_region_field': self.enable_team_region_field,
            'enable_captain_display_name_field': self.enable_captain_display_name_field,
            'enable_captain_whatsapp_field': self.enable_captain_whatsapp_field,
            'enable_captain_phone_field': self.enable_captain_phone_field,
            'enable_captain_discord_field': self.enable_captain_discord_field,
            'enable_roster_display_names': self.enable_roster_display_names,
            'enable_roster_emails': self.enable_roster_emails,
            'enable_payment_mobile_number_field': self.enable_payment_mobile_number_field,
            'enable_payment_screenshot_field': self.enable_payment_screenshot_field,
            'enable_payment_notes_field': self.enable_payment_notes_field,
        }
