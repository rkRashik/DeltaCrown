"""Disposable fixtures for the real entry-point check; never a runtime module."""
import importlib
import io
import json
import os


def migrate_fixture(stage, folder=None, require_prepared=False):
    stage("migrations")
    if folder is None:
        from django.core.management import call_command
        call_command("migrate", interactive=False, verbosity=0, stdout=io.StringIO())
    else:
        from scripts.asgi_migration_qa import migrate
        migrate(folder, stage, require_prepared=require_prepared)
    stage("migrations", "completed")


def arrange(folder, slow, ordinary, lockdown, stage):
    """Called only after the cancellation harness's local DB/socket guards."""
    from django.conf import settings
    from django.contrib.auth import authenticate, get_user_model, login
    from django.contrib.auth.decorators import login_required
    from django.db import connection
    from django.http import HttpResponse
    from django.urls import include, path
    from django.test import override_settings
    from deltacrown import settings as base_settings

    # Restore the middleware omitted by media QA, in exactly its original order.
    # Its network proxy is inactive in local media mode; sockets remain guarded.
    settings.MIDDLEWARE = list(base_settings.MIDDLEWARE)
    original_urlconf = base_settings.ROOT_URLCONF
    assert settings.DEBUG is False and settings.OWNLOBBY_MEDIA_MODE == "local", "Requires guarded local media QA"
    assert settings.SESSION_ENGINE == "django.contrib.sessions.backends.cached_db", "Preserve the project's cached_db session backend"
    assert settings.CACHES["default"]["BACKEND"] == "django.core.cache.backends.locmem.LocMemCache", "QA cache must remain local"
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
        prepared = os.environ.get("QA_REQUIRE_PREPARED") == "1"
        migrate_fixture(stage, folder if prepared else None, require_prepared=prepared)
        stage("synthetic_users")
        User = get_user_model()
        owner = User.objects.create_user(username="asgi-qa-owner", email="owner@example.invalid",
                                         password="synthetic-only", is_verified=True)
        other = User.objects.create_user(username="asgi-qa-other", email="other@example.invalid",
                                         password="synthetic-only", is_verified=True)
        stage("synthetic_users", "completed")
        stage("synthetic_media")
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
        stage("synthetic_media", "completed")

        auth_events = []

        def record_auth(item):
            if len(auth_events) < 40:
                auth_events.append(item)
            temporary = folder / "auth_events.tmp"
            temporary.write_text(json.dumps(auth_events), encoding="utf-8")
            temporary.replace(folder / "auth_events.json")

        def observe_auth(request, **details):
            from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
            from django.contrib.sessions.models import Session
            # This record lookup is restricted to the current synthetic session.
            key = request.session.session_key
            row = Session.objects.filter(session_key=key).first() if key else None
            stored = row.get_decoded() if row else {}
            marker = request.session.get("qa_marker")
            expected = owner if marker == "owner" else other if marker == "other" else None
            item = dict(cookie_received=bool(request.COOKIES.get(settings.SESSION_COOKIE_NAME)),
                        session_key_present=bool(key), record_exists=row is not None,
                        stored_auth_fields=all(k in stored for k in (SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY)),
                        stored_marker_present="qa_marker" in stored,
                        stored_marker_matches=bool(expected and stored.get("qa_marker") == marker),
                        stored_user_matches=bool(expected and stored.get(SESSION_KEY) == str(expected.pk)),
                        backend_configured=stored.get(BACKEND_SESSION_KEY) in settings.AUTHENTICATION_BACKENDS,
                        authenticated=bool(request.user.is_authenticated),
                        request_marker_matches=bool(expected),
                        request_user_matches=bool(expected and request.user.pk == expected.pk),
                        route_resolved=request.resolver_match is not None, **details)
            record_auth(item)

        def request_error(sender, request, **kwargs):
            import sys
            if request.path.startswith("/qa/"):
                # No exception message, response body or session contents.
                error = sys.exc_info()[1]
                record_auth(dict(phase="request_exception", exception_type=type(error).__name__,
                                 route_resolved=request.resolver_match is not None))

        from django.core.signals import got_request_exception
        got_request_exception.connect(request_error, weak=False)

        def session_login(request, who):
            # Test-only endpoint: CSRF middleware still governs every POST.
            if request.method != "POST":
                from django.middleware.csrf import get_token
                return HttpResponse(get_token(request))
            assert who in {"owner", "other", "legacy"}
            marker = "owner" if who == "legacy" else who
            user = authenticate(request, username="asgi-qa-" + marker, password="synthetic-only")
            assert user is not None and user.backend in settings.AUTHENTICATION_BACKENDS
            if who == "legacy":
                # Exact old-fixture negative control, after genuine authentication.
                old_backend = "django.contrib.auth.backends.ModelBackend"
                assert old_backend not in settings.AUTHENTICATION_BACKENDS
                login(request, user, backend=old_backend)
            else:
                login(request, user)
            request.session["qa_marker"] = marker
            observe_auth(request, phase="login_before_response", credential_auth_succeeded=True,
                         legacy_control=who == "legacy")
            return HttpResponse("synthetic login")

        @login_required
        def protected(request):
            try:
                assert request.user.username == "asgi-qa-" + request.session["qa_marker"]
                observe_auth(request, phase="protected_view", protected_view_entered=True)
                return HttpResponse("synthetic authenticated")
            except Exception as error:
                observe_auth(request, phase="protected_view_exception", exception_type=type(error).__name__)
                raise

        def observed_protected(request):
            observe_auth(request, phase="protected_boundary", protected_handler_entered=True)
            return protected(request)  # Keep the original login_required boundary.

        global urlpatterns
        urlpatterns = [path("qa/", ordinary), path("qa/slow/", slow),
                       path("qa/login/<str:who>/", session_login), path("qa/protected/", observed_protected),
                       path("", include(original_urlconf))]
        settings.ROOT_URLCONF = __name__
        connection.close()  # Fixture-setup connection, before any ASGI requests.

    stage("real_asgi_import")
    entry = importlib.import_module("deltacrown.asgi")
    stage("real_asgi_import", "completed")
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
    from urllib.parse import urlencode, urlsplit

    emitted = 0

    def request(path, jar, method="GET", data=None):
        nonlocal emitted
        client = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        previous = jar.get("sessionid")
        session_set = False
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
                    session_set = session_set or "sessionid" in cookie
                    jar.update({k: v.value for k, v in cookie.items()})
            if path.startswith("/qa/"):
                try:
                    events = json.loads((folder / "auth_events.json").read_text(encoding="utf-8"))
                except FileNotFoundError:
                    events = []
                new = events[emitted:]
                emitted = len(events)
                print("REAL_ASGI_AUTH " + json.dumps(dict(path=path, method=method, status=response.status,
                      redirect_path=urlsplit(response.getheader("Location") or "").path,
                      cookie_before=bool(previous), cookie_forwarded=bool(previous),
                      cookie_set=session_set, cookie_after=bool(jar.get("sessionid")),
                      cookie_changed=previous != jar.get("sessionid"), server=new)), flush=True)
            return response.status, body, response.getheader("Cache-Control")
        finally:
            client.close()

    anonymous, owner, other = {}, {}, {}
    assert request("/qa/protected/", anonymous)[0] == 302
    assert request("/qa/login/owner/", anonymous, "POST", {})[0] == 403
    legacy = {}
    status, token, _ = request("/qa/login/legacy/", legacy)
    assert status == 200
    assert request("/qa/login/legacy/", legacy, "POST", {"csrfmiddlewaretoken": token.decode()})[0] == 200
    assert request("/qa/protected/", legacy)[0] == 302
    legacy_facts = json.loads((folder / "auth_events.json").read_text(encoding="utf-8"))[-1]
    assert all(legacy_facts[k] for k in ("cookie_received", "record_exists", "stored_auth_fields",
                                       "stored_marker_matches", "stored_user_matches"))
    assert not legacy_facts["backend_configured"] and not legacy_facts["authenticated"]
    for who, jar in (("owner", owner), ("other", other)):
        status, token, _ = request(f"/qa/login/{who}/", jar)
        assert status == 200
        assert request(f"/qa/login/{who}/", jar, "POST", {"csrfmiddlewaretoken": token.decode()})[0] == 200
        assert request("/qa/protected/", jar)[0] == 200
        facts = json.loads((folder / "auth_events.json").read_text(encoding="utf-8"))[-1]
        assert all(facts[k] for k in ("cookie_received", "record_exists", "stored_auth_fields",
                                     "stored_marker_matches", "stored_user_matches", "backend_configured",
                                     "authenticated", "request_user_matches", "protected_view_entered"))
    assert owner["sessionid"] != other["sessionid"]
    assert request("/qa/protected/", {"sessionid": "synthetic-invalid-session"})[0] == 302
    media = json.loads((folder / "fixture.json").read_text(encoding="utf-8"))["media"]
    assert request(media, anonymous)[0] == 404
    assert request(media, other)[0] == 404
    status, body, cache = request(media, owner)
    assert status == 200 and body.startswith(b"\x89PNG\r\n\x1a\n") and cache == "private, no-store"
    assert request(media, anonymous)[0] == 404  # No personalized response leaked after owner read.
    print("REAL_ASGI_HTTP sessions/auth/CSRF/private-media owner+denial PASS", flush=True)
