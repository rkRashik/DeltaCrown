from django import forms
from django.core.exceptions import ValidationError
from apps.user_profile.models import UserProfile
from .models import Team, TeamMembership, TeamInvite
from .game_config import GAME_CHOICES
import re

# Region choices for team location
REGION_CHOICES = [
    ('', 'Select Region'),
    ('NA', 'North America'),
    ('SA', 'South America'),
    ('EU', 'Europe'),
    ('SEA', 'Southeast Asia'),
    ('EA', 'East Asia'),
    ('OCE', 'Oceania'),
    ('ME', 'Middle East'),
    ('AF', 'Africa'),
    ('SA-BD', 'Bangladesh'),
    ('SA-IN', 'India'),
    ('SA-PK', 'Pakistan'),
]

class TeamCreationForm(forms.ModelForm):
    accept_terms = forms.BooleanField(
        required=True,
        label="I accept the Terms & Conditions",
        error_messages={
            'required': 'Please read and accept the Team Creation Terms & Responsibilities to continue.'
        }
    )
    
    class Meta:
        model = Team
        fields = ['name', 'tag', 'tagline', 'description', 'logo', 'game', 'region', 'banner_image', 
                  'twitter', 'instagram', 'discord', 'youtube', 'twitch', 'linktree']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter team name (3-50 characters)',
                'maxlength': '50'
            }),
            'tag': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter team tag (2-10 characters)',
                'maxlength': '10',
                'style': 'text-transform: uppercase;'
            }),
            'tagline': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., "Rise Above", "Never Back Down", "Victory Awaits"',
                'maxlength': '200'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description of your team (optional)',
                'rows': 3,
                'maxlength': '500'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'game': forms.Select(attrs={
                'class': 'form-control'
            }),
            'region': forms.Select(attrs={
                'class': 'form-control'
            }),
            'banner_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'twitter': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://twitter.com/your-team'
            }),
            'instagram': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://instagram.com/your-team'
            }),
            'discord': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://discord.gg/your-server'
            }),
            'youtube': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://youtube.com/your-channel'
            }),
            'twitch': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://twitch.tv/your-channel'
            }),
            'linktree': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://linktr.ee/your-team'
            })
        }

    def __init__(self, *args, **kwargs):
        # Extract user parameter if provided (for compatibility)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set choices for region field
        self.fields['region'].choices = REGION_CHOICES
        self.fields['region'].required = True  # Make region required

    def clean_banner_image(self):
        """Validate banner image file size (max 10MB)"""
        banner = self.cleaned_data.get('banner_image')
        if banner:
            if banner.size > 10 * 1024 * 1024:  # 10MB in bytes
                raise ValidationError('Team banner file size must not exceed 10MB. Please compress or resize your image.')
        return banner

    def clean_region(self):
        """Ensure region is properly saved"""
        region = self.cleaned_data.get('region')
        if not region or region == '':
            raise ValidationError('Please select a region for your team.')
        return region

    def save(self, commit=True):
        team = super().save(commit=False)
        
        # Set the captain if user is provided
        if self.user:
            from apps.user_profile.models import UserProfile
            try:
                profile = UserProfile.objects.get(user=self.user)
                team.captain = profile
            except UserProfile.DoesNotExist:
                # Create profile if it doesn't exist
                profile = UserProfile.objects.create(
                    user=self.user,
                    display_name=self.user.get_full_name() or self.user.username
                )
                team.captain = profile
        
        if commit:
            team.save()
            # Ensure captain membership exists
            if hasattr(team, 'ensure_captain_membership'):
                team.ensure_captain_membership()
        
        return team

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if len(name) < 3:
                raise ValidationError("Team names need at least 3 characters to be unique and memorable.")
            if len(name) > 50:
                raise ValidationError("Team name is too long. Please keep it under 50 characters.")
            
            # Check for uniqueness
            if Team.objects.filter(name__iexact=name).exclude(pk=self.instance.pk if self.instance else None).exists():
                raise ValidationError(
                    "This team name is already taken. Try adding your region or a variation to make it unique!"
                )
        return name

    def clean_tag(self):
        tag = self.cleaned_data.get('tag')
        if tag:
            tag = tag.strip().upper()
            if len(tag) < 2:
                raise ValidationError("Team tags need at least 2 characters.")
            if len(tag) > 10:
                raise ValidationError("Team tag is too long. Keep it short and memorable (max 10 characters).")
            
            # Only allow alphanumeric characters
            if not re.match(r'^[A-Z0-9]+$', tag):
                raise ValidationError("Team tags can only contain letters and numbers (no spaces or special characters).")
            
            # Check for uniqueness
            if Team.objects.filter(tag__iexact=tag).exclude(pk=self.instance.pk if self.instance else None).exists():
                raise ValidationError(
                    "This tag is already in use by another team. Try a different combination!"
                )
        return tag

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        if logo:
            # Check file size (max 5MB)
            if logo.size > 5 * 1024 * 1024:
                raise ValidationError("Team logo file size must not exceed 5MB. Please compress or resize your image.")
            
            # Check file format
            if not logo.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                raise ValidationError("Please upload a valid image file (PNG, JPG, JPEG, GIF, or WebP format).")
        return logo
    
    def clean_game(self):
        """Validate that user doesn't already have a team for this game"""
        game = self.cleaned_data.get('game')
        if game and self.user:
            # Get user's profile
            profile = getattr(self.user, 'profile', None) or getattr(self.user, 'userprofile', None)
            if profile:
                # Check if user is already in a team for this game
                existing_teams = TeamMembership.objects.filter(
                    profile=profile,
                    status='ACTIVE'
                ).select_related('team').filter(team__game=game)
                
                if existing_teams.exists():
                    team = existing_teams.first().team
                    team_name = team.name
                    team_tag = team.tag
                    game_display = dict(GAME_CHOICES).get(game, game)
                    # Friendly, supportive message explaining the one-team-per-game rule
                    raise ValidationError(
                        f"You already belong to {team_name} [{team_tag}] for {game_display}. "
                        f"To maintain competitive integrity, each player can only represent one active team per game. "
                        f"You can view your current team from your profile, leave it if needed, and then create a new one."
                    )
                
                # Check if game requires game ID (for VALORANT, CS2, DOTA2, MLBB)
                games_requiring_id = ['VALORANT', 'CS2', 'DOTA2', 'MLBB']
                if game in games_requiring_id:
                    # Check if user has the required game ID configured
                    game_id_field_map = {
                        'VALORANT': 'riot_id',
                        'CS2': 'steam_id',
                        'DOTA2': 'steam_id',
                        'MLBB': 'mlbb_id'
                    }
                    game_id_label_map = {
                        'VALORANT': 'Riot ID',
                        'CS2': 'Steam ID',
                        'DOTA2': 'Steam ID',
                        'MLBB': 'Mobile Legends ID'
                    }
                    field_name = game_id_field_map.get(game)
                    if field_name and not getattr(profile, field_name, None):
                        # Store game code in session for redirect (handled by view)
                        game_display = dict(GAME_CHOICES).get(game, game)
                        game_id_label = game_id_label_map.get(game, 'game ID')
                        # Friendly message explaining why game ID is needed
                        raise ValidationError(
                            f"To create a {game_display} team, you need to verify your {game_id_label} first. "
                            f"This helps us ensure fair competition and match your team to your in-game profile. "
                            f"You'll be guided to add it in the next step."
                        )
        return game

    def clean_banner_image(self):
        banner = self.cleaned_data.get('banner_image')
        if banner:
            # Check file size (max 2MB)
            if banner.size > 2 * 1024 * 1024:
                raise ValidationError("Banner file size cannot exceed 2MB.")
            
            # Check file format
            if not banner.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                raise ValidationError("Banner must be a valid image file (PNG, JPG, JPEG, GIF, or WebP).")
        return banner


