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
            
            # Social Media
            'facebook', 'instagram', 'tiktok', 'twitter',
            'youtube_link', 'twitch_link', 'discord_id',
            
            # Note: Legacy game ID fields migrated to Game Passport system
            # Game-specific identities now managed via GameProfile model
            
            # Privacy Settings
            'is_private', 'show_email', 'show_phone', 'show_socials',
            'show_real_name', 'show_age', 'show_gender', 'show_country', 'show_address'
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
            
            # Social Media
            'facebook': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://facebook.com/yourprofile'
            }),
            'instagram': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://instagram.com/yourprofile'
            }),
            'tiktok': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://tiktok.com/@yourprofile'
            }),
            'twitter': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://twitter.com/yourhandle'
            }),
            'youtube_link': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://youtube.com/@yourchannel'
            }),
            'twitch_link': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://twitch.tv/yourchannel'
            }),
            'discord_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your Discord username'
            }),
            
            # Privacy Settings
            'is_private': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'show_email': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'show_phone': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'show_socials': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'show_real_name': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'show_age': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'show_gender': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'show_country': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'show_address': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
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
            
            # Social Media
            'facebook': 'Link to your Facebook profile (optional).',
            'instagram': 'Link to your Instagram profile (optional).',
            'tiktok': 'Link to your TikTok profile (optional).',
            'twitter': 'Link to your Twitter/X profile (optional).',
            'discord_id': 'Your Discord username for team communication.',
            'youtube_link': 'Link to your YouTube channel (optional).',
            'twitch_link': 'Link to your Twitch channel (optional).',
            
            # Privacy Settings
            'is_private': 'Hide your entire profile from public view.',
            'show_email': 'Display your email address on your public profile.',
            'show_phone': 'Display your phone number on your public profile.',
            'show_socials': 'Display your gaming IDs and social links on your public profile.',
            'show_real_name': 'Display your real name on your public profile.',
            'show_age': 'Display your age on your public profile.',
            'show_gender': 'Display your gender on your public profile.',
            'show_country': 'Display your country on your public profile.',
            'show_address': 'Display your address on your public profile.',
        }


class PrivacySettingsForm(forms.ModelForm):
    """Legacy form for privacy settings only"""
    class Meta:
        model = UserProfile
        fields = ("is_private", "show_email", "show_phone", "show_socials")
        widgets = {
            "is_private": forms.CheckboxInput(attrs={"class": "form-checkbox h-4 w-4"}),
            "show_email": forms.CheckboxInput(attrs={"class": "form-checkbox h-4 w-4"}),
            "show_phone": forms.CheckboxInput(attrs={"class": "form-checkbox h-4 w-4"}),
            "show_socials": forms.CheckboxInput(attrs={"class": "form-checkbox h-4 w-4"}),
        }
        help_texts = {
            "is_private": "If enabled, your public profile is hidden (404) unless explicitly shared with staff.",
            "show_email": "Show your email on the public profile page.",
            "show_phone": "Show your phone on the public profile page.",
            "show_socials": "Show your linked social account on the public profile page.",
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

