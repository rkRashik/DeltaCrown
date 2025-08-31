import io
import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.contrib.auth.models import User

pytestmark = pytest.mark.django_db

def make_image_file(name="avatar.png", size=(64, 64), color=(255, 0, 0)):
    buf = io.BytesIO()
    img = Image.new("RGB", size, color)
    img.save(buf, format="PNG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/png")

def test_edit_profile_upload_avatar(client):
    u = User.objects.create_user("alice", password="pw")
    client.force_login(u)

    url = reverse("user_profile:edit")
    f = make_image_file()
    r = client.post(url, {
        "display_name": "Alice",
        "region": "BD",
        "bio": "Hi there",
        "discord_id": "alice#0001",
        "riot_id": "Alice#BD",
        "efootball_id": "alice123",
    }, format="multipart")
    # send files in a second arg if needed by your test runner
    r = client.post(url, {
        "display_name": "Alice",
        "region": "BD",
        "bio": "Hi there",
        "discord_id": "alice#0001",
        "riot_id": "Alice#BD",
        "efootball_id": "alice123",
        "avatar": f,
    })

    assert r.status_code in (200, 302)
    u.refresh_from_db()
    assert u.profile.display_name == "Alice"
    assert u.profile.avatar  # file path set
