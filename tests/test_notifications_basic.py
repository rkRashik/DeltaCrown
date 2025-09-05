import pytest
from django.contrib.auth import get_user_model

from apps.notifications.services import emit
from apps.notifications.models import Notification

User = get_user_model()


@pytest.mark.django_db
def test_emit_dedup_via_fingerprint():
    u = User.objects.create_user("u1", "u1@example.com", "x")
    fp = "fp:abc:123"
    r1 = emit([u], event="generic", title="Hello", fingerprint=fp)
    r2 = emit([u], event="generic", title="Hello again", fingerprint=fp)

    assert r1.created == 1 and r1.skipped == 0
    assert r2.created == 0 and r2.skipped == 1
    assert Notification.objects.filter(recipient=u).count() == 1
