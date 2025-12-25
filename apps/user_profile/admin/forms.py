"""
Custom admin forms for User Profile app

Includes:
- UserProfileAdminForm: Enhanced form with game_profiles validation
- GameProfileAdminForm: GP-1 schema-driven dynamic form for Game Passports
"""

from django import forms
from django.core.exceptions import ValidationError

from apps.user_profile.models import UserProfile, GameProfile, GamePassportSchema
from apps.user_profile.admin.game_profiles_field import GameProfilesField
from apps.games.models import Game
from apps.user_profile.validators.schema_validator import GamePassportSchemaValidator


class UserProfileAdminForm(forms.ModelForm):
    """Enhanced admin form with proper game_profiles handling"""
    
    game_profiles = GameProfilesField(
        required=False,
        label="Game Profiles",
    )
    
    class Meta:
        model = UserProfile
        fields = '__all__'
    
    def clean_game_profiles(self):
        """Additional validation for game profiles"""
        profiles = self.cleaned_data.get('game_profiles', [])
        
        # Check for duplicate game entries
        games_seen = set()
        for profile in profiles:
            game = profile.get('game', '').lower()
            if game in games_seen:
                raise forms.ValidationError(
                    f"Duplicate entry for game '{game}'. Each game can only appear once."
                )
            games_seen.add(game)
        
        return profiles


# ============================================================================
# GAME PASSPORT ADMIN FORM (GP-1)
# ============================================================================

