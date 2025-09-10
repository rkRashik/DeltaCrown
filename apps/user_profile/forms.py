# apps/user_profile/forms.py
from __future__ import annotations

from django import forms
from django.apps import apps


UserProfile = apps.get_model("user_profile", "UserProfile")


class PrivacySettingsForm(forms.ModelForm):
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
