# apps/tournaments/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Registration, Tournament, PAYMENT_METHODS
from apps.teams.models import Team

WALLET_METHODS = {"bkash", "nagad", "rocket"}


class SoloRegistrationForm(forms.ModelForm):
    payment_method = forms.ChoiceField(choices=PAYMENT_METHODS, required=False, label="Payment method")
    payment_sender = forms.CharField(max_length=32, required=False, label="Your wallet/account number")
    payment_reference = forms.CharField(max_length=120, required=False, label="Transaction / Reference ID")

    class Meta:
        model = Registration
        fields = ("payment_method", "payment_sender", "payment_reference")
        widgets = {
            "payment_method": forms.Select(attrs={"class": "form-select"}),
            "payment_sender": forms.TextInput(attrs={"class": "form-control", "placeholder": "017XXXXXXXX / account"}),
            "payment_reference": forms.TextInput(attrs={"class": "form-control", "placeholder": "TRX / bank ref"}),
        }

    def __init__(self, *args, **kwargs):
        self.tournament: Tournament = kwargs.pop("tournament")
        self.user_profile = kwargs.pop("user_profile")
        super().__init__(*args, **kwargs)

        # Bind instance before validation
        self.instance.tournament = self.tournament
        self.instance.user = self.user_profile

        # For paid tournaments, require method + reference.
        fee = self.tournament.entry_fee_bdt or 0
        self.fields["payment_method"].required = fee > 0
        self.fields["payment_reference"].required = fee > 0
        # payment_sender requirement depends on chosen method -> enforced in clean()

    def clean(self):
        cleaned = super().clean()
        fee = self.tournament.entry_fee_bdt or 0

        pm = (cleaned.get("payment_method") or "").strip().lower()
        snd = (cleaned.get("payment_sender") or "").strip()
        ref = (cleaned.get("payment_reference") or "").strip()

        if fee > 0:
            if not pm:
                self.add_error("payment_method", "Select a payment method.")
            if not ref:
                self.add_error("payment_reference", "Enter the transaction/reference ID.")
            # 🔴 Solo flow: require sender for wallet methods (bkash/nagad/rocket)
            if pm in WALLET_METHODS and not snd:
                self.add_error("payment_sender", "Enter the payer wallet/phone number.")

        return cleaned

    def save(self, commit=True):
        self.instance.payment_method = self.cleaned_data.get("payment_method", "")
        self.instance.payment_sender = self.cleaned_data.get("payment_sender", "")
        self.instance.payment_reference = self.cleaned_data.get("payment_reference", "")
        if commit:
            self.instance.full_clean()  # includes model.clean
            self.instance.save()
        return self.instance


class TeamRegistrationForm(forms.ModelForm):
    team = forms.ModelChoiceField(queryset=Team.objects.none(), label="Team")
    payment_method = forms.ChoiceField(choices=PAYMENT_METHODS, required=False, label="Payment method")
    payment_sender = forms.CharField(max_length=32, required=False, label="Your wallet/account number")
    payment_reference = forms.CharField(max_length=120, required=False, label="Transaction / Reference ID")

    class Meta:
        model = Registration
        fields = ("team", "payment_method", "payment_sender", "payment_reference")
        widgets = {
            "payment_method": forms.Select(attrs={"class": "form-select"}),
            "payment_sender": forms.TextInput(attrs={"class": "form-control", "placeholder": "017XXXXXXXX / account"}),
            "payment_reference": forms.TextInput(attrs={"class": "form-control", "placeholder": "TRX / bank ref"}),
        }

    def __init__(self, *args, **kwargs):
        self.tournament: Tournament = kwargs.pop("tournament")
        self.user_profile = kwargs.pop("user_profile")
        super().__init__(*args, **kwargs)

        # Bind instance before validation
        self.instance.tournament = self.tournament

        # Only teams captained by this user
        self.fields["team"].queryset = Team.objects.filter(captain=self.user_profile)

        fee = self.tournament.entry_fee_bdt or 0
        self.fields["payment_method"].required = fee > 0
        self.fields["payment_reference"].required = fee > 0
        # 🟢 Team flow: sender is optional even for wallet methods (test expects redirect without it)
        self.fields["payment_sender"].required = False

    def clean_team(self):
        team = self.cleaned_data.get("team")
        if not team:
            raise ValidationError("Select a team you captain.")
        if Registration.objects.filter(tournament=self.tournament, team=team).exists():
            raise ValidationError("This team is already registered for the tournament.")
        return team

    def clean(self):
        cleaned = super().clean()
        fee = self.tournament.entry_fee_bdt or 0

        pm = (cleaned.get("payment_method") or "").strip().lower()
        ref = (cleaned.get("payment_reference") or "").strip()

        if fee > 0:
            if not pm:
                self.add_error("payment_method", "Select a payment method.")
            if not ref:
                self.add_error("payment_reference", "Enter the transaction/reference ID.")
            # NOTE: payment_sender intentionally not required here for team flow.
        return cleaned

    def save(self, commit=True):
        self.instance.team = self.cleaned_data["team"]
        self.instance.payment_method = self.cleaned_data.get("payment_method", "")
        self.instance.payment_sender = self.cleaned_data.get("payment_sender", "")
        self.instance.payment_reference = self.cleaned_data.get("payment_reference", "")
        if commit:
            self.instance.full_clean()
            self.instance.save()
        return self.instance
