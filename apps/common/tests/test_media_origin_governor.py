"""OL-10: bounded private-origin reads, conditional artwork requests and the ASGI liveness fast path.

Synthetic only: no credentials, no network, no database.
"""
import threading
import time
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from asgiref.sync import async_to_sync
from django.http import HttpResponse
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from apps.common.media import origin, views
from apps.common.media.storage import ProtectedS3Storage
from deltacrown.fast_health import FastHealth


class Tracker:
    def __init__(self):
        self.lock, self.now, self.peak = threading.Lock(), 0, 0

    def opened(self):
        with self.lock:
            self.now += 1
            self.peak = max(self.peak, self.now)

    def closed(self):
        with self.lock:
            self.now -= 1


class Body:
    def __init__(self, size, delay=0.0, tracker=None):
        self.stream = BytesIO(b"\x89PNG\r\n\x1a\n" + b"x" * size)
        self.delay, self.tracker, self.closed = delay, tracker, False
        if tracker:
            tracker.opened()

    def read(self, n=-1):
        time.sleep(self.delay)
        return self.stream.read(n)

    def close(self):
        if not self.closed and self.tracker:
            self.tracker.closed()
        self.closed = True


def storage():
    return ProtectedS3Storage(bucket_name="synthetic", access_key="x", secret_key="x", region_name="r",
                              endpoint_url="https://example.invalid")


async def drain(response):
    return b"".join([c async for c in response.streaming_content])


def exhaust():
    """Take every origin slot (short wait), return the leases."""
    with patch.object(origin, "WAIT_SECONDS", 0.05):
        return [origin.acquire() for _ in range(origin.SLOTS)]


