"""Mobile auth endpoints under /api/mobile/v1/auth/.

Reuses the existing accounts plumbing:
- ``PendingSignup``/``EmailOTP`` for signup + verification (same flow as web)
- ``send_otp_email`` for delivery
- ``EmailOrUsernameBackend`` rules (active + not scheduled for deletion)
- SimpleJWT for token issue/refresh

Every response goes through the mobile envelope.
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from apps.accounts.emails import send_otp_email
from apps.accounts.models import AccountDeletionRequest, EmailOTP, PendingSignup

from ..base import MobileApiView
from ..responses import error_response, success_response
from ..serializers import serialize_mobile_profile
from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    RefreshSerializer,
    RegisterSerializer,
    ResendOtpSerializer,
    VerifyOtpSerializer,
)


logger = logging.getLogger(__name__)
User = get_user_model()


def _compact_user(user) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "profile": serialize_mobile_profile(getattr(user, "profile", None)),
    }


def _issue_token_pair(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def _account_blocked_reason(user) -> Optional[str]:
    if not user.is_active:
        return "account_inactive"
    try:
        deletion = getattr(user, "deletion_request", None)
        if deletion and deletion.status == AccountDeletionRequest.Status.SCHEDULED:
            return "account_scheduled_for_deletion"
    except AccountDeletionRequest.DoesNotExist:
        pass
    if not getattr(user, "is_verified", True):
        return "account_unverified"
    return None


def _validation_error(code: str, message: str, details=None):
    return error_response(
        code=code,
        message=message,
        details=details or {},
        status=http_status.HTTP_400_BAD_REQUEST,
    )


def _serializer_or_error(serializer_cls, data) -> Tuple[Optional[object], Optional[object]]:
    serializer = serializer_cls(data=data or {})
    if not serializer.is_valid():
        return None, _validation_error(
            "invalid_request",
            "Invalid request payload.",
            details=serializer.errors,
        )
    return serializer.validated_data, None


class MobileLoginView(MobileApiView):
    """POST /api/mobile/v1/auth/login/ — identifier (username|email) + password."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        data, err = _serializer_or_error(LoginSerializer, request.data)
        if err is not None:
            return err

        identifier = (data["identifier"] or "").strip()
        password = data["password"]

        # ``EmailOrUsernameBackend`` accepts either form and already enforces
        # active + non-scheduled-deletion rules. authenticate() returns None
        # for any failure — never reveal whether the user exists.
        user = authenticate(request, username=identifier, password=password)
        if user is None:
            return error_response(
                code="invalid_credentials",
                message="Incorrect email/username or password.",
                status=http_status.HTTP_401_UNAUTHORIZED,
            )

        reason = _account_blocked_reason(user)
        if reason == "account_inactive":
            return error_response(
                code="account_inactive",
                message="This account is currently disabled.",
                status=http_status.HTTP_403_FORBIDDEN,
            )
        if reason == "account_scheduled_for_deletion":
            return error_response(
                code="account_scheduled_for_deletion",
                message="This account is scheduled for deletion. Cancel the deletion request to sign in.",
                status=http_status.HTTP_403_FORBIDDEN,
            )
        if reason == "account_unverified":
            return error_response(
                code="account_unverified",
                message="Verify your email before signing in.",
                status=http_status.HTTP_403_FORBIDDEN,
            )

        tokens = _issue_token_pair(user)
        return success_response({**tokens, "user": _compact_user(user)})


