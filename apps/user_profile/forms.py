# apps/user_profile/forms.py
from __future__ import annotations

from django import forms
from django.apps import apps


UserProfile = apps.get_model("user_profile", "UserProfile")


class UserProfileForm(forms.ModelForm):
    """Modern comprehensive user profile form"""
    
    class Meta:
        model = UserProfile
        fields = [
            # Public Identity
            'avatar', 'banner', 'display_name', 'slug', 'region', 'bio',
            
            # Legal Identity (for KYC)
            'real_full_name', 'date_of_birth', 'nationality',
            
            # Contact & Location
            'phone', 'country', 'city', 'postal_code', 'address',
            
            # Demographics
            'gender',
            
            # Emergency Contact
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation',
            
            # UP.2 C2 CLEANUP: Legacy social media fields removed (2026-01-15)
            # Social links now managed via SocialLink model and inline forms
            
            # Platform Preferences (Phase 6 Part C)
            'preferred_language', 'timezone_pref', 'time_format', 'theme_preference',
            
            # Note: Legacy game ID fields migrated to Game Passport system
            # Game-specific identities now managed via GameProfile model
            # Note: Privacy settings managed via PrivacySettings model (not on UserProfile)
        ]
        
        widgets = {
            # Public Identity
            'display_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your display name'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'custom-url-slug (e.g., legend-gamer)'
            }),
            'region': forms.Select(attrs={
                'class': 'form-input'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-input',
                'placeholder': 'Tell others about yourself...',
                'rows': 4
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'file-input',
                'accept': 'image/*'
            }),
            'banner': forms.FileInput(attrs={
                'class': 'file-input',
                'accept': 'image/*'
            }),
            
            # Legal Identity
            'real_full_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Full legal name (for certificates & prizes)'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'nationality': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Bangladeshi, Indian, etc.'
            }),
            
            # Contact & Location
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+8801XXXXXXXXX (for bKash/Nagad)'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Bangladesh'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Dhaka'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '1200'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-input',
                'placeholder': 'Full address for prize shipping...',
                'rows': 3
            }),
            
            # Demographics
            'gender': forms.Select(attrs={
                'class': 'form-input'
            }),
            
            # Emergency Contact
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Guardian/Parent/Spouse name'
            }),
            'emergency_contact_phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+8801XXXXXXXXX'
            }),
            'emergency_contact_relation': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Father, Mother, Spouse, etc.'
            }),
            
            # UP.2 C2 CLEANUP: Social Media widgets removed (2026-01-15)
            # Social links now managed via SocialLink model
            
            # Platform Preferences
            'preferred_language': forms.Select(attrs={
                'class': 'form-input'
            }),
            'timezone_pref': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Asia/Dhaka'
            }),
            'time_format': forms.Select(attrs={
                'class': 'form-input'
            }),
            'theme_preference': forms.Select(attrs={
                'class': 'form-input'
            }),
        }
        
        help_texts = {
            # Public Identity
            'display_name': 'This is how your name will appear on your profile and in teams.',
            'slug': 'Custom URL for your profile (e.g., deltacrown.com/u/your-slug). Leave blank for auto-generated.',
            'region': 'Select your primary gaming region.',
            'bio': 'A brief description about yourself and your gaming interests.',
            'banner': 'Banner image for your profile page (recommended: 1920x480px).',
            
            # Legal Identity
            'real_full_name': 'Your full legal name (required for tournament certificates and prize verification).',
            'date_of_birth': 'Your date of birth (for age verification and tournament eligibility).',
            'nationality': 'Your citizenship/nationality (may differ from country of residence).',
            
            # Contact & Location
            'phone': 'Phone number for SMS notifications and bKash/Nagad payments (e.g., +8801XXXXXXXXX).',
            'country': 'Your country of residence (for regional tournaments).',
            'city': 'Your city (for local meetups and events).',
            'postal_code': 'Postal/ZIP code for prize shipping.',
            'address': 'Full street address (required for physical prize shipping).',
            
            # Demographics
            'gender': 'Your gender (optional, for diversity statistics).',
            
            # Emergency Contact
            'emergency_contact_name': 'Name of person to contact in case of emergency during in-person events.',
            'emergency_contact_phone': 'Emergency contact phone number.',
            'emergency_contact_relation': 'Relationship to emergency contact (e.g., Father, Mother, Spouse).',
            
            # UP.2 C2 CLEANUP: Social Media help_texts removed (2026-01-15)
            # Social links now managed via SocialLink model
            
            # Platform Preferences
            'preferred_language': 'Your preferred language for the UI (currently only English is fully supported).',
            'timezone_pref': 'Your timezone for displaying times (e.g., Asia/Dhaka, UTC, America/New_York).',
            'time_format': 'Display times in 12-hour (3:00 PM) or 24-hour (15:00) format.',
            'theme_preference': 'Choose your preferred theme (Light, Dark, or match your system settings).',
        }


