"""Disposable fixtures for the real entry-point check; never a runtime module."""
import importlib
import io
import json


def arrange(folder, slow, ordinary, lockdown):
    """Called only after the cancellation harness's local DB/socket guards."""
    from django.conf import settings
    from django.contrib.auth import get_user_model, login
    from django.contrib.auth.decorators import login_required
    from django.core.management import call_command
    from django.db import connection
    from django.http import HttpResponse
    from django.urls import include, path
    from django.test import override_settings
    from deltacrown import settings as base_settings

    # Restore the middleware omitted by media QA, in exactly its original order.
    # Its network proxy is inactive in local media mode; sockets remain guarded.
    settings.MIDDLEWARE = list(base_settings.MIDDLEWARE)
    original_urlconf = base_settings.ROOT_URLCONF
    assert settings.DEBUG is False and settings.OWNLOBBY_MEDIA_MODE == "local"
    assert settings.SESSION_ENGINE == "django.contrib.sessions.backends.db"
    middleware = list(settings.MIDDLEWARE)
    if lockdown:
        # Exercise the entry point's actual automatic fail-closed installation.
        settings.OWNLOBBY_MEDIA_MODE = "hybrid"
        assert not any((settings.MEDIA_STORAGE_VERIFIED, settings.MEDIA_RESTORE_VERIFIED,
                        settings.MEDIA_LEGACY_PRIVACY_VERIFIED))
    else:
        storage = {"BACKEND": "apps.common.media.storage.ProtectedFileSystemStorage",
                   "OPTIONS": {"location": str(folder / "media")}}
        override_settings(STORAGES={**settings.STORAGES,
                                   "private_media": storage, "public_media": storage,
                                   "default": storage}).enable()
        # Only the guarded, disposable DB. No production migration command.
        call_command("migrate", interactive=False, verbosity=0, stdout=io.StringIO())
        User = get_user_model()
        owner = User.objects.create_user(username="asgi-qa-owner", email="owner@example.invalid",
                                         password="synthetic-only", is_verified=True)
        other = User.objects.create_user(username="asgi-qa-other", email="other@example.invalid",
                                         password="synthetic-only", is_verified=True)
        from django.apps import apps
        from django.core.files.base import ContentFile
        from PIL import Image
        Profile = apps.get_model("user_profile", "UserProfile")
        profile, _ = Profile.objects.get_or_create(user=owner)
        KYC = apps.get_model("user_profile", "KYCSubmission")
        image = io.BytesIO()
        Image.new("RGB", (2, 2), "black").save(image, format="PNG")
        field = KYC._meta.get_field("document_front")
        from django.core.files.storage import storages
        name = storages["private_media"].save("synthetic/qa.png", ContentFile(image.getvalue()))
        record = KYC.objects.create(user_profile=profile, document_type="passport", document_front=name)
        assert field.model == KYC
        (folder / "fixture.json").write_text(json.dumps({
            "media": f"/files/user_profile.kycsubmission/document_front/{record.pk}/"}), encoding="utf-8")

        def session_login(request, who):
            # Test-only endpoint: CSRF middleware still governs every POST.
            if request.method != "POST":
                from django.middleware.csrf import get_token
                return HttpResponse(get_token(request))
            login(request, owner if who == "owner" else other,
                  backend="django.contrib.auth.backends.ModelBackend")
            request.session["qa_marker"] = who
            return HttpResponse("synthetic login")

        @login_required
        def protected(request):
            assert request.user.username == "asgi-qa-" + request.session["qa_marker"]
            return HttpResponse("synthetic authenticated")

        global urlpatterns
        urlpatterns = [path("qa/", ordinary), path("qa/slow/", slow),
                       path("qa/login/<str:who>/", session_login), path("qa/protected/", protected),
                       path("", include(original_urlconf))]
        settings.ROOT_URLCONF = __name__
        connection.close()  # Fixture-setup connection, before any ASGI requests.

    entry = importlib.import_module("deltacrown.asgi")
    from deltacrown.cutover_lockdown import CutoverLockdown
    root = entry.application
    router = root.application if isinstance(root, CutoverLockdown) else root
    assert isinstance(root, CutoverLockdown) == lockdown
    assert router.application_mapping["http"] is entry.django_asgi_app
    assert list(settings.MIDDLEWARE) == middleware
    # Test-process-only insertion at the prospective HTTP integration point.
    from apps.common.asgi_lifecycle import HTTPDisconnectDrain
    wrapper = HTTPDisconnectDrain(router.application_mapping["http"])
    router.application_mapping["http"] = wrapper
    assert router.application_mapping["websocket"] is entry.websocket_app
    return root, wrapper


def check_http(port, folder):
    """Real session/auth/CSRF and governed-file requests over loopback Daphne."""
    import http.client
    from http.cookies import SimpleCookie
    from urllib.parse import urlencode

    def request(path, jar, method="GET", data=None):
        client = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        headers = {"Cookie": "; ".join(f"{k}={v}" for k, v in jar.items())}
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        try:
            client.request(method, path, body=urlencode(data) if data is not None else None, headers=headers)
            response = client.getresponse()
            body = response.read()
            for key, value in response.getheaders():
                if key.lower() == "set-cookie":
                    cookie = SimpleCookie(value)
                    jar.update({k: v.value for k, v in cookie.items()})
            return response.status, body, response.getheader("Cache-Control")
        finally:
            client.close()

    anonymous, owner, other = {}, {}, {}
    assert request("/qa/protected/", anonymous)[0] == 302
    assert request("/qa/login/owner/", anonymous, "POST", {})[0] == 403
    for who, jar in (("owner", owner), ("other", other)):
        status, token, _ = request(f"/qa/login/{who}/", jar)
        assert status == 200
        assert request(f"/qa/login/{who}/", jar, "POST", {"csrfmiddlewaretoken": token.decode()})[0] == 200
        assert request("/qa/protected/", jar)[0] == 200
    assert owner["sessionid"] != other["sessionid"]
    assert request("/qa/protected/", {"sessionid": "synthetic-invalid-session"})[0] == 302
    media = json.loads((folder / "fixture.json").read_text(encoding="utf-8"))["media"]
    assert request(media, anonymous)[0] == 404
    assert request(media, other)[0] == 404
    status, body, cache = request(media, owner)
    assert status == 200 and body.startswith(b"\x89PNG\r\n\x1a\n") and cache == "private, no-store"
    assert request(media, anonymous)[0] == 404  # No personalized response leaked after owner read.
    print("REAL_ASGI_HTTP sessions/auth/CSRF/private-media owner+denial PASS", flush=True)
