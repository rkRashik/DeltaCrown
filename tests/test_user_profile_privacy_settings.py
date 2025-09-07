# tests/test_user_profile_privacy_settings.py
import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

def test_privacy_flags_update(client, django_user_model):
    user = django_user_model.objects.create_user(username="rashik", password="pw", email="r@example.com")
    # Ensure profile exists (your project uses OneToOne with related_name="profile")
    from apps.user_profile.models import UserProfile
    UserProfile.objects.get_or_create(user=user)

    client.login(username="rashik", password="pw")
    url = reverse("user_profile:edit")

    # GET loads
    res = client.get(url)
    assert res.status_code == 200

    # POST toggles
    data = {
        "display_name": "Rashik",
        "region": "BD",
        "bio": "hi",
        "discord_id": "",
        "riot_id": "",
        "efootball_id": "",
        "is_private": "on",
        "show_email": "",        # unchecked
        "show_phone": "on",
        "show_socials": "on",
    }
    res = client.post(url, data)
    assert res.status_code in (302, 200)

    prof = UserProfile.objects.get(user=user)
    assert prof.is_private is True
    assert prof.show_email is False
    assert prof.show_phone is True
    assert prof.show_socials is True