class GameProfileAdminForm(forms.ModelForm):
    """
    GP-2A Game Passport Admin Form
    
    Schema-driven form with structured identity fields:
    - Shows only games from games.Game (source of truth)
    - Uses ign/discriminator/platform/region columns (not JSON)
    - Validates with GamePassportSchemaValidator.validate_structured()
    - Populates region/rank/role choices from schema
    - Enforces server-side validation with normalization
    """
    
    # GP-2A: Structured identity fields (replace identity_data JSON)
    ign = forms.CharField(
        required=False,
        max_length=64,
        label="IGN / Username",
        help_text="In-game name or username (primary identity field)"
    )
    discriminator = forms.CharField(
        required=False,
        max_length=32,
        label="Discriminator / Tag",
        help_text="Tag line, zone ID, or discriminator (for Riot, MLBB)"
    )
    platform = forms.CharField(
        required=False,
        max_length=32,
        label="Platform",
        help_text="Platform identifier (for cross-platform games like EA FC, R6)"
    )
    region = forms.ChoiceField(
        required=False,
        label="Region",
        help_text="Player region (choices from game schema)",
        choices=[('', '---------')]  # Default empty choice, populated in __init__
    )
    
    class Meta:
        model = GameProfile
        fields = [
            'user',
            'game',
            'in_game_name',
            'ign',
            'discriminator',
            'platform',
            'region',
            'rank_name',
            'visibility',
            'is_lft',
            'is_pinned',
            'pinned_order',
            'status',
            'metadata',
        ]
        widgets = {
            'metadata': forms.Textarea(attrs={'rows': 3, 'cols': 50}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Limit game choices to passport-supported games only (TASK A requirement)
        passport_supported_games = Game.objects.filter(
            is_passport_supported=True,
            is_active=True
        ).order_by('display_name')
        
        self.fields['game'].queryset = passport_supported_games
        self.fields['game'].help_text = (
            'Select a game from the registry (only passport-supported games shown). '
            'Identity fields will adapt to your selection.'
        )
        
        # Admin warning if unsupported games exist
        total_games = Game.objects.filter(is_active=True).count()
        if total_games > passport_supported_games.count():
            unsupported_count = total_games - passport_supported_games.count()
            self.fields['game'].help_text += f' ({unsupported_count} unsupported games hidden)'
        
        # If editing existing passport, populate structured fields
        if self.instance and self.instance.pk:
            self._populate_structured_fields_from_instance()
            self._populate_region_choices()  # GP-2D: Populate region dropdown from schema
        
        # If creating new passport and game is in POST data, populate region choices
        if not self.instance.pk and 'game' in self.data:
            self._populate_region_choices_from_post()
        
        # Make in_game_name optional (auto-computed from ign/discriminator)
        self.fields['in_game_name'].help_text = 'Display name (auto-computed from identity fields if left blank)'
        self.fields['in_game_name'].required = False
        
        # Remove role-related help text (GP-2D: role removed from passport)
        self.fields['rank_name'].help_text = 'Current rank (free text or select from schema choices)'
    
    def _populate_structured_fields_from_instance(self):
        """
        Populate structured identity fields from existing passport.
        GP-2A: Columns are already populated by migration.
        """
        if self.instance.ign:
            self.initial['ign'] = self.instance.ign
        if self.instance.discriminator:
            self.initial['discriminator'] = self.instance.discriminator
        if self.instance.platform:
            self.initial['platform'] = self.instance.platform
        if self.instance.region:
            self.initial['region'] = self.instance.region
    
    # GP-2E: _customize_field_labels_for_game() removed
    # All label customization now handled by GP-2D JavaScript (schema-driven)
    
    def _populate_region_choices(self):
        """
        GP-2D: Populate region dropdown from GamePassportSchema.
        Called when editing an existing passport.
        """
        if not self.instance or not self.instance.game:
            return
        
        try:
            schema = GamePassportSchema.objects.get(game=self.instance.game)
            choices = [('', '---------')]
            choices.extend(schema.get_region_choices_for_form())
            self.fields['region'].choices = choices
            self.fields['region'].required = schema.region_required
        except GamePassportSchema.DoesNotExist:
            # No schema: allow free text via CharField
            self.fields['region'].widget = forms.TextInput()
    
    def _populate_region_choices_from_post(self):
        """
        GP-2D: Populate region dropdown when creating new passport.
        Called when form is submitted with a game selection.
        """
        try:
            game_id = self.data.get('game')
            if game_id:
                game = Game.objects.get(pk=game_id)
                schema = GamePassportSchema.objects.get(game=game)
                choices = [('', '---------')]
                choices.extend(schema.get_region_choices_for_form())
                self.fields['region'].choices = choices
                self.fields['region'].required = schema.region_required
        except (Game.DoesNotExist, GamePassportSchema.DoesNotExist, ValueError):
            # No game selected or no schema: keep default empty dropdown
            pass
    
    def clean(self):
        """GP-2A Schema-driven validation using structured identity fields"""
        cleaned_data = super().clean()
        game = cleaned_data.get('game')
        ign = cleaned_data.get('ign')
        discriminator = cleaned_data.get('discriminator')
        platform = cleaned_data.get('platform')
        region = cleaned_data.get('region')
        role = cleaned_data.get('main_role')
        user = cleaned_data.get('user')
        
        if not game:
            return cleaned_data
        
        # Use GP-2A structured validator (single source of truth)
        result = GamePassportSchemaValidator.validate_structured(
            game=game,
            ign=ign,
            discriminator=discriminator,
            platform=platform,
            region=region,
            main_role=role,
            user=user,
            passport_id=self.instance.pk if self.instance else None
        )
        
        if not result.is_valid:
            # Convert validation errors to form errors
            form_errors = {}
            for field_name, error_msg in result.errors.items():
                # Map validation field names to form field names
                if field_name in ['ign', 'discriminator', 'platform', 'region', 'main_role']:
                    form_errors[field_name] = error_msg
                else:
                    form_errors[field_name] = error_msg
            
            raise ValidationError(form_errors)
        
        # Set computed values from validation result
        if not cleaned_data.get('in_game_name'):
            cleaned_data['in_game_name'] = result.in_game_name
        cleaned_data['identity_key'] = result.identity_key
        
        # Store validated structured fields
        cleaned_data['ign'] = result.ign or ign
        cleaned_data['discriminator'] = result.discriminator or discriminator
        cleaned_data['platform'] = result.platform or platform
        
        # metadata should only contain showcase fields (NOT identity)
        # Keep any existing metadata, don't overwrite with identity
        if 'metadata' not in cleaned_data or cleaned_data['metadata'] is None:
            cleaned_data['metadata'] = {}
        
        return cleaned_data
    
    def save(self, commit=True):
        """
        Save with computed values from GP-2A validation.
        Structured identity fields are saved to columns, not metadata.
        """
        instance = super().save(commit=False)
        
        # Set computed fields from clean()
        if hasattr(self, 'cleaned_data'):
            instance.identity_key = self.cleaned_data.get('identity_key', instance.identity_key)
            instance.ign = self.cleaned_data.get('ign', instance.ign)
            instance.discriminator = self.cleaned_data.get('discriminator', instance.discriminator)
            instance.platform = self.cleaned_data.get('platform', instance.platform)
            # metadata only contains showcase fields, not identity
            instance.metadata = self.cleaned_data.get('metadata', instance.metadata)
        
        if commit:
            instance.save()
        
        return instance
