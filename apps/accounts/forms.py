from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password

from .models import EmailOTP, PendingSignup

User = get_user_model()


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    """
    Custom authentication form that accepts either username or email.
    """
    username = forms.CharField(
        label="Username or Email",
        max_length=254,
        widget=forms.TextInput(attrs={
            'autofocus': True,
            'placeholder': 'Enter your username or email'
        })
    )

    error_messages = {
        'invalid_login': (
            "Please enter a correct username/email and password. Note that both "
            "fields may be case-sensitive."
        ),
        'inactive': "This account is inactive.",
    }


class SignUpForm(forms.Form):
    username = forms.CharField(label="Username", max_length=150)
    email = forms.EmailField(label="Email", required=True)
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Drop expired pending signups + orphaned OTPs before validation runs
        # so a stale record from days ago can never block a fresh attempt.
        try:
            EmailOTP.prune_stale_unverified()
        except Exception:
            # Pruning failure must not crash the signup page.
            pass

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords do not match.")
        if password1:
            validate_password(password1)

        username = cleaned.get("username")
        email = cleaned.get("email")
        if not username or not email:
            return cleaned

        # Same-email resume: if a pending signup exists for this email it will
        # be replaced atomically in save(). The username for that pending row
        # may collide with the submitted username — that is the resume case
        # and must NOT block.
        same_email_pending = (
            PendingSignup.objects.filter(email__iexact=email).first()
        )
        username_pending_qs = PendingSignup.objects.filter(
            username__iexact=username,
        )
        if same_email_pending is not None:
            username_pending_qs = username_pending_qs.exclude(
                pk=same_email_pending.pk,
            )
        if username_pending_qs.exists():
            self.add_error(
                "username",
                "This username is pending verification for a different "
                "email. Pick another username, or finish verifying that "
                "signup.",
            )
        return cleaned

    def save(self):
        # Replace any prior pending signup for this email so the user gets
        # a clean record (and a fresh OTP downstream). Cascading deletes
        # remove old EmailOTPs.
        PendingSignup.objects.filter(
            email__iexact=self.cleaned_data["email"],
        ).delete()
        return PendingSignup.objects.create(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password_hash=make_password(self.cleaned_data["password1"]),
        )


class VerifyEmailForm(forms.Form):
    code = forms.CharField(label="Verification code", min_length=6, max_length=6)
    email = forms.EmailField(label="Email", required=False)