class TeamEditForm(TeamCreationForm):
    class Meta(TeamCreationForm.Meta):
        fields = ['name', 'tag', 'description', 'logo', 'region', 'twitter', 'instagram', 'discord', 'youtube', 'twitch']
        
    def __init__(self, *args, **kwargs):
        # Extract user parameter if provided (for compatibility)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Add social media fields
        social_fields = ['twitter', 'instagram', 'discord', 'youtube', 'twitch']
        for field in social_fields:
            self.fields[field] = forms.URLField(
                required=False,
                widget=forms.URLInput(attrs={
                    'class': 'form-control',
                    'placeholder': f'{field.title()} URL (optional)'
                })
            )


class TeamInviteForm(forms.Form):
    username_or_email = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username or email address'
        }),
        help_text="Enter the username or email of the player you want to invite"
    )
    role = forms.ChoiceField(
        choices=TeamMembership.Role.choices,
        initial=TeamMembership.Role.PLAYER,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Optional message to include with the invitation',
            'rows': 3
        })
    )

    def __init__(self, *args, **kwargs):
        self.team = kwargs.pop('team', None)
        self.sender = kwargs.pop('sender', None)
        super().__init__(*args, **kwargs)

    def clean_username_or_email(self):
        value = self.cleaned_data['username_or_email'].strip()
        
        # Try to find user by username first
        try:
            profile = UserProfile.objects.get(user__username__iexact=value)
        except UserProfile.DoesNotExist:
            # Try by email
            try:
                profile = UserProfile.objects.get(user__email__iexact=value)
            except UserProfile.DoesNotExist:
                raise ValidationError("User not found. Please provide a valid username or email.")
        
        # Check if user is already a member
        if self.team and self.team.has_member(profile):
            raise ValidationError("This user is already a member of the team.")
        
        # Check if there's already a pending invite
        if self.team and TeamInvite.objects.filter(
            team=self.team, 
            invited_user=profile, 
            status='PENDING'
        ).exists():
            raise ValidationError("This user already has a pending invitation to join the team.")
        
        return profile

    def clean_role(self):
        role = self.cleaned_data.get('role')
        if role == TeamMembership.Role.CAPTAIN:
            raise ValidationError("Cannot invite someone as captain. Transfer captaincy after they join.")
        return role