class KYCUploadForm(forms.ModelForm):
    """
    Form for users to upload KYC verification documents.
    Requires: ID front, ID back, and selfie with ID.
    """
    
    class Meta:
        model = apps.get_model("user_profile", "VerificationRecord")
        fields = ['id_document_front', 'id_document_back', 'selfie_with_id']
        
        widgets = {
            'id_document_front': forms.FileInput(attrs={
                'class': 'file-input',
                'accept': 'image/*,.pdf',
                'required': True
            }),
            'id_document_back': forms.FileInput(attrs={
                'class': 'file-input',
                'accept': 'image/*,.pdf',
                'required': True
            }),
            'selfie_with_id': forms.FileInput(attrs={
                'class': 'file-input',
                'accept': 'image/*',
                'required': True
            }),
        }
        
        help_texts = {
            'id_document_front': 'Upload clear photo of the front of your National ID/Passport (JPG, PNG, or PDF)',
            'id_document_back': 'Upload clear photo of the back of your National ID (JPG, PNG, or PDF)',
            'selfie_with_id': 'Upload a selfie holding your ID next to your face (JPG or PNG)',
        }
        
        labels = {
            'id_document_front': 'ID Document - Front Side',
            'id_document_back': 'ID Document - Back Side',
            'selfie_with_id': 'Selfie with ID',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        front = cleaned_data.get('id_document_front')
        back = cleaned_data.get('id_document_back')
        selfie = cleaned_data.get('selfie_with_id')
        
        # Ensure all documents are provided
        if not all([front, back, selfie]):
            raise forms.ValidationError(
                "All three documents are required for KYC verification."
            )
        
        # File size validation (max 5MB per file)
        max_size = 5 * 1024 * 1024  # 5MB
        for field_name, file_obj in [('id_document_front', front), 
                                       ('id_document_back', back), 
                                       ('selfie_with_id', selfie)]:
            if file_obj and hasattr(file_obj, 'size') and file_obj.size > max_size:
                raise forms.ValidationError(
                    f"{field_name}: File size must not exceed 5MB. Your file is {file_obj.size / 1024 / 1024:.1f}MB."
                )
        
        return cleaned_data


class PrivacySettingsForm(forms.ModelForm):
    """
    Form for users to control their profile privacy settings.
    Provides granular control over what information is visible to others.
    """
    
    class Meta:
        model = apps.get_model("user_profile", "PrivacySettings")
        fields = [
            # Profile Visibility
            'show_real_name', 'show_phone', 'show_email', 'show_age', 
            'show_gender', 'show_country', 'show_address',
            # Gaming & Activity
            'show_game_ids', 'show_match_history', 'show_teams', 'show_achievements',
            # Economy & Inventory
            'show_inventory_value', 'show_level_xp',
            # Social
            'show_social_links',
            # Interaction Permissions
            'allow_team_invites', 'allow_friend_requests', 'allow_direct_messages',
        ]
        
        widgets = {
            # All fields are checkboxes
            field: forms.CheckboxInput(attrs={'class': 'form-checkbox h-4 w-4'})
            for field in [
                'show_real_name', 'show_phone', 'show_email', 'show_age', 
                'show_gender', 'show_country', 'show_address',
                'show_game_ids', 'show_match_history', 'show_teams', 'show_achievements',
                'show_inventory_value', 'show_level_xp', 'show_social_links',
                'allow_team_invites', 'allow_friend_requests', 'allow_direct_messages',
            ]
        }
        
        labels = {
            # Profile Visibility
            'show_real_name': 'Show Real Name',
            'show_phone': 'Show Phone Number',
            'show_email': 'Show Email Address',
            'show_age': 'Show Age',
            'show_gender': 'Show Gender',
            'show_country': 'Show Country',
            'show_address': 'Show Full Address',
            # Gaming & Activity
            'show_game_ids': 'Show Game IDs',
            'show_match_history': 'Show Match History',
            'show_teams': 'Show Teams',
            'show_achievements': 'Show Achievements & Badges',
            # Economy & Inventory
            'show_inventory_value': 'Show Inventory Value',
            'show_level_xp': 'Show Level & XP',
            # Social
            'show_social_links': 'Show Social Media Links',
            # Interaction Permissions
            'allow_team_invites': 'Allow Team Invitations',
            'allow_friend_requests': 'Allow Friend Requests',
            'allow_direct_messages': 'Allow Direct Messages',
        }
        
        help_texts = {
            'show_real_name': 'Display your legal name on your public profile',
            'show_phone': 'Display your phone number on your public profile',
            'show_email': 'Display your email address on your public profile',
            'show_address': 'Display your full address on your public profile',
            'show_game_ids': 'Display your in-game IDs (Riot ID, PUBG ID, etc.) on your profile',
            'show_match_history': 'Display your tournament match history to other users',
            'show_teams': 'Display the teams you are part of on your profile',
            'show_achievements': 'Display your earned badges and achievements',
            'show_inventory_value': 'Display the total value of your in-game inventory',
            'allow_team_invites': 'Allow team captains to send you team invitations',
            'allow_friend_requests': 'Allow other users to send you friend requests',
            'allow_direct_messages': 'Allow other users to send you direct messages',
        }


# ============================================================================
# PHASE 4: COMPREHENSIVE SETTINGS FORMS
# ============================================================================

class UserProfileSettingsForm(forms.ModelForm):
    """
    Comprehensive profile settings form covering all tabs:
    - Identity, Connections, Social, Platform, About
    Phase 4B: Replaces manual POST extraction with proper form validation.
    UP.2 C2 CLEANUP: Social links now managed via SocialLink model
    """
    
    # Popular languages list for communication_languages multi-select
    LANGUAGE_CHOICES = [
        ('English', 'English'),
        ('Bengali', 'Bengali'),
        ('Hindi', 'Hindi'),
        ('Urdu', 'Urdu'),
        ('Arabic', 'Arabic'),
        ('German', 'German'),
        ('French', 'French'),
        ('Spanish', 'Spanish'),
        ('Portuguese', 'Portuguese'),
        ('Russian', 'Russian'),
        ('Turkish', 'Turkish'),
        ('Malay', 'Malay'),
        ('Indonesian', 'Indonesian'),
        ('Japanese', 'Japanese'),
        ('Korean', 'Korean'),
        ('Chinese', 'Chinese'),
        ('Italian', 'Italian'),
    ]
    
    communication_languages = forms.MultipleChoiceField(
        choices=LANGUAGE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'language-checkbox'}),
        required=False,
        help_text='Select all languages you can communicate in'
    )
    
    class Meta:
        model = UserProfile
        fields = [
            # Identity Tab
            'display_name', 'gender', 'pronouns', 'name_pronunciation', 'city', 'country', 'bio',
            
            # Connections Tab
            'phone', 'whatsapp', 'secondary_email', 'preferred_contact_method',
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation',
            
            # UP.2 C2 CLEANUP: Social Links Tab fields removed (2026-01-15)
            # Social links now managed via SocialLink model and update_basic_info endpoint
            
            # Platform Tab
            'preferred_language', 'timezone_pref', 'time_format',
            
            # About Section Fields (Phase 4)
            'device_platform', 'play_style', 'lan_availability',
            'main_role', 'secondary_role', 'communication_languages', 'active_hours',
        ]
        
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'maxlength': 500}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial value for communication_languages from JSON field
        if self.instance and self.instance.pk:
            languages = self.instance.communication_languages
            if isinstance(languages, list):
                self.initial['communication_languages'] = languages
            elif isinstance(languages, str) and languages:
                # Handle legacy string format
                try:
                    import json
                    parsed = json.loads(languages)
                    self.initial['communication_languages'] = parsed if isinstance(parsed, list) else []
                except (json.JSONDecodeError, ValueError):
                    self.initial['communication_languages'] = []
            else:
                self.initial['communication_languages'] = []
    
    def clean_communication_languages(self):
        """
        Phase 4C.3: MultipleChoiceField returns list of selected languages.
        Store as JSON list in model.
        """
        data = self.cleaned_data.get('communication_languages')
        # MultipleChoiceField already returns a list, just ensure it's a list
        return list(data) if data else []
    
    def clean(self):
        """
        Phase 4C.1: Validate preferred_contact_method has required handle.
        """
        cleaned_data = super().clean()
        preferred_method = cleaned_data.get('preferred_contact_method')
        
        if preferred_method:
            # Check if required contact handle exists
            if preferred_method == 'discord' and not cleaned_data.get('discord_id'):
                self.add_error('preferred_contact_method', 
                    'Discord ID is required when Discord is your preferred contact method. Fill it in the Connections tab.')
            elif preferred_method == 'whatsapp' and not cleaned_data.get('whatsapp'):
                self.add_error('preferred_contact_method', 
                    'WhatsApp number is required when WhatsApp is your preferred contact method. Fill it in the Connections tab.')
        
        return cleaned_data


