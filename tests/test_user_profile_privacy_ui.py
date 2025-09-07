import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def _ensure_profile(user):
    from django.apps import apps
    UserProfile = apps.get_model("user_profile", "UserProfile")
    prof, _ = UserProfile.objects.get_or_create(user=user)
    return prof


def test_privacy_edit_get(client, django_user_model):
    u = django_user_model.objects.create_user(username="alice", password="pw", email="a@example.com")
    _ensure_profile(u)

    client.login(username="alice", password="pw")
    res = client.get(reverse("user_profile:edit"))
    assert res.status_code == 200
    content = res.content.decode()
    assert "Privacy Settings" in content
    assert "Private profile" in content


def test_privacy_edit_post_updates_flags(client, django_user_model):
    u = django_user_model.objects.create_user(username="bob", password="pw", email="b@example.com")
    prof = _ensure_profile(u)

    client.login(username="bob", password="pw")
    url = reverse("user_profile:edit")
    payload = {
        "is_private": "on",
        "show_email": "on",
        "show_phone": "",
        "show_socials": "on",
    }
    res = client.post(url, data=payload, follow=True)
    assert res.status_code in (200, 302)

    prof.refresh_from_db()
    assert prof.is_private is True
    assert prof.show_email is True
    assert prof.show_phone is False
    assert prof.show_socials is True