class TeamMemberManagementForm(forms.Form):
    member_id = forms.IntegerField(widget=forms.HiddenInput())
    action = forms.ChoiceField(
        choices=[
            ('promote', 'Promote to Captain'),
            ('demote', 'Change to Player'),
            ('remove', 'Remove from Team')
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        self.team = kwargs.pop('team', None)
        self.current_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        member_id = cleaned_data.get('member_id')
        
        if not self.team or not self.current_user:
            raise ValidationError("Invalid team or user context.")
        
        # Check if current user is captain
        if not self.team.is_captain(self.current_user):
            raise ValidationError("Only team captains can manage members.")
        
        # Get the target member
        try:
            target_membership = TeamMembership.objects.get(
                id=member_id, 
                team=self.team,
                status=TeamMembership.Status.ACTIVE
            )
        except TeamMembership.DoesNotExist:
            raise ValidationError("Invalid team member selected.")
        
        # Don't allow captain to manage themselves (except for removal)
        if target_membership.profile == self.current_user and action != 'remove':
            raise ValidationError("You cannot change your own role. Transfer captaincy to another member first.")
        
        return cleaned_data


class TeamSettingsForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['banner_image', 'roster_image', 'region', 'twitter', 'instagram', 'discord', 'youtube', 'twitch', 'linktree']
        widgets = {
            'banner_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'roster_image': forms.FileInput(attrs={
                'class': 'form-control', 
                'accept': 'image/*'
            }),
            'region': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Team region'
            }),
            'twitter': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://twitter.com/your-team'
            }),
            'instagram': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://instagram.com/your-team'
            }),
            'discord': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://discord.gg/your-server'
            }),
            'youtube': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://youtube.com/your-channel'
            }),
            'twitch': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://twitch.tv/your-channel'
            }),
            'linktree': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://linktr.ee/your-team'
            })
        }

    def __init__(self, *args, **kwargs):
        # Extract user parameter if provided (for compatibility)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_banner_image(self):
        image = self.cleaned_data.get('banner_image')
        if image:
            if image.size > 5 * 1024 * 1024:  # 5MB
                raise ValidationError("Banner image cannot exceed 5MB.")
        return image

    def clean_roster_image(self):
        image = self.cleaned_data.get('roster_image')
        if image:
            if image.size > 5 * 1024 * 1024:  # 5MB
                raise ValidationError("Roster image cannot exceed 5MB.")
        return image
