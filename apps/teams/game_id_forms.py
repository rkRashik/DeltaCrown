# apps/teams/forms/game_id_forms.py
"""
Forms for collecting game IDs when creating/joining teams
"""
from django import forms
from django.apps import apps


class GameIDCollectionForm(forms.Form):
    """
    Dynamic form for collecting game ID based on selected game.
    Used during team creation and join requests.
    """
    game_id = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input game-id-input',
            'placeholder': 'Enter your Game ID',
        })
    )
    
    # For Mobile Legends which requires both Game ID and Server ID
    mlbb_server_id = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input game-id-input',
            'placeholder': 'Server ID',
        })
    )
    
    def __init__(self, *args, game_code=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if game_code:
            game_code_lower = game_code.lower()
            
            # Update placeholder and label based on game
            game_labels = {
                'valorant': {
                    'label': 'Riot ID',
                    'placeholder': 'Enter your Riot ID (Name#TAG)',
                    'help_text': 'Your Riot ID consists of your game name and tagline (e.g., PlayerName#NA1)'
                },
                'efootball': {
                    'label': 'eFootball User ID',
                    'placeholder': 'Enter your User ID',
                    'help_text': 'Your eFootball account User ID'
                },
                'dota2': {
                    'label': 'Steam ID',
                    'placeholder': 'Enter your Steam ID',
                    'help_text': 'Your Steam account ID for Dota 2'
                },
                'cs2': {
                    'label': 'Steam ID',
                    'placeholder': 'Enter your Steam ID',
                    'help_text': 'Your Steam account ID for Counter-Strike 2'
                },
                'mlbb': {
                    'label': 'Mobile Legends Game ID',
                    'placeholder': 'Enter your Game ID',
                    'help_text': 'Your Mobile Legends: Bang Bang Game ID'
                },
                'pubgm': {
                    'label': 'PUBG Mobile Character ID',
                    'placeholder': 'Enter your Character/Player ID',
                    'help_text': 'Your PUBG Mobile Character or Player ID'
                },
                'freefire': {
                    'label': 'Free Fire Player ID',
                    'placeholder': 'Enter your User/Player ID',
                    'help_text': 'Your Free Fire User or Player ID'
                },
                'fc24': {
                    'label': 'EA ID',
                    'placeholder': 'Enter your EA ID',
                    'help_text': 'Your EA account ID for FC 24'
                },
                'codm': {
                    'label': 'Call of Duty Mobile UID',
                    'placeholder': 'Enter your UID',
                    'help_text': 'Your unique Call of Duty Mobile UID'
                },
            }
            
            game_info = game_labels.get(game_code_lower, {
                'label': 'Game ID',
                'placeholder': 'Enter your Game ID',
                'help_text': 'Your in-game ID or username'
            })
            
            self.fields['game_id'].label = game_info['label']
            self.fields['game_id'].widget.attrs['placeholder'] = game_info['placeholder']
            self.fields['game_id'].help_text = game_info['help_text']
            
            # Show server ID field only for Mobile Legends
            if game_code_lower == 'mlbb':
                self.fields['mlbb_server_id'].required = True
                self.fields['mlbb_server_id'].label = 'Server ID'
                self.fields['mlbb_server_id'].help_text = 'Your Mobile Legends server ID'
            else:
                del self.fields['mlbb_server_id']
    
    def save_to_profile(self, profile, game_code):
        """Save the game ID to user profile"""
        game_id = self.cleaned_data['game_id']
        
        # Save to profile using the model's helper method
        if game_code.lower() == 'mlbb':
            profile.mlbb_id = game_id
            profile.mlbb_server_id = self.cleaned_data.get('mlbb_server_id', '')
        else:
            profile.set_game_id(game_code, game_id)
        
        profile.save()
        return profile


class RosterGameIDForm(forms.Form):
    """
    Form for displaying/editing game IDs in roster management.
    Used by team captains to view member game IDs.
    """
    def __init__(self, *args, profile=None, game_code=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if profile and game_code:
            game_id = profile.get_game_id(game_code)
            label = profile.get_game_id_label(game_code)
            
            self.fields['game_id_display'] = forms.CharField(
                label=label,
                initial=game_id or 'Not provided',
                disabled=True,
                required=False,
                widget=forms.TextInput(attrs={
                    'class': 'form-input-readonly',
                    'readonly': 'readonly'
                })
            )
            
            # Add server ID for MLBB
            if game_code.lower() == 'mlbb' and profile.mlbb_server_id:
                self.fields['mlbb_server_display'] = forms.CharField(
                    label='Server ID',
                    initial=profile.mlbb_server_id,
                    disabled=True,
                    required=False,
                    widget=forms.TextInput(attrs={
                        'class': 'form-input-readonly',
                        'readonly': 'readonly'
                    })
                )
