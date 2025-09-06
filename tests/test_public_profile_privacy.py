import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

@pytest.mark.django_db
def test_public_profile_private(client):
    u = User.objects.create_user(username="alice", email="a@example.com", password="x")
    # attach/create profile with privacy flags
    try:
        prof = u.profile  # typical OneToOne
    except Exception:
        from apps.user_profile.models import UserProfile
        prof = UserProfile.objects.create(user=u)
    prof.is_private = True
    prof.save()

    resp = client.get(reverse("user_profile:public_profile", args=["alice"]))
    assert resp.status_code == 200
    assert b"This profile is private" in resp.content

@pytest.mark.django_db
def test_public_profile_toggles(client):
    u = User.objects.create_user(username="bob", email="b@example.com", password="x")
    # ensure profile exists
    try:
        prof = u.profile
    except Exception:
        from apps.user_profile.models import UserProfile
        prof = UserProfile.objects.create(user=u)
    prof.is_private = False
    prof.show_email = True
    prof.show_phone = False
    prof.show_socials = False
    prof.phone = "+8801XXXXXXX"  # if model has it; harmless if ignored in template
    prof.save()

    resp = client.get(reverse("user_profile:public_profile", args=["bob"]))
    assert resp.status_code == 200
    # email visible
    assert b"b@example.com" in resp.content
    # phone hidden
    assert b"+8801" not in resp.content
