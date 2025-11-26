from __future__ import annotations

import urllib.error

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from django.views import View
from django.views.generic import FormView

from . import oauth
from .emails import send_otp_email
from .forms import SignUpForm, VerifyEmailForm, EmailOrUsernameAuthenticationForm
from .models import EmailOTP, PendingSignup

User = get_user_model()


# ---------- Helpers ----------

def _pending_session_keys():
    return (
        "pending_signup_id",
        "pending_user_id",
        "pending_email",
        "pending_user_email",
        "pending_signup_email",
        "pending_otp_purpose",
    )


def _clear_pending(session):
    for key in _pending_session_keys():
        session.pop(key, None)


# ---------- Classic auth ----------


class DCLoginView(LoginView):
    template_name = "account/login.html"
    redirect_authenticated_user = True
    form_class = EmailOrUsernameAuthenticationForm
    
    def get_success_url(self):
        # Get the 'next' parameter from GET or POST
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url:
            return next_url
        # Default redirect to homepage
        return reverse('siteui:homepage')


class DCLogoutView(LogoutView):
    next_page = reverse_lazy("siteui:homepage")
    http_method_names = ["get", "post", "options"]
    
    def get(self, request, *args, **kwargs):
        """Allow GET requests for logout - show confirmation or logout directly."""
        return self.post(request, *args, **kwargs)


class SignUpView(FormView):
    template_name = "account/signup.html"
    form_class = SignUpForm
    success_url = reverse_lazy("account:verify_email_otp")

    def form_valid(self, form):
        EmailOTP.prune_stale_unverified()
        pending = form.save()
        try:
            otp = EmailOTP.issue(pending_signup=pending)
        except EmailOTP.RequestThrottled as exc:
            pending.delete()
            wait_seconds = max(exc.retry_after, 1)
            minutes = (wait_seconds + 59) // 60
            messages.error(
                self.request,
                f"Too many verification attempts. Please wait about {minutes} minute(s) and try again.",
            )
            return self.form_invalid(form)

        send_otp_email(pending, otp.code, expires_in_minutes=EmailOTP.EXPIRATION_MINUTES)

        session = self.request.session
        session["pending_signup_id"] = pending.id
        session["pending_email"] = pending.email
        session["pending_otp_purpose"] = otp.purpose
        session.pop("pending_user_id", None)
        session.pop("pending_user_email", None)
        session.pop("pending_signup_email", None)
        messages.info(self.request, "We sent a 6-digit code to your email.")
        return super().form_valid(form)


from django.shortcuts import redirect, render
@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    # Redirect to the unified profile page handled by apps.user_profile
    return redirect('user_profile:profile')


# ---------- Email OTP ----------


class VerifyEmailView(FormView):
    template_name = "account/verify_email_otp.html"
    form_class = VerifyEmailForm
    success_url = reverse_lazy("account:profile")

    def dispatch(self, request, *args, **kwargs):
        pending_subject = self._get_pending_subject()
        if not pending_subject:
            messages.info(request, "Nothing to verify. Please sign in or sign up.")
            return redirect("account:login")
        if isinstance(pending_subject, User) and pending_subject.is_verified:
            _clear_pending(request.session)
            messages.success(request, "Email already verified. You can sign in now.")
            return redirect("account:login")
        return super().dispatch(request, *args, **kwargs)

    def _get_pending_subject(self):
        session = self.request.session
        signup_id = session.get("pending_signup_id")
        if signup_id:
            pending = PendingSignup.objects.filter(id=signup_id).first()
            if pending:
                return pending
        user_id = session.get("pending_user_id")
        if user_id:
            return User.objects.filter(id=user_id).first()
        return None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        email = self.request.session.get("pending_email") or self.request.session.get("pending_user_email") or self.request.session.get("pending_signup_email")
        ctx["pending_email"] = email
        return ctx

    def form_valid(self, form):
        subject = self._get_pending_subject()
        if not subject:
            messages.error(self.request, "No pending verification found.")
            _clear_pending(self.request.session)
            return redirect("account:signup")

        otp_qs = EmailOTP.objects.filter(is_used=False)
        if isinstance(subject, PendingSignup):
            otp_qs = otp_qs.filter(pending_signup=subject)
        else:
            otp_qs = otp_qs.filter(user=subject)
        otp = otp_qs.order_by("-created_at").first()
        if not otp:
            messages.error(self.request, "No active code. Please request a new one.")
            return self.form_invalid(form)

        result = otp.verify_code(form.cleaned_data["code"])
        if result.success:
            auth_user = result.user or (subject if isinstance(subject, User) else None)
            if auth_user:
                login(self.request, auth_user)
            _clear_pending(self.request.session)
            messages.success(self.request, "Email verified - welcome!")
            return super().form_valid(form)

        if result.locked:
            _clear_pending(self.request.session)
            messages.error(
                self.request,
                "Too many incorrect attempts. Please sign up again to restart the process.",
            )
            return redirect("account:signup")

        messages.error(self.request, result.reason or "Invalid or expired code.")
        return self.form_invalid(form)


