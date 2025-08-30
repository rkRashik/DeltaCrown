from django import forms
from django.core.exceptions import ValidationError
from apps.user_profile.models import UserProfile

class TeamInviteForm(forms.Form):
    username_or_email = forms.CharField(max_length=200)

    def clean_username_or_email(self):
        value = self.cleaned_data['username_or_email']
        try:
            # Check if it's a username
            user = UserProfile.objects.get(user__username=value)
        except UserProfile.DoesNotExist:
            try:
                # Check if it's an email
                user = UserProfile.objects.get(user__email=value)
            except UserProfile.DoesNotExist:
                raise ValidationError("User not found. Please provide a valid username or email.")
        return user
