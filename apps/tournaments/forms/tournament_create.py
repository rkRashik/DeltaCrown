"""
Tournament Creation Frontend Form and View
"""

from django import forms
from apps.tournaments.models import Tournament, Game
from apps.tournaments.models.form_template import RegistrationFormTemplate
from apps.tournaments.models.form_configuration import TournamentFormConfiguration
from apps.games.services import game_service
from apps.games.models import Game


class TournamentCreateForm(forms.ModelForm):
    """Frontend form for creating tournaments"""
    
    # ==============================================
    # REGISTRATION FORM CONFIGURATION FIELDS (NEW)
    # ==============================================
    
    # Form Type Selection
    use_default_form = forms.BooleanField(
        required=False,
        initial=True,
        label='Use Default Registration Form',
        help_text='Use the standard solo or team registration form based on tournament type',
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox', 'x-model': 'useDefaultForm'})
    )
    
    use_custom_form = forms.BooleanField(
        required=False,
        initial=False,
        label='Use Custom Registration Form',
        help_text='Select or create a custom form with additional fields',
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox', 'x-model': 'useCustomForm'})
    )
    
    custom_form_template = forms.ModelChoiceField(
        queryset=RegistrationFormTemplate.objects.filter(is_active=True),
        required=False,
        empty_label='-- Select Custom Form or Create New --',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'x-show': 'useCustomForm',
            'x-cloak': True
        }),
        help_text='Choose an existing custom form or select "Create New" to build one from scratch'
    )
    
    class Meta:
        model = Tournament
        fields = [
            'name',
            'slug',
            'game',
            'format',
            'tournament_start',
            'registration_start',
            'registration_end',
            'max_participants',
            'entry_fee_amount',
            'prize_pool',
            'is_official',
            'description',
            'rules_text',
        ]
        widgets = {
            'tournament_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-input'}),
            'registration_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-input'}),
            'registration_end': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-input'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-textarea'}),
            'rules_text': forms.Textarea(attrs={'rows': 6, 'class': 'form-textarea'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'DeltaCrown Valorant Championship 2025'}),
            'slug': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'valorant-championship-2025'}),
            'max_participants': forms.NumberInput(attrs={'class': 'form-input', 'min': 4, 'max': 128}),
            'entry_fee_amount': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'step': '0.01'}),
            'prize_pool': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate game choices from GameService (canonical games only)
        game_choices = [('', 'Select a game...')]
        
        # Get all active games
        for game in game_service.list_active_games():
            game_choices.append((game.id, game.display_name))
        
        self.fields['game'].widget = forms.Select(
            choices=game_choices,
            attrs={'class': 'form-select'}
        )
        
        # Format type choices
        self.fields['format'].widget = forms.Select(
            choices=[
                ('', 'Select format...'),
                ('single_elimination', 'Single Elimination'),
                ('double_elimination', 'Double Elimination'),
                ('round_robin', 'Round Robin'),
                ('swiss', 'Swiss System'),
                ('group_playoff', 'Group Stage + Knockout'),
            ],
            attrs={'class': 'form-select'}
        )
        
        # Set all fields as required except description and rules_text
        for field_name in self.fields:
            if field_name not in ['description', 'rules_text']:
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
        
        # Validate form configuration
        use_default = cleaned_data.get('use_default_form')
        use_custom = cleaned_data.get('use_custom_form')
        custom_form = cleaned_data.get('custom_form_template')
        
        # Must select at least one form type
        if not use_default and not use_custom:
            raise forms.ValidationError('Please select at least one registration form type (Default or Custom).')
        
        # Cannot select both
        if use_default and use_custom:
            raise forms.ValidationError('Please select only one registration form type.')
        
        # If custom form selected, must provide template or redirect to builder
        if use_custom and not custom_form:
            # This will be handled by redirect to form builder in the view
            cleaned_data['redirect_to_form_builder'] = True
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save tournament and create form configuration"""
        tournament = super().save(commit=False)
        
        if commit:
            tournament.save()
            
            # Create form configuration
            use_custom = self.cleaned_data.get('use_custom_form')
            custom_form = self.cleaned_data.get('custom_form_template')
            
            if use_custom and custom_form:
                # Custom form selected
                form_config = TournamentFormConfiguration.objects.create(
                    tournament=tournament,
                    form_type=TournamentFormConfiguration.FORM_TYPE_CUSTOM,
                    custom_form=custom_form
                )
            else:
                # Default form
                form_type = (
                    TournamentFormConfiguration.FORM_TYPE_DEFAULT_TEAM
                    if tournament.participation_type == 'team'
                    else TournamentFormConfiguration.FORM_TYPE_DEFAULT_SOLO
                )
                form_config = TournamentFormConfiguration.objects.create(
                    tournament=tournament,
                    form_type=form_type
                )
        
        return tournament
