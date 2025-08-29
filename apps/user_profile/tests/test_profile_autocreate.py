import pytest
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile

User = get_user_model()

@pytest.mark.django_db
def test_profile_autocreated_on_user_create():
    u = User.objects.create_user(username="alice", password="x")
    assert UserProfile.objects.filter(user=u).exists()

@pytest.mark.django_db
def test_backfill_idempotent():
    u = User.objects.create_user(username="bob", password="x")
    # simulate losing the profile then ensure get_or_create recovers
    UserProfile.objects.filter(user=u).delete()
    UserProfile.objects.get_or_create(user=u)
    assert UserProfile.objects.filter(user=u).count() == 1
