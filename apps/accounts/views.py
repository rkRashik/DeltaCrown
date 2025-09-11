from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import FormView
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from django.contrib.auth import get_user_model
import urllib.error
from .forms import SignUpForm, VerifyEmailForm
from .models import EmailOTP
from .emails import send_otp_email
from . import oauth

User = get_user_model()

# ---------- Classic auth ----------
class DCLoginView(LoginView):
    # Use singular 'account/' to match template directory
    template_name = "account/login.html"

class DCLogoutView(LogoutView):
    next_page = reverse_lazy("homepage")

class SignUpView(FormView):
    template_name = "account/signup.html"
    form_class = SignUpForm
    success_url = reverse_lazy("account:verify_email")

    def form_valid(self, form):
        user = form.save()  # is_active = False
        otp = EmailOTP.create_for_user(user)
        send_otp_email(user, otp.code)
        self.request.session["pending_user_id"] = user.id
        messages.info(self.request, "We sent a 6-digit code to your email.")
        return super().form_valid(form)

@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    return render(request, "account/profile.html", {})

# ---------- Email OTP ----------
class VerifyEmailView(FormView):
    template_name = "account/verify_email.html"
    form_class = VerifyEmailForm
    success_url = reverse_lazy("account:profile")

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get("pending_user_id"):
            return redirect("account:login")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user_id = self.request.session.get("pending_user_id")
        user = User.objects.filter(id=user_id).first()
        if not user:
            return HttpResponseBadRequest("No pending user.")
        otp = EmailOTP.objects.filter(user=user, is_used=False).order_by("-created_at").first()
        if not otp or not otp.verify(form.cleaned_data["code"]):
            messages.error(self.request, "Invalid or expired code.")
            return self.form_invalid(form)
        user.is_active = True
        user.save(update_fields=["is_active"])
        login(self.request, user)
        self.request.session.pop("pending_user_id", None)
        messages.success(self.request, "Email verified—welcome!")
        return super().form_valid(form)

class ResendOTPView(View):
    def post(self, request):
        user_id = request.session.get("pending_user_id")
        user = User.objects.filter(id=user_id).first()
        if not user:
            return redirect("account:login")
        last = EmailOTP.objects.filter(user=user).order_by("-created_at").first()
        from django.utils import timezone
        if last and (timezone.now() - last.created_at).total_seconds() < 60:
            messages.info(request, "Please wait a minute before requesting a new code.")
            return redirect("account:verify_email")
        otp = EmailOTP.create_for_user(user)
        send_otp_email(user, otp.code)
        messages.success(request, "A new code has been sent.")
        return redirect("account:verify_email")

# ---------- Google OAuth ----------
class GoogleLoginStart(View):
    def get(self, request):
        client_id = settings.GOOGLE_OAUTH_CLIENT_ID
        redirect_uri = _build_google_redirect_uri(request)  # <— same as callback
        state = get_random_string(24)
        request.session["google_oauth_state"] = state
        url = oauth.build_auth_url(client_id, redirect_uri, state)
        return HttpResponseRedirect(url)


def _build_google_redirect_uri(request):
    host = request.get_host()  # e.g., localhost:8000 or 766c...ngrok-free.app
    path = reverse("account:google_callback")
    if host.endswith(".ngrok-free.app") or host.endswith(".trycloudflare.com"):
        return f"https://{host}{path}"
    if host.startswith("localhost") or host.startswith("127.0.0.1"):
        return f"http://{host}{path}"
    # Fallback: settings.SITE_URL if you ever front this elsewhere
    base = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    return base + path if base else f"http://{host}{path}"

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
            # Helpful error surface for debugging (keeps in dev only)
            detail = e.read().decode(errors="ignore")
            return HttpResponseBadRequest(f"Google token exchange failed ({e.code}). {detail}")

        email = info.get("email")
        sub = info.get("sub")
        name = info.get("name") or (email.split("@")[0] if email else f"user-{sub[:6]}")
        if not email:
            return HttpResponseBadRequest("Google login requires email scope")

        user, created = User.objects.get_or_create(
            email=email,
            defaults={"username": _unique_username_from(name), "is_active": True},
        )
        if created:
            messages.success(request, "Welcome with Google!")
        login(request, user)
        request.session.pop("google_oauth_state", None)
        return redirect("account:profile")

def _unique_username_from(base: str) -> str:
    base = slugify(base) or "user"
    i, candidate = 0, base
    while User.objects.filter(username__iexact=candidate).exists():
        i += 1
        candidate = f"{base}{i}"
    return candidate

def unique_username_from(base: str) -> str:
    base = slugify(base) or "user"
    i, candidate = 0, base
    while User.objects.filter(username__iexact=candidate).exists():
        i += 1
        candidate = f"{base}{i}"
    return candidate
