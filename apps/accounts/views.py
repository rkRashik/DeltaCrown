from __future__ import annotations

import hashlib
import logging
import secrets
import urllib.parse

from django.conf import settings
from django.core.cache import cache
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
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

logger = logging.getLogger(__name__)

User = get_user_model()


# ---------- IP-based Rate Limiting Helper ----------


def _get_client_ip(request):
    """Extract client IP, respecting X-Forwarded-For behind reverse proxies."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _is_rate_limited(request, scope, max_attempts, window_seconds):
    """
    Cache-based rate limiter for Django views.
    Returns True if the request should be blocked.
    """
    ip = _get_client_ip(request)
    key = f"ratelimit:{scope}:{hashlib.sha256(ip.encode()).hexdigest()[:16]}"
    attempts = cache.get(key, 0)
    if attempts >= max_attempts:
        return True
    cache.set(key, attempts + 1, timeout=window_seconds)
    return False


# ---------- Safe Password Reset ----------


class SafePasswordResetView(PasswordResetView):
    """
    Wraps Django's PasswordResetView so that SMTP / email-sending errors
    don't crash the page with a 500/502.  Instead the user is silently
    redirected to the 'done' page.  The real error is logged so you can
    diagnose email-configuration issues in Render logs.
    """

    def post(self, request, *args, **kwargs):
        # Rate limit: 5 requests per 60 seconds per IP
        if _is_rate_limited(request, 'password_reset', max_attempts=5, window_seconds=60):
            logger.warning("Password reset rate limited: ip=%s", _get_client_ip(request))
            return HttpResponseRedirect(self.get_success_url())
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except Exception:
            logger.exception(
                "Password-reset email failed to send – SMTP / email backend error"
            )
            # Still redirect to the "email sent" page so we don't leak
            # information about whether the email address exists.
            return HttpResponseRedirect(self.get_success_url())


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


def _bind_pending_to_session(session, subject):
    """Persist subject identity into the session for verify/resend recovery."""
    if isinstance(subject, PendingSignup):
        session["pending_signup_id"] = subject.id
        session["pending_email"] = subject.email
        session.pop("pending_user_id", None)
        session.pop("pending_user_email", None)
    elif isinstance(subject, User):
        session["pending_user_id"] = subject.id
        session["pending_email"] = subject.email
        session.pop("pending_signup_id", None)
        session.pop("pending_signup_email", None)


def _resolve_pending_subject(request, *, email_hint=None):
    """Find the pending signup or unverified user for the current verify flow.

    Resolution order:
      1. Session-stored ``pending_signup_id`` / ``pending_user_id``.
      2. Caller-supplied ``email_hint`` (typically from form or query string).
      3. ``pending_email`` left over in the session.

    When email-based recovery succeeds, the session is rebound so subsequent
    requests behave as if the user never lost it.
    """
    session = request.session
    signup_id = session.get("pending_signup_id")
    if signup_id:
        pending = PendingSignup.objects.filter(id=signup_id).first()
        if pending:
            return pending
        session.pop("pending_signup_id", None)

    user_id = session.get("pending_user_id")
    if user_id:
        user = User.objects.filter(id=user_id).first()
        if user:
            return user
        session.pop("pending_user_id", None)

    candidate_emails = []
    if email_hint:
        candidate_emails.append(email_hint)
    fallback_email = (
        session.get("pending_email")
        or session.get("pending_signup_email")
        or session.get("pending_user_email")
    )
    if fallback_email and fallback_email not in candidate_emails:
        candidate_emails.append(fallback_email)

    for raw in candidate_emails:
        email = (raw or "").strip().lower()
        if not email:
            continue
        pending = PendingSignup.objects.filter(email__iexact=email).first()
        if pending:
            _bind_pending_to_session(session, pending)
            return pending
        user = User.objects.filter(
            email__iexact=email, is_verified=False,
        ).first()
        if user:
            _bind_pending_to_session(session, user)
            return user
    return None


# ---------- Classic auth ----------


class DCLoginView(LoginView):
    template_name = "account/login.html"
    redirect_authenticated_user = True
    form_class = EmailOrUsernameAuthenticationForm

    def post(self, request, *args, **kwargs):
        # Rate limit: 10 login attempts per 60 seconds per IP
        if _is_rate_limited(request, 'login', max_attempts=10, window_seconds=60):
            logger.warning("Login rate limited: ip=%s", _get_client_ip(request))
            from django.contrib import messages as django_messages
            django_messages.error(request, "Too many login attempts. Please try again later.")
            return self.get(request, *args, **kwargs)
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["google_oauth_enabled"] = bool(settings.GOOGLE_OAUTH_CLIENT_ID)
        return ctx

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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["google_oauth_enabled"] = bool(settings.GOOGLE_OAUTH_CLIENT_ID)
        return ctx

    def form_valid(self, form):
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
        _bind_pending_to_session(session, pending)
        session["pending_otp_purpose"] = otp.purpose
        messages.info(self.request, "We sent a 6-digit code to your email.")
        return super().form_valid(form)


from django.shortcuts import redirect, render
@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    # Redirect to the unified profile page handled by apps.user_profile
    return redirect('user_profile:profile', username=request.user.username)


# ---------- Email OTP ----------


class VerifyEmailView(FormView):
    template_name = "account/verify_email_otp.html"
    form_class = VerifyEmailForm
    # success_url will be set dynamically in form_valid after login
    success_url = None

    def dispatch(self, request, *args, **kwargs):
        # Cheap opportunistic cleanup so a stale row never confuses lookup.
        try:
            EmailOTP.prune_stale_unverified()
        except Exception:
            pass

        email_hint = (
            (request.POST.get("email") if request.method == "POST" else None)
            or request.GET.get("email")
        )
        pending_subject = _resolve_pending_subject(
            request, email_hint=email_hint,
        )
        if isinstance(pending_subject, User) and pending_subject.is_verified:
            _clear_pending(request.session)
            messages.success(request, "Email already verified. You can sign in now.")
            return redirect("account:login")
        # If no subject is resolvable we still render the page so the user
        # can recover by typing their email — only a POST without any email
        # at all bounces back to signup.
        if pending_subject is None and request.method == "POST" and not email_hint:
            messages.error(
                request,
                "Your verification session ended. Enter the email you signed "
                "up with so we can find your code.",
            )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        session = self.request.session
        email = (
            session.get("pending_email")
            or session.get("pending_user_email")
            or session.get("pending_signup_email")
            or self.request.GET.get("email")
            or ""
        )
        ctx["pending_email"] = email
        ctx["recovery_mode"] = not bool(
            session.get("pending_signup_id") or session.get("pending_user_id"),
        )
        return ctx

    def form_valid(self, form):
        email_hint = form.cleaned_data.get("email") or self.request.POST.get("email")
        subject = _resolve_pending_subject(
            self.request, email_hint=email_hint,
        )
        if not subject:
            messages.error(
                self.request,
                "We couldn't find a pending signup for that email. "
                "Please sign up again.",
            )
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
            # If this was a signup flow (PendingSignup), send the user to the homepage.
            if isinstance(subject, PendingSignup):
                return redirect('siteui:homepage')
            # Otherwise send to profile (existing user flows)
            if auth_user:
                return redirect('user_profile:profile', username=auth_user.username)
            return redirect('account:login')

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
        try:
            EmailOTP.prune_stale_unverified()
        except Exception:
            pass

        email_hint = request.POST.get("email") or request.GET.get("email")
        subject = _resolve_pending_subject(request, email_hint=email_hint)
        if not subject:
            messages.error(
                request,
                "Could not find a pending signup. Please sign up again.",
            )
            return redirect("account:signup")

        try:
            otp = EmailOTP.issue(
                user=subject if isinstance(subject, User) else None,
                pending_signup=subject if isinstance(subject, PendingSignup) else None,
            )
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
        if not client_id:
            messages.error(request, "Google sign-in is not configured yet. Please use email/password.")
            return redirect("account:login")
        redirect_uri = _build_google_redirect_uri(request)
        state = get_random_string(24)
        request.session["google_oauth_state"] = state
        # Preserve 'next' across the OAuth round-trip
        next_url = request.GET.get("next", "")
        if next_url:
            request.session["google_oauth_next"] = next_url
        url = oauth.build_auth_url(client_id, redirect_uri, state)
        return HttpResponseRedirect(url)


class GoogleCallback(View):
    def get(self, request):
        # Handle user-cancelled OAuth ("access_denied")
        if request.GET.get("error"):
            messages.info(request, "Google sign-in was cancelled.")
            return redirect("account:login")

        state = request.GET.get("state")
        code = request.GET.get("code")
        if not state or state != request.session.get("google_oauth_state"):
            messages.error(request, "Invalid sign-in session. Please try again.")
            return redirect("account:login")

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
        except Exception as e:
            logger.error("Google OAuth token exchange failed: %s", e)
            messages.error(request, "Google sign-in failed. Please try again or use email/password.")
            return redirect("account:login")

        email = info.get("email")
        if not email:
            messages.error(request, "Google did not provide an email address. Please use email/password sign-in.")
            return redirect("account:login")

        name = info.get("name") or email.split("@")[0]

        # Look up by email (case-insensitive), create if not found
        try:
            user = User.objects.get(email__iexact=email)
            created = False
        except User.DoesNotExist:
            user = User.objects.create_user(
                username=_unique_username_from(name),
                email=email,
                password=None,  # unusable password — must use Google or reset flow
                is_active=True,
            )
            setattr(user, "is_verified", True)
            user.email_verified_at = timezone.now()
            user.save(update_fields=["is_verified", "email_verified_at"])
            created = True

        # Ensure existing users are marked verified (Google confirmed their email)
        update_fields = []
        if not user.is_active:
            user.is_active = True
            update_fields.append("is_active")
        if not getattr(user, "is_verified", True):
            user.is_verified = True
            update_fields.append("is_verified")
        if not user.email_verified_at:
            user.email_verified_at = timezone.now()
            update_fields.append("email_verified_at")
        if update_fields:
            user.save(update_fields=update_fields)

        if created:
            messages.success(request, f"Welcome to DeltaCrown, {user.username}! Your account has been created.")
        else:
            messages.success(request, f"Welcome back, {user.username}!")

        login(request, user, backend="apps.accounts.backends.EmailOrUsernameBackend")
        request.session.pop("google_oauth_state", None)

        next_url = request.session.pop("google_oauth_next", None) or reverse("siteui:homepage")
        return redirect(next_url)


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


# ---------------------------------------------------------------------------
# Discord OAuth2 Account Linking
# ---------------------------------------------------------------------------

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_OAUTH_SCOPES = "identify"


def _build_discord_redirect_uri(request) -> str:
    """Build the absolute callback URI for Discord OAuth2."""
    host = request.get_host()
    path = reverse("account:discord_callback")
    if host.endswith(".ngrok-free.app") or host.endswith(".trycloudflare.com"):
        return f"https://{host}{path}"
    if host.startswith("localhost") or host.startswith("127.0.0.1"):
        return f"http://{host}{path}"
    base = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    return base + path if base else f"http://{host}{path}"


class DiscordLinkStart(View):
    """
    Step 1 of Discord OAuth2 linking.

    Accepts an optional `state` query-param generated by the bot (encodes the
    Discord user-ID so the callback can notify them).  Requires the user to be
    logged in — unauthenticated visitors are redirected to login first.

    URL: /account/discord/link?state=<bot_state>
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        if not request.user.is_authenticated:
            next_url = request.get_full_path()
            return redirect(f"{reverse('account:login')}?next={urllib.parse.quote(next_url)}")

        client_id = getattr(settings, "DISCORD_CLIENT_ID", "")
        if not client_id:
            messages.error(request, "Discord integration not configured yet.")
            return redirect(reverse("user_profile:settings"))

        # Preserve the bot's state token if present (used to DM the user on success)
        bot_state = request.GET.get("state", "")

        # Generate our own CSRF state token and store it in cache
        csrf_state = secrets.token_urlsafe(32)
        cache.set(
            f"discord_oauth_state:{csrf_state}",
            {"user_id": request.user.pk, "bot_state": bot_state},
            timeout=600,  # 10 minutes
        )

        redirect_uri = _build_discord_redirect_uri(request)
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": DISCORD_OAUTH_SCOPES,
            "state": csrf_state,
            "prompt": "none",  # Skip consent screen if already granted
        }
        discord_auth_url = (
            "https://discord.com/api/oauth2/authorize?"
            + urllib.parse.urlencode(params)
        )
        return redirect(discord_auth_url)


