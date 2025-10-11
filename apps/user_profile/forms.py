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
            'avatar', 'display_name', 'region', 'bio',
            'riot_id', 'riot_tagline', 'steam_id', 'efootball_id', 
            'mlbb_id', 'mlbb_server_id', 'pubg_mobile_id', 'free_fire_id',
            'ea_id', 'codm_uid', 'discord_id',
            'youtube_link', 'twitch_link',
            'is_private', 'show_email', 'show_phone', 'show_socials'
        ]
        
        widgets = {
            'display_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your display name'
            }),
            'region': forms.Select(attrs={
                'class': 'form-input'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-input',
                'placeholder': 'Tell others about yourself...',
                'rows': 4
            }),
            'riot_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your Riot ID (e.g., Username#TAG)'
            }),
            'riot_tagline': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Tagline (part after #)'
            }),
            'steam_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your Steam ID'
            }),
            'efootball_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your eFootball User ID'
            }),
            'mlbb_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Mobile Legends Game ID'
            }),
            'mlbb_server_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Server ID'
            }),
            'pubg_mobile_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'PUBG Mobile Character/Player ID'
            }),
            'free_fire_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Free Fire Player ID'
            }),
            'ea_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'EA ID for FC 24'
            }),
            'codm_uid': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Call of Duty Mobile UID'
            }),
            'discord_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your Discord username'
            }),
            'youtube_link': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://youtube.com/@yourchannel'
            }),
            'twitch_link': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://twitch.tv/yourchannel'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'file-input',
                'accept': 'image/*'
            }),
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
        }
        
        help_texts = {
            'display_name': 'This is how your name will appear on your profile and in teams.',
            'region': 'Select your primary gaming region.',
            'bio': 'A brief description about yourself and your gaming interests.',
            'riot_id': 'Your Riot Games ID for Valorant (Name#TAG format).',
            'riot_tagline': 'The tagline part of your Riot ID (after the #).',
            'steam_id': 'Your Steam ID for Dota 2, Counter-Strike 2.',
            'efootball_id': 'Your eFootball User ID.',
            'mlbb_id': 'Your Mobile Legends: Bang Bang Game ID.',
            'mlbb_server_id': 'Your Mobile Legends Server ID.',
            'pubg_mobile_id': 'Your PUBG Mobile Character/Player ID.',
            'free_fire_id': 'Your Free Fire User/Player ID.',
            'ea_id': 'Your EA ID for FC 24.',
            'codm_uid': 'Your Call of Duty Mobile Unique ID.',
            'discord_id': 'Your Discord username for team communication.',
            'youtube_link': 'Link to your YouTube channel (optional).',
            'twitch_link': 'Link to your Twitch channel (optional).',
            'is_private': 'Hide your entire profile from public view.',
            'show_email': 'Display your email address on your public profile.',
            'show_phone': 'Display your phone number on your public profile.',
            'show_socials': 'Display your gaming IDs and social links on your public profile.',
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