class CareerSettingsForm(forms.ModelForm):
    """
    Career and recruitment settings form.
    Maps to Recruitment tab in settings_control_deck.html.
    Phase 4B: Enables persistence for previously non-functional Recruitment tab.
    """
    
    class Meta:
        model = apps.get_model('user_profile', 'CareerProfile')
        fields = [
            'career_status',
            'lft_enabled',
            'primary_roles',
            'availability',
            'salary_expectation_min',
            'recruiter_visibility',
            'allow_direct_contracts',
        ]
        exclude = ['user_profile']
        
        widgets = {
            'career_status': forms.RadioSelect(),
            'salary_expectation_min': forms.NumberInput(attrs={'min': 0, 'step': '0.01'}),
        }
        
        help_texts = {
            'career_status': 'Your current professional career status',
            'lft_enabled': 'Show "Looking For Team" badge on your profile',
            'primary_roles': 'Your main competitive roles (JSON array)',
            'availability': 'Your time commitment availability',
            'salary_expectation_min': 'Minimum monthly salary expectation',
            'recruiter_visibility': 'Who can see your career information',
            'allow_direct_contracts': 'Allow recruiters to send direct contract offers',
        }


class HardwareLoadoutForm(forms.ModelForm):
    """
    Hardware loadout form for gaming gear showcase.
    Maps to Loadout tab in settings_control_deck.html.
    Phase 4B: Enables persistence for previously non-functional Loadout tab.
    """
    
    class Meta:
        model = apps.get_model('user_profile', 'HardwareLoadout')
        fields = ['mouse_brand', 'keyboard_brand', 'headset_brand', 'monitor_brand']
        exclude = ['user_profile']
        
        widgets = {
            'mouse_brand': forms.TextInput(attrs={
                'placeholder': 'e.g., Logitech G Pro X Superlight',
                'maxlength': 100
            }),
            'keyboard_brand': forms.TextInput(attrs={
                'placeholder': 'e.g., Wooting 60HE',
                'maxlength': 100
            }),
            'headset_brand': forms.TextInput(attrs={
                'placeholder': 'e.g., HyperX Cloud II',
                'maxlength': 100
            }),
            'monitor_brand': forms.TextInput(attrs={
                'placeholder': 'e.g., BenQ Zowie XL2546K 240Hz',
                'maxlength': 100
            }),
        }