class DiscordCallback(View):
    """
    Step 2 of Discord OAuth2 linking — Discord redirects here after consent.

    Exchanges the code for an access token, fetches the Discord user's identity,
    and stores it in SocialLink(platform='discord').  Queues a Celery task to
    grant the @Linked role.

    URL: /account/discord/callback/
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        error = request.GET.get("error")
        if error:
            messages.error(request, "Discord sign-in was cancelled or denied.")
            return redirect(reverse("user_profile:settings"))

        code = request.GET.get("code")
        state = request.GET.get("state")

        if not code or not state:
            messages.error(request, "Invalid Discord callback — missing parameters.")
            return redirect(reverse("user_profile:settings"))

        # Validate CSRF state
        cache_key = f"discord_oauth_state:{state}"
        cached = cache.get(cache_key)
        if not cached:
            messages.error(request, "Discord link session expired. Please try again.")
            return redirect(reverse("user_profile:settings"))
        cache.delete(cache_key)

        user_id = cached.get("user_id")
        bot_state = cached.get("bot_state", "")

        # Ensure we still have the correct user
        if not request.user.is_authenticated or request.user.pk != user_id:
            messages.error(request, "Session mismatch — please log in and try again.")
            return redirect(reverse("account:login"))

        # Exchange code for access token
        redirect_uri = _build_discord_redirect_uri(request)
        try:
            import requests as http_requests  # avoid shadowing Django's request

            token_resp = http_requests.post(
                f"{DISCORD_API_BASE}/oauth2/token",
                data={
                    "client_id": getattr(settings, "DISCORD_CLIENT_ID", ""),
                    "client_secret": getattr(settings, "DISCORD_CLIENT_SECRET", ""),
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()

            # Fetch Discord user identity
            access_token = token_data["access_token"]
            user_resp = http_requests.get(
                f"{DISCORD_API_BASE}/users/@me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            user_resp.raise_for_status()
            discord_user = user_resp.json()
        except Exception as exc:
            logger.warning("Discord OAuth token exchange failed: %s", exc)
            messages.error(request, "Could not connect to Discord. Please try again.")
            return redirect(reverse("user_profile:settings"))

        discord_id = str(discord_user["id"])
        discord_username = discord_user.get("global_name") or discord_user.get("username", "")

        # Upsert SocialLink(platform='discord')
        from apps.user_profile.models import SocialLink  # lazy import to avoid circular

        SocialLink.objects.update_or_create(
            user=request.user,
            platform="discord",
            defaults={
                "url": f"https://discord.com/users/{discord_id}",
                "handle": discord_username,
                "is_verified": True,
            },
        )

        # Queue the role-grant task (fire-and-forget)
        try:
            from apps.organizations.tasks.discord_sync import sync_discord_linked_role

            sync_discord_linked_role.delay(
                user_id=request.user.pk,
                discord_id=discord_id,
                bot_state=bot_state,
            )
        except Exception as exc:
            logger.warning("Could not queue sync_discord_linked_role: %s", exc)

        messages.success(
            request,
            f"✅ Discord account @{discord_username} linked successfully! "
            "You will receive the @Linked role in the DeltaCrown server shortly.",
        )
        return redirect(reverse("user_profile:settings"))


class DiscordUnlink(LoginRequiredMixin, View):
    """Unlink a user's Discord account.

    Deletes the verified SocialLink(platform='discord') and queues a Celery
    task to strip the @Linked role from the DeltaCrown guild.

    URL: /account/discord/unlink/
    """

    def post(self, request: HttpRequest) -> HttpResponse:
        from apps.user_profile.models import SocialLink

        try:
            link = SocialLink.objects.get(user=request.user, platform="discord")
        except SocialLink.DoesNotExist:
            return JsonResponse({"success": False, "message": "No Discord account linked."})

        # Extract discord_id from the stored URL (https://discord.com/users/<id>)
        discord_id = ""
        if link.url and "/users/" in link.url:
            discord_id = link.url.rsplit("/", 1)[-1]

        link.delete()

        # Queue role-strip task (fire-and-forget)
        if discord_id:
            try:
                from apps.organizations.tasks.discord_sync import strip_discord_linked_role
                strip_discord_linked_role.delay(discord_id=discord_id)
            except Exception as exc:
                logger.warning("Could not queue strip_discord_linked_role: %s", exc)

        return JsonResponse({"success": True, "message": "Discord account unlinked."})