class MobileRegisterView(MobileApiView):
    """POST /api/mobile/v1/auth/register/ — start signup; sends OTP."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        data, err = _serializer_or_error(RegisterSerializer, request.data)
        if err is not None:
            return err

        username = data["username"].strip()
        email = data["email"].strip().lower()
        password = data["password"]

        try:
            validate_password(password)
        except DjangoValidationError as exc:
            return _validation_error(
                "weak_password",
                "Password does not meet the strength requirements.",
                details={"password": list(exc.messages)},
            )

        # Opportunistic pruning matches the web signup form's behavior so a
        # stale row from days ago can't block a fresh attempt.
        try:
            EmailOTP.prune_stale_unverified()
        except Exception:
            pass

        if User.objects.filter(username__iexact=username).exists():
            return _validation_error(
                "username_taken", "This username is already taken.", details={"field": "username"}
            )
        if User.objects.filter(email__iexact=email).exists():
            return _validation_error(
                "email_taken", "This email is already in use.", details={"field": "email"}
            )

        # Same-email resume mirrors web signup: replace any pending row for
        # the same email atomically. Username-only collisions with a *different*
        # email block.
        same_email_pending = PendingSignup.objects.filter(email__iexact=email).first()
        username_pending_qs = PendingSignup.objects.filter(username__iexact=username)
        if same_email_pending is not None:
            username_pending_qs = username_pending_qs.exclude(pk=same_email_pending.pk)
        if username_pending_qs.exists():
            return _validation_error(
                "username_pending",
                "This username is pending verification for a different email.",
                details={"field": "username"},
            )

        password_hash = make_password(password)
        try:
            with transaction.atomic():
                pending = (
                    PendingSignup.objects.select_for_update()
                    .filter(email__iexact=email)
                    .first()
                )
                if pending:
                    pending.username = username
                    pending.email = email
                    pending.password_hash = password_hash
                    pending.created_at = timezone.now()
                    pending.save(update_fields=["username", "email", "password_hash", "created_at"])
                    EmailOTP.objects.filter(pending_signup=pending).delete()
                else:
                    pending = PendingSignup.objects.create(
                        username=username, email=email, password_hash=password_hash
                    )
        except IntegrityError:
            return _validation_error(
                "duplicate_pending",
                "A signup for this email or username is already pending. Please verify it or try again.",
            )

        try:
            otp = EmailOTP.issue(pending_signup=pending)
        except EmailOTP.RequestThrottled as exc:
            return error_response(
                code="otp_throttled",
                message="Too many verification attempts. Please wait and try again.",
                details={"retry_after_seconds": exc.retry_after},
                status=http_status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            sent = send_otp_email(pending, otp.code, expires_in_minutes=EmailOTP.EXPIRATION_MINUTES)
        except Exception as exc:
            logger.exception("Mobile signup OTP email failed: pending_signup_id=%s err=%s", pending.id, exc)
            sent = 0
        if sent < 1:
            return error_response(
                code="email_send_failed",
                message="We couldn't send the verification email right now. Please try again.",
                status=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return success_response(
            {
                "pending_signup_id": pending.id,
                "email": pending.email,
                "otp_required": True,
                "message": "Verification code sent.",
            },
            status=http_status.HTTP_201_CREATED,
        )


class MobileVerifyOtpView(MobileApiView):
    """POST /api/mobile/v1/auth/verify-otp/ — finalize signup, issue JWTs."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        data, err = _serializer_or_error(VerifyOtpSerializer, request.data)
        if err is not None:
            return err

        try:
            pending = PendingSignup.objects.get(pk=data["pending_signup_id"])
        except PendingSignup.DoesNotExist:
            return error_response(
                code="pending_signup_not_found",
                message="Verification session expired. Please sign up again.",
                status=http_status.HTTP_404_NOT_FOUND,
            )

        otp = (
            EmailOTP.objects.filter(pending_signup=pending, is_used=False)
            .order_by("-created_at")
            .first()
        )
        if otp is None:
            return error_response(
                code="otp_not_found",
                message="No active verification code. Please request a new one.",
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        result = otp.verify_code(data["otp"])
        if result.success:
            user = result.user
            if user is None:
                logger.error("Mobile OTP verify succeeded but returned no user; pending_id=%s", pending.id)
                return error_response(
                    code="verification_failed",
                    message="Verification failed. Please try again.",
                    status=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            tokens = _issue_token_pair(user)
            return success_response({**tokens, "user": _compact_user(user)})

        if result.locked:
            return error_response(
                code="otp_locked",
                message="Too many incorrect attempts. Please sign up again to restart.",
                status=http_status.HTTP_429_TOO_MANY_REQUESTS,
            )

        return error_response(
            code="otp_invalid",
            message=result.reason or "Invalid or expired code.",
            status=http_status.HTTP_400_BAD_REQUEST,
        )


class MobileResendOtpView(MobileApiView):
    """POST /api/mobile/v1/auth/resend-otp/ — reissue verification code."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        data, err = _serializer_or_error(ResendOtpSerializer, request.data)
        if err is not None:
            return err

        try:
            pending = PendingSignup.objects.get(pk=data["pending_signup_id"])
        except PendingSignup.DoesNotExist:
            return error_response(
                code="pending_signup_not_found",
                message="Verification session expired. Please sign up again.",
                status=http_status.HTTP_404_NOT_FOUND,
            )

        try:
            otp = EmailOTP.issue(pending_signup=pending)
        except EmailOTP.RequestThrottled as exc:
            return error_response(
                code="otp_throttled",
                message="Please wait before requesting another code.",
                details={"retry_after_seconds": exc.retry_after},
                status=http_status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            sent = send_otp_email(pending, otp.code, expires_in_minutes=EmailOTP.EXPIRATION_MINUTES)
        except Exception as exc:
            logger.exception("Mobile resend OTP email failed: pending_signup_id=%s err=%s", pending.id, exc)
            sent = 0
        if sent < 1:
            return error_response(
                code="email_send_failed",
                message="We couldn't send the verification email right now. Please try again.",
                status=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return success_response({"message": "Verification code resent."})


class MobileRefreshView(MobileApiView):
    """POST /api/mobile/v1/auth/refresh/ — wrap SimpleJWT refresh in envelope."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        data, err = _serializer_or_error(RefreshSerializer, request.data)
        if err is not None:
            return err

        # Lazy import keeps test settings that skip the rest_framework_simplejwt
        # serializer module from blowing up at import time.
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer

        serializer = TokenRefreshSerializer(data={"refresh": data["refresh"]})
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as exc:
            return error_response(
                code="invalid_refresh_token",
                message="Refresh token is invalid or expired.",
                details={"detail": str(getattr(exc, "detail", exc))},
                status=http_status.HTTP_401_UNAUTHORIZED,
            )

        return success_response(
            {k: v for k, v in serializer.validated_data.items() if k in ("access", "refresh")}
        )


class MobileLogoutView(MobileApiView):
    """POST /api/mobile/v1/auth/logout/ — blacklist refresh token if enabled."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        data, err = _serializer_or_error(LogoutSerializer, request.data)
        if err is not None:
            return err

        try:
            token = RefreshToken(data["refresh"])
        except TokenError as exc:
            return error_response(
                code="invalid_refresh_token",
                message="Refresh token is invalid or expired.",
                details={"detail": str(exc)},
                status=http_status.HTTP_401_UNAUTHORIZED,
            )

        # Server-side invalidation only works when the blacklist app is
        # installed; surface that fact instead of silently pretending.
        blacklisted = False
        try:
            token.blacklist()
            blacklisted = True
        except AttributeError:
            # SimpleJWT didn't expose .blacklist() — unexpected with current versions.
            pass
        except Exception as exc:
            # ``token_blacklist`` app not installed or DB unavailable. Logged
            # so ops can decide whether to enable the blacklist app.
            logger.info("Refresh token not blacklisted server-side: %s", exc)

        return success_response(
            {
                "message": "Logged out successfully.",
                "blacklisted": blacklisted,
            }
        )