class AboutSettingsForm(forms.ModelForm):
    """
    Dedicated form for About tab settings ONLY.
    Phase 4C.1.2: Separates About fields to prevent validation errors from other tabs.
    
    IMPORTANT: This form does NOT include identity/platform/connections fields like:
    - display_name, preferred_language, timezone_pref, time_format (Identity/Platform)
    - preferred_contact_method (Connections Hub)
    
    This ensures saving About tab doesn't require unrelated fields.
    """
    
    # Popular languages list for communication_languages multi-select
    LANGUAGE_CHOICES = [
        ('English', 'English'),
        ('Bengali', 'Bengali'),
        ('Hindi', 'Hindi'),
        ('Urdu', 'Urdu'),
        ('Arabic', 'Arabic'),
        ('German', 'German'),
        ('French', 'French'),
        ('Spanish', 'Spanish'),
        ('Portuguese', 'Portuguese'),
        ('Russian', 'Russian'),
        ('Turkish', 'Turkish'),
        ('Malay', 'Malay'),
        ('Indonesian', 'Indonesian'),
        ('Japanese', 'Japanese'),
        ('Korean', 'Korean'),
        ('Chinese', 'Chinese'),
        ('Italian', 'Italian'),
    ]
    
    communication_languages = forms.MultipleChoiceField(
        choices=LANGUAGE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'language-checkbox'}),
        required=False,
        help_text='Select all languages you can communicate in'
    )
    
    class Meta:
        model = UserProfile
        fields = [
            # Player Summary (About section bio)
            'profile_story',
            'competitive_goal',  # UP.3 HOTFIX #3
            
            # Primary Team & Game
            'primary_team',
            'primary_game',
            
            # Competitive DNA
            'device_platform',
            'play_style',
            'main_role',
            'secondary_role',
            'lft_status',  # UP.3 HOTFIX #4
            
            # Logistics & Availability
            'active_hours',
            'communication_languages',
            'lan_availability',
        ]
        
        widgets = {
            'profile_story': forms.Textarea(attrs={
                'rows': 4,
                'maxlength': 320,
                'placeholder': 'Share your competitive journey, achievements, or what makes you unique as a player...',
                'class': 'z-input h-24 resize-none',
                'oninput': 'updateCharCount(this, 320, \'summary\'); markUnsaved();'
            }),
            'competitive_goal': forms.Textarea(attrs={
                'rows': 2,
                'maxlength': 160,
                'placeholder': 'e.g., "Reach Diamond rank this season" or "Win a regional tournament"',
                'class': 'z-input h-16 resize-none',
                'oninput': 'updateCharCount(this, 160, \'goal\'); markUnsaved();'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial value for communication_languages from JSON field
        if self.instance and self.instance.pk:
            languages = self.instance.communication_languages
            if isinstance(languages, list):
                self.initial['communication_languages'] = languages
            elif isinstance(languages, str) and languages:
                # Handle legacy string format
                try:
                    import json
                    parsed = json.loads(languages)
                    self.initial['communication_languages'] = parsed if isinstance(parsed, list) else []
                except (json.JSONDecodeError, ValueError):
                    self.initial['communication_languages'] = []
            else:
                self.initial['communication_languages'] = []
    
    def clean_communication_languages(self):
        """
        Phase 4C.3: MultipleChoiceField returns list of selected languages.
        Store as JSON list in model.
        """
        data = self.cleaned_data.get('communication_languages')
        # MultipleChoiceField already returns a list, just ensure it's a list
        return list(data) if data else []
    
    def clean_profile_story(self):
        """UP.3 EXTENSION: Enforce 320 char limit for Player Summary"""
        story = self.cleaned_data.get('profile_story', '')
        if story and len(story) > 320:
            raise forms.ValidationError(f'Player Summary must be 320 characters or less (currently {len(story)})')
        return story
    
    def clean_competitive_goal(self):
        """UP.3 HOTFIX #3: Enforce 160 char limit for Competitive Goal"""
        goal = self.cleaned_data.get('competitive_goal', '')
        if goal and len(goal) > 160:
            raise forms.ValidationError(f'Competitive Goal must be 160 characters or less (currently {len(goal)})')
        return goal
    
    def clean(self):
        """UP.3 EXTENSION: Validate primary_team/game consistency"""
        cleaned_data = super().clean()
        primary_team = cleaned_data.get('primary_team')
        primary_game = cleaned_data.get('primary_game')
        
        # If team is set, game must match team's game
        if primary_team and primary_game:
            if hasattr(primary_team, 'game') and primary_team.game != primary_game:
                self.add_error('primary_game', 
                    f'Primary game must match your primary team\'s game ({primary_team.game.display_name if hasattr(primary_team, "game") else "team game"}). Clear your team selection to choose a different game.')
        
        return cleaned_data


class PrivacySettingsFormComplete(forms.ModelForm):
    """
    Complete privacy settings form with ALL toggles.
    Phase 4B: Ensures all UI checkboxes persist to database.
    Replaces partial privacy save logic that only saved 7 of 19 fields.
    """
    
    class Meta:
        model = apps.get_model('user_profile', 'PrivacySettings')
        fields = [
            # Visibility Preset
            'visibility_preset',
            
            # Personal Info Privacy
            'show_real_name', 'show_phone', 'show_email', 'show_age', 
            'show_gender', 'show_country', 'show_address',
            
            # Gaming & Activity Privacy
            'show_game_ids', 'show_match_history', 'show_teams', 
            'show_achievements', 'show_activity_feed', 'show_tournaments',
            
            # Economy & Inventory Privacy
            'show_inventory_value', 'show_level_xp', 'inventory_visibility',
            
            # Social Privacy
            'show_social_links', 'show_followers_count', 'show_following_count',
            'show_followers_list', 'show_following_list',
            
            # Interaction Permissions
            'allow_team_invites', 'allow_friend_requests', 'allow_direct_messages',
            
            # Private Account
            'is_private_account',
            
            # Phase 4 About Section Privacy
            'show_pronouns', 'show_nationality', 'show_device_platform',
            'show_play_style', 'show_roles', 'show_active_hours', 'show_preferred_contact',
        ]
        exclude = ['user_profile']
        
        widgets = {
            # All boolean fields as checkboxes
            **{field: forms.CheckboxInput() for field in [
                'show_real_name', 'show_phone', 'show_email', 'show_age', 
                'show_gender', 'show_country', 'show_address',
                'show_game_ids', 'show_match_history', 'show_teams', 
                'show_achievements', 'show_activity_feed', 'show_tournaments',
                'show_inventory_value', 'show_level_xp',
                'show_social_links', 'show_followers_count', 'show_following_count',
                'show_followers_list', 'show_following_list',
                'allow_team_invites', 'allow_friend_requests', 'allow_direct_messages',
                'is_private_account',
                'show_pronouns', 'show_nationality', 'show_device_platform',
                'show_play_style', 'show_roles', 'show_active_hours', 'show_preferred_contact',
            ]},
            'visibility_preset': forms.Select(),
            'inventory_visibility': forms.Select(),
        }
