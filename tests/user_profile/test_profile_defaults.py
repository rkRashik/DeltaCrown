import pytest
from django.contrib.auth import get_user_model

from apps.user_profile.models_main import UserProfile


@pytest.mark.django_db
def test_user_profile_created_with_safe_bio_defaults():
    User = get_user_model()

    user = User.objects.create_user(
        username="otp_profile_default_user",
        email="otp_profile_default_user@example.com",
        password="pass1234",
    )

    profile = UserProfile.objects.get(user=user)

    assert profile.bio == ""
    assert profile.about_bio == ""
    assert profile is not None
