"""
Tournament Form Configuration Model

Stores the registration form setup for each tournament, including:
- Form type selection (default solo/team or custom)
- Toggleable field configurations
- Custom form reference
"""

from django.db import models
from django.core.exceptions import ValidationError
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.form_template import RegistrationFormTemplate


class TournamentFormConfiguration(models.Model):
    """
    Configuration for tournament registration form.
    
    Defines which form type to use and which optional fields are enabled.
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
    
    # Relationships
    tournament = models.OneToOneField(
        Tournament,
        on_delete=models.CASCADE,
        related_name='form_configuration',
        help_text='Tournament this form configuration belongs to'
    )
    
    custom_form = models.ForeignKey(
        RegistrationFormTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tournament_configurations',
        help_text='Custom form template (if form_type is custom)'
    )
    
    # Form Type Selection
    form_type = models.CharField(
        max_length=20,
        choices=FORM_TYPE_CHOICES,
        default=FORM_TYPE_DEFAULT_SOLO,
        help_text='Type of registration form to use'
    )
    
    # ===========================================
    # TOGGLEABLE FIELDS FOR SOLO REGISTRATION
    # ===========================================
    
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
    # TOGGLEABLE FIELDS FOR TEAM REGISTRATION
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
            }
        )
        return config
