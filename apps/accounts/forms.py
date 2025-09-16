from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class SignUpForm(forms.Form):
    username = forms.CharField(label="Username", max_length=150)
    email = forms.EmailField(label="Email", required=True)
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords do not match.")
        if password1:
            validate_password(password1)
        return cleaned

    def save(self):
        data = self.cleaned_data
        email = data["email"].strip().lower()
        user = User.objects.create_user(
            username=data["username"],
            email=email,
            password=data["password1"],
            is_active=False,
        )
        if getattr(user, "is_verified", False):
            user.is_verified = False
            user.save(update_fields=["is_verified"])
        return user


class VerifyEmailForm(forms.Form):
    code = forms.CharField(label="Verification code", min_length=6, max_length=6)
