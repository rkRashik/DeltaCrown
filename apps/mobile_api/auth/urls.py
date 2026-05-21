"""URL patterns for /api/mobile/v1/auth/."""
from django.urls import path

from .views import (
    MobileLoginView,
    MobileLogoutView,
    MobileRefreshView,
    MobileRegisterView,
    MobileResendOtpView,
    MobileVerifyOtpView,
)


urlpatterns = [
    path("login/", MobileLoginView.as_view(), name="login"),
    path("register/", MobileRegisterView.as_view(), name="register"),
    path("verify-otp/", MobileVerifyOtpView.as_view(), name="verify_otp"),
    path("resend-otp/", MobileResendOtpView.as_view(), name="resend_otp"),
    path("refresh/", MobileRefreshView.as_view(), name="refresh"),
    path("logout/", MobileLogoutView.as_view(), name="logout"),
]
