from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .views import (
    DCLoginView, DCLogoutView, SignUpView, profile_view,
    VerifyEmailView, ResendOTPView,
    GoogleLoginStart, GoogleCallback
)

app_name = "accounts"

urlpatterns = [
    path("login/", DCLoginView.as_view(), name="login"),
    path("logout/", DCLogoutView.as_view(), name="logout"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("profile/", profile_view, name="profile"),

    # OTP verify
    path("verify/", VerifyEmailView.as_view(), name="verify_email"),
    path("verify/resend/", ResendOTPView.as_view(), name="resend_otp"),

    # Password reset (keeps namespaced email template)
    path("password_reset/", auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset_form.html",
        email_template_name="accounts/password_reset_email.txt",
        success_url=reverse_lazy("accounts:password_reset_done"),
    ), name="password_reset"),
    path("password_reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html"
    ), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html",
        success_url=reverse_lazy("accounts:password_reset_complete"),
    ), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html"
    ), name="password_reset_complete"),

    # Google OAuth
    path("google/login/", GoogleLoginStart.as_view(), name="google_login"),
    path("google/callback/", GoogleCallback.as_view(), name="google_callback"),
]
