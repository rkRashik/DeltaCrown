from django import forms
from django.core.exceptions import ValidationError
from .models import Registration, Tournament, PAYMENT_METHODS
from apps.teams.models import Team

class SoloRegistrationForm(forms.ModelForm):
    payment_method = forms.ChoiceField(choices=PAYMENT_METHODS, required=False)
    payment_reference = forms.CharField(max_length=120, required=False)

    class Meta:
        model = Registration
        fields = ("payment_method", "payment_reference")

    def __init__(self, *args, **kwargs):
        self.tournament: Tournament = kwargs.pop("tournament")
        self.user_profile = kwargs.pop("user_profile")
        super().__init__(*args, **kwargs)

        # ✅ ensure the model instance is fully populated before ModelForm runs full_clean()
        self.instance.tournament = self.tournament
        self.instance.user = self.user_profile

        # Conditionally require payment fields if entry fee is set
        if self.tournament.entry_fee_bdt and self.tournament.entry_fee_bdt > 0:
            self.fields["payment_method"].required = True
            self.fields["payment_reference"].required = True

    def clean(self):
        cleaned = super().clean()
        return cleaned

    def save(self, commit=True):
        # instance already has tournament + user via __init__
        self.instance.payment_method = self.cleaned_data.get("payment_method", "")
        self.instance.payment_reference = self.cleaned_data.get("payment_reference", "")
        if commit:
            self.instance.full_clean()
            self.instance.save()
        return self.instance


class TeamRegistrationForm(forms.ModelForm):
    team = forms.ModelChoiceField(queryset=Team.objects.none())
    payment_method = forms.ChoiceField(choices=PAYMENT_METHODS, required=False)
    payment_reference = forms.CharField(max_length=120, required=False)

    class Meta:
        model = Registration
        fields = ("team", "payment_method", "payment_reference")

    def __init__(self, *args, **kwargs):
        self.tournament: Tournament = kwargs.pop("tournament")
        self.user_profile = kwargs.pop("user_profile")
        super().__init__(*args, **kwargs)

        # ✅ ensure tournament is set before ModelForm runs full_clean()
        self.instance.tournament = self.tournament

        # Limit selectable teams to those captained by current user
        self.fields["team"].queryset = Team.objects.filter(captain=self.user_profile)

        if self.tournament.entry_fee_bdt and self.tournament.entry_fee_bdt > 0:
            self.fields["payment_method"].required = True
            self.fields["payment_reference"].required = True

    def clean_team(self):
        team = self.cleaned_data["team"]
        if not team:
            raise ValidationError("Select a team you captain.")
        exists = Registration.objects.filter(tournament=self.tournament, team=team).exists()
        if exists:
            raise ValidationError("This team is already registered for the tournament.")
        return team

    def save(self, commit=True):
        # instance already has tournament via __init__; team comes from cleaned_data
        self.instance.team = self.cleaned_data["team"]
        self.instance.payment_method = self.cleaned_data.get("payment_method", "")
        self.instance.payment_reference = self.cleaned_data.get("payment_reference", "")
        if commit:
            self.instance.full_clean()
            self.instance.save()
        return self.instance
from django import forms
from django.core.exceptions import ValidationError
from .models import Registration, Tournament, PAYMENT_METHODS
from apps.teams.models import Team

class SoloRegistrationForm(forms.ModelForm):
    payment_method = forms.ChoiceField(choices=PAYMENT_METHODS, required=False)
    payment_reference = forms.CharField(max_length=120, required=False)

    class Meta:
        model = Registration
        fields = ("payment_method", "payment_reference")

    def __init__(self, *args, **kwargs):
        self.tournament: Tournament = kwargs.pop("tournament")
        self.user_profile = kwargs.pop("user_profile")
        super().__init__(*args, **kwargs)

        # ✅ ensure the model instance is fully populated before ModelForm runs full_clean()
        self.instance.tournament = self.tournament
        self.instance.user = self.user_profile

        # Conditionally require payment fields if entry fee is set
        if self.tournament.entry_fee_bdt and self.tournament.entry_fee_bdt > 0:
            self.fields["payment_method"].required = True
            self.fields["payment_reference"].required = True

    def clean(self):
        cleaned = super().clean()
        return cleaned

    def save(self, commit=True):
        # instance already has tournament + user via __init__
        self.instance.payment_method = self.cleaned_data.get("payment_method", "")
        self.instance.payment_reference = self.cleaned_data.get("payment_reference", "")
        if commit:
            self.instance.full_clean()
            self.instance.save()
        return self.instance


class TeamRegistrationForm(forms.ModelForm):
    team = forms.ModelChoiceField(queryset=Team.objects.none())
    payment_method = forms.ChoiceField(choices=PAYMENT_METHODS, required=False)
    payment_reference = forms.CharField(max_length=120, required=False)

    class Meta:
        model = Registration
        fields = ("team", "payment_method", "payment_reference")

    def __init__(self, *args, **kwargs):
        self.tournament: Tournament = kwargs.pop("tournament")
        self.user_profile = kwargs.pop("user_profile")
        super().__init__(*args, **kwargs)

        # ✅ ensure tournament is set before ModelForm runs full_clean()
        self.instance.tournament = self.tournament

        # Limit selectable teams to those captained by current user
        self.fields["team"].queryset = Team.objects.filter(captain=self.user_profile)

        if self.tournament.entry_fee_bdt and self.tournament.entry_fee_bdt > 0:
            self.fields["payment_method"].required = True
            self.fields["payment_reference"].required = True

    def clean_team(self):
        team = self.cleaned_data["team"]
        if not team:
            raise ValidationError("Select a team you captain.")
        exists = Registration.objects.filter(tournament=self.tournament, team=team).exists()
        if exists:
            raise ValidationError("This team is already registered for the tournament.")
        return team

    def save(self, commit=True):
        # instance already has tournament via __init__; team comes from cleaned_data
        self.instance.team = self.cleaned_data["team"]
        self.instance.payment_method = self.cleaned_data.get("payment_method", "")
        self.instance.payment_reference = self.cleaned_data.get("payment_reference", "")
        if commit:
            self.instance.full_clean()
            self.instance.save()
        return self.instance
