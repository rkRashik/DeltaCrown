import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

def test_ics_regeneration_rotates_token_and_invalidates_old(client, django_user_model):
    user = django_user_model.objects.create_user(username="ics", password="pw", email="ics@example.com")
    client.login(username="ics", password="pw")

    # Ensure initial token exists via page load
    url_help = reverse("tournaments:my_matches_ics_link")
    r = client.get(url_help)
    assert r.status_code == 200

    # Extract current token from context by hitting the view's ensure method
    from apps.tournaments.models.userprefs import CalendarFeedToken
    old_token = CalendarFeedToken.objects.get(user=user).token

    # Regenerate
    url_regen = reverse("tournaments:my_matches_ics_regen")
    r2 = client.post(url_regen, follow=True)
    assert r2.status_code in (200, 302)

    new_token = CalendarFeedToken.objects.get(user=user).token
    assert new_token != old_token

    # Old link should 404
    url_old_feed = reverse("tournaments:my_matches_ics", args=[old_token])
    r3 = client.get(url_old_feed)
    assert r3.status_code == 404

    # New link should work (200 and text/calendar)
    url_new_feed = reverse("tournaments:my_matches_ics", args=[new_token])
    r4 = client.get(url_new_feed)
    assert r4.status_code == 200
    assert "text/calendar" in r4.headers.get("Content-Type", "")