class ResendOTPView(View):
    def post(self, request):
        pending = None
        subject = None
        signup_id = request.session.get("pending_signup_id")
        if signup_id:
            pending = PendingSignup.objects.filter(id=signup_id).first()
            subject = pending
        if not subject:
            user_id = request.session.get("pending_user_id")
            if user_id:
                subject = User.objects.filter(id=user_id).first()

        if not subject:
            messages.error(request, "No pending verification found.")
            return redirect("account:signup")

        try:
            otp = EmailOTP.issue(user=subject if isinstance(subject, User) else None, pending_signup=pending if pending else None)
        except EmailOTP.RequestThrottled as exc:
            wait_seconds = max(exc.retry_after, 1)
            minutes = (wait_seconds + 59) // 60
            messages.info(request, f"Please wait about {minutes} minute(s) before requesting another code.")
            return redirect("account:verify_email_otp")

        send_otp_email(subject, otp.code, expires_in_minutes=EmailOTP.EXPIRATION_MINUTES)
        request.session["pending_otp_purpose"] = otp.purpose
        messages.success(request, "A new verification code has been sent.")
        return redirect("account:verify_email_otp")


# ---------- Google OAuth ----------


class GoogleLoginStart(View):
    def get(self, request):
        client_id = settings.GOOGLE_OAUTH_CLIENT_ID
        redirect_uri = _build_google_redirect_uri(request)
        state = get_random_string(24)
        request.session["google_oauth_state"] = state
        url = oauth.build_auth_url(client_id, redirect_uri, state)
        return HttpResponseRedirect(url)


class GoogleCallback(View):
    def get(self, request):
        state = request.GET.get("state")
        code = request.GET.get("code")
        if not state or state != request.session.get("google_oauth_state"):
            return HttpResponseBadRequest("Bad OAuth state")

        client_id = settings.GOOGLE_OAUTH_CLIENT_ID
        client_secret = settings.GOOGLE_OAUTH_CLIENT_SECRET
        redirect_uri = _build_google_redirect_uri(request)

        try:
            info = oauth.exchange_code_for_userinfo(
                code=code,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
            )
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="ignore")
            return HttpResponseBadRequest(f"Google token exchange failed ({e.code}). {detail}")

        email = info.get("email")
        sub = info.get("sub")
        name = info.get("name") or (email.split("@")[0] if email else f"user-{sub[:6]}")
        if not email:
            return HttpResponseBadRequest("Google login requires email scope")

        user, created = User.objects.get_or_create(
            email=email,
            defaults={"username": _unique_username_from(name), "is_active": True, "is_verified": True},
        )
        if created and not user.email_verified_at:
            user.email_verified_at = timezone.now()
            user.save(update_fields=["email_verified_at"])
        if created:
            messages.success(request, "Welcome with Google!")
        login(request, user)
        request.session.pop("google_oauth_state", None)
        return redirect("account:profile")


def _build_google_redirect_uri(request):
    host = request.get_host()
    path = reverse("account:google_callback")
    if host.endswith(".ngrok-free.app") or host.endswith(".trycloudflare.com"):
        return f"https://{host}{path}"
    if host.startswith("localhost") or host.startswith("127.0.0.1"):
        return f"http://{host}{path}"
    base = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    return base + path if base else f"http://{host}{path}"


def _unique_username_from(base: str) -> str:
    base = slugify(base) or "user"
    i, candidate = 0, base
    while User.objects.filter(username__iexact=candidate).exists():
        i += 1
        candidate = f"{base}{i}"
    return candidate


def unique_username_from(base: str) -> str:
    return _unique_username_from(base)
