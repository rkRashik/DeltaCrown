import pytest
from django.contrib.auth import get_user_model

from apps.user_profile.models import UserProfile
from apps.notifications.models import Notification
from apps.notifications.services import notify, emit


@pytest.mark.django_db
def test_notify_and_emit_alias():
    U = get_user_model()
    u = U.objects.create_user("p1", "p1@e.com", "x")
    p, _ = UserProfile.objects.get_or_create(user=u)

    r = notify([p], Notification.Type.REG_CONFIRMED, title="Welcome")
    assert r["created"] == 1

    # dedupe with same tuple
    r2 = notify([p], Notification.Type.REG_CONFIRMED, title="Welcome", dedupe=True)
    assert r2["skipped"] >= 1

    # alias
    r3 = emit([p], Notification.Type.MATCH_SCHEDULED, title="Match")
    assert r3["created"] == 1
