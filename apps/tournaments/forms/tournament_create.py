"""
Tournament Creation Frontend Form and View
"""

from django import forms
from apps.tournaments.models import Tournament
from apps.common.game_assets import GAME_DATA


class TournamentCreateForm(forms.ModelForm):
    """Frontend form for creating tournaments"""
    
    class Meta:
        model = Tournament
        fields = [
            'name',
            'slug',
            'game',
            'format_type',
            'tournament_start',
            'registration_start',
            'registration_end',
            'max_participants',
            'entry_fee',
            'prize_pool',
            'is_official',
            'description',
            'rules',
        ]
        widgets = {
            'tournament_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-input'}),
            'registration_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-input'}),
            'registration_end': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-input'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-textarea'}),
            'rules': forms.Textarea(attrs={'rows': 6, 'class': 'form-textarea'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'DeltaCrown Valorant Championship 2025'}),
            'slug': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'valorant-championship-2025'}),
            'max_participants': forms.NumberInput(attrs={'class': 'form-input', 'min': 4, 'max': 128}),
            'entry_fee': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'step': '0.01'}),
            'prize_pool': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate game choices from GAME_DATA
        game_choices = [('', 'Select a game...')] + [
            (code, data['display_name']) 
            for code, data in GAME_DATA.items()
        ]
        self.fields['game'].widget = forms.Select(
            choices=game_choices,
            attrs={'class': 'form-select'}
        )
        
        # Format type choices
        self.fields['format_type'].widget = forms.Select(
            choices=[
                ('', 'Select format...'),
                ('single_elimination', 'Single Elimination'),
                ('double_elimination', 'Double Elimination'),
                ('round_robin', 'Round Robin'),
                ('swiss', 'Swiss System'),
                ('group_stage_knockout', 'Group Stage + Knockout'),
            ],
            attrs={'class': 'form-select'}
        )
        
        # Set all fields as required except description and rules
        for field_name in self.fields:
            if field_name not in ['description', 'rules']:
                self.fields[field_name].required = True
    
    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if slug:
            # Convert to lowercase and replace spaces with hyphens
            slug = slug.lower().strip().replace(' ', '-')
            # Check uniqueness
            if Tournament.objects.filter(slug=slug).exists():
                raise forms.ValidationError('A tournament with this slug already exists.')
        return slug
    
    def clean(self):
        cleaned_data = super().clean()
        reg_start = cleaned_data.get('registration_start')
        reg_end = cleaned_data.get('registration_end')
        tournament_start = cleaned_data.get('tournament_start')
        
        if reg_start and reg_end and reg_start >= reg_end:
            raise forms.ValidationError('Registration end must be after registration start.')
        
        if reg_end and tournament_start and reg_end >= tournament_start:
            raise forms.ValidationError('Tournament start must be after registration end.')
        
        return cleaned_data