class OriginGovernorTests(SimpleTestCase):
    def test_budget_is_bounded_and_a_double_release_never_adds_a_slot(self):
        leases = exhaust()
        self.assertTrue(all(leases))
        with patch.object(origin, "WAIT_SECONDS", 0.05):
            self.assertIsNone(origin.acquire())  # exhausted: shed instead of queueing forever
            leases[0].release()
            leases[0].release()
            again = origin.acquire()
            self.assertTrue(again)
            self.assertIsNone(origin.acquire())
        for lease in leases[1:] + [again]:
            lease.release()
        self.assertTrue(all(exhaust()))  # nothing leaked

    def test_exhausted_budget_returns_fast_503_without_touching_the_origin(self):
        blob = SimpleNamespace(storage=storage(), name="cards/7.png")
        with patch.object(origin, "acquire", return_value=None), patch.object(blob.storage, "open_stream_object") as get:
            response = views.serve_blob(blob)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response["Retry-After"], "2")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        get.assert_not_called()

    def test_slot_is_released_after_errors_and_after_a_response_that_is_closed_unread(self):
        blob = SimpleNamespace(storage=storage(), name="cards/7.png")
        for _ in range(origin.SLOTS + 2):
            with patch.object(blob.storage, "open_stream_object", side_effect=RuntimeError("boom")):
                self.assertEqual(views.serve_blob(blob).status_code, 503)
        for _ in range(origin.SLOTS + 2):
            body = Body(1000)
            with patch.object(blob.storage, "open_stream_object", return_value={"Body": body, "ContentLength": 1008}):
                response = views.serve_blob(blob)
            self.assertEqual(response.status_code, 200)
            response.close()  # never iterated (HEAD, or client gone): the lease must still come back
            self.assertTrue(body.closed)
        leases = exhaust()
        self.assertTrue(all(leases))
        for lease in leases:
            lease.release()

    def test_response_dropped_by_a_disconnected_client_still_frees_body_and_slot(self):
        import gc
        blob = SimpleNamespace(storage=storage(), name="cards/7.png")
        for _ in range(origin.SLOTS + 2):
            body = Body(1000)
            with patch.object(blob.storage, "open_stream_object", return_value={"Body": body, "ContentLength": 1008}):
                response = views.serve_blob(blob)
            self.assertEqual(response.status_code, 200)
            del response  # request task cancelled: nobody iterates or closes it
            gc.collect()
            self.assertTrue(body.closed)
        leases = exhaust()
        self.assertTrue(all(leases))
        for lease in leases:
            lease.release()

    def test_many_concurrent_requests_never_exceed_the_origin_budget(self):
        tracker, results = Tracker(), []
        blob = SimpleNamespace(storage=storage(), name="cards/7.png")
        size = 300 * 1024

        def open_object(name):
            return {"Body": Body(size, delay=0.002, tracker=tracker), "ContentLength": size + 8}

        def request():
            response = views.serve_blob(blob)
            if response.status_code == 200:
                results.append(len(async_to_sync(drain)(response)))
                response.close()
            else:
                results.append(response.status_code)

        with patch.object(origin, "WAIT_SECONDS", 20), patch.object(blob.storage, "open_stream_object", side_effect=open_object):
            threads = [threading.Thread(target=request) for _ in range(20)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(60)
        self.assertEqual(results, [size + 8] * 20)  # all served (queued behind the budget), none lost
        self.assertLessEqual(tracker.peak, origin.SLOTS)
        self.assertEqual(tracker.now, 0)  # every body closed


class OriginResilienceTests(SimpleTestCase):
    """OL-12: production lost all media when a burst of cancelled requests left every lease unreleased."""

    def test_abandoned_leases_are_reclaimed_without_the_garbage_collector(self):
        held = exhaust()  # references kept: neither released nor collectable, like a response stuck in a cancelled task
        self.assertTrue(all(held))
        with patch.object(origin, "WAIT_SECONDS", 0.05):
            self.assertIsNone(origin.acquire())
        with patch.object(origin, "MAX_HOLD_SECONDS", 0.05), patch.object(origin, "WAIT_SECONDS", 2):
            time.sleep(0.1)
            fresh = [origin.acquire() for _ in range(origin.SLOTS)]
        self.assertTrue(all(fresh))  # the budget healed itself
        for lease in held:
            lease.release()  # the original holders finally finish: must not hand out extra slots
        with patch.object(origin, "WAIT_SECONDS", 0.05):
            self.assertIsNone(origin.acquire())
        for lease in fresh:
            lease.release()
        self.assertTrue(all(exhaust()))

    def test_small_derivative_is_read_whole_released_at_once_and_cached(self):
        origin._cache.clear()
        blob_storage = storage()
        payload = b"RIFF" + b"y" * 5000
        body = Body(5000)
        body.stream = BytesIO(payload)
        with patch.object(blob_storage, "open_stream_object", return_value={"Body": body, "ContentLength": len(payload)}) as get:
            first = views.serve_derivative(blob_storage, "derivatives/v1/a.webp")
            with patch.object(origin, "WAIT_SECONDS", 0.05):  # every small slot is free although `first` is unread
                leases = [origin.acquire(small=True) for _ in range(origin.SMALL_SLOTS)]
                self.assertTrue(all(leases))
                self.assertIsNone(origin.acquire(small=True))
            for lease in leases:
                lease.release()
            second = views.serve_derivative(blob_storage, "derivatives/v1/a.webp")
        self.assertEqual((first.content, second.content), (payload, payload))
        get.assert_called_once()

    def test_cache_is_bounded_and_skips_large_entries(self):
        origin._cache.clear()
        with patch.object(origin, "CACHE_BYTES", 10_000):
            for i in range(10):
                origin.cache_put(f"k{i}", b"z" * 3000)
            origin.cache_put("huge", b"z" * (origin.CACHE_ENTRY_MAX + 1))
        self.assertEqual(sum(len(v) for v in origin._cache.values()), 9000)
        self.assertIsNone(origin.cache_get("k0"))
        self.assertIsNotNone(origin.cache_get("k9"))
        self.assertIsNone(origin.cache_get("huge"))
        origin._cache.clear()
        origin._cache_size = 0


class ConditionalArtworkTests(SimpleTestCase):
    def call(self, label, field_name, name="a.png", **headers):
        model = Mock()
        model._meta.get_field.return_value = Mock(spec=views.MediaImageField)
        model._meta.label_lower = label
        blob = Mock()
        blob.name = name
        obj = SimpleNamespace(pk=3, **{field_name: blob})
        served = HttpResponse(b"art", content_type="image/png")
        served["Cache-Control"] = "private, no-store"
        with patch.object(views.apps, "get_model", return_value=model), patch.object(
                views, "get_object_or_404", return_value=obj), patch.object(views, "can_download", return_value=True), patch.object(
                views, "serve_blob", return_value=served) as serve, patch.object(views, "enabled", return_value=True):
            request = APIRequestFactory().get("/files/", **headers)
            return views.download.cls.as_view()(request, label, field_name, 3), serve

    def test_game_artwork_sends_an_etag_and_a_matching_request_gets_304_without_bytes(self):
        first, _ = self.call("games.game", "icon")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first["Cache-Control"], "private, max-age=900, must-revalidate")
        etag = first["ETag"]
        second, serve = self.call("games.game", "icon", HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(second.status_code, 304)
        serve.assert_not_called()
        self.assertEqual(second["Cache-Control"], "private, max-age=900, must-revalidate")
        self.assertEqual(second["Content-Security-Policy"], "default-src 'none'; sandbox")
        changed, serve = self.call("games.game", "icon", name="b.png", HTTP_IF_NONE_MATCH=etag)  # re-upload
        self.assertEqual(changed.status_code, 200)
        serve.assert_called_once()

    def test_visibility_dependent_artwork_revalidates_and_other_media_stays_no_store(self):
        banner, _ = self.call("tournaments.tournament", "banner_image")
        self.assertEqual(banner["Cache-Control"], "private, no-cache")
        self.assertEqual(
            self.call("tournaments.tournament", "banner_image", HTTP_IF_NONE_MATCH=banner["ETag"])[0].status_code, 304)
        for label, field_name in (("user_profile.userprofile", "avatar"), ("tournaments.paymentverification", "proof_image")):
            response, _ = self.call(label, field_name, HTTP_IF_NONE_MATCH='"o-anything"')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Cache-Control"], "private, no-store")
            self.assertFalse(response.has_header("ETag"))


class FastHealthTests(SimpleTestCase):
    def run_scope(self, **scope):
        sent, inner = [], Mock()

        async def app(s, receive, send):
            inner(s["path"])

        async def send(message):
            sent.append(message)

        async def go():
            await FastHealth(app)({"type": "http", "method": "GET", **scope}, None, send)

        async_to_sync(go)()
        return sent, inner

    def test_healthz_is_answered_without_entering_the_application(self):
        sent, inner = self.run_scope(path="/healthz/")
        inner.assert_not_called()
        self.assertEqual(sent[0]["status"], 200)
        self.assertEqual(sent[1]["body"], b'{"status": "ok"}')
        sent, _ = self.run_scope(path="/healthz/", method="HEAD")
        self.assertEqual(sent[1]["body"], b"")

    def test_everything_else_passes_through(self):
        for scope in ({"path": "/teams/"}, {"path": "/healthz/", "method": "POST"}, {"path": "/healthz"}):
            sent, inner = self.run_scope(**scope)
            inner.assert_called_once()
            self.assertEqual(sent, [])
