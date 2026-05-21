"""Serializers for /api/mobile/v1/auth/ endpoints."""
from __future__ import annotations

from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)
    password = serializers.CharField(max_length=512, trim_whitespace=False)


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=512, trim_whitespace=False)


class VerifyOtpSerializer(serializers.Serializer):
    pending_signup_id = serializers.IntegerField(min_value=1)
    otp = serializers.RegexField(regex=r"^\d{6}$", max_length=6, min_length=6)


class ResendOtpSerializer(serializers.Serializer):
    pending_signup_id = serializers.IntegerField(min_value=1)


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
