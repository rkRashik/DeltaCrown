"""No network, provider, production DB or storage access: ASGI lockdown regressions."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from deltacrown.cutover_lockdown import CutoverLockdown, lockdown_required


class LockdownDecisionTests(unittest.TestCase):
    def cfg(self, storage=False, restore=False, privacy=False, mode="hybrid"):
        return SimpleNamespace(
            OWNLOBBY_MEDIA_MODE=mode,
            MEDIA_STORAGE_VERIFIED=storage,
            MEDIA_RESTORE_VERIFIED=restore,
            MEDIA_LEGACY_PRIVACY_VERIFIED=privacy,
        )

    def test_hybrid_is_locked_for_any_missing_proof(self):
        with patch.dict(os.environ, {"OWNLOBBY_CUTOVER_LOCKDOWN": "0"}):
            for good in ((False, True, True), (True, False, True),
                         (True, True, False), (False, False, False)):
                self.assertTrue(lockdown_required(self.cfg(*good)))

    def test_only_all_true_unlocked_without_explicit_lock(self):
        with patch.dict(os.environ, {"OWNLOBBY_CUTOVER_LOCKDOWN": "0"}):
            self.assertFalse(lockdown_required(self.cfg(True, True, True)))
            self.assertFalse(lockdown_required(self.cfg(mode="legacy")))

    def test_explicit_lock_always_wins_even_with_all_proofs(self):
        with patch.dict(os.environ, {"OWNLOBBY_CUTOVER_LOCKDOWN": "1"}):
            self.assertTrue(lockdown_required(self.cfg(True, True, True)))
            self.assertTrue(lockdown_required(self.cfg(mode="legacy")))


class ASGILockdownTests(unittest.IsolatedAsyncioTestCase):
    async def invoke(self, scope):
        app_calls = []
        output = []

        async def upstream(_scope, _receive, send):
            app_calls.append(_scope)
            if _scope["type"] == "http":
                await send({"type": "http.response.start", "status": 200,
                            "headers": []})
                await send({"type": "http.response.body", "body": b"ok"})

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(event):
            output.append(event)

        await CutoverLockdown(upstream)(scope, receive, send)
        return app_calls, output

    async def test_http_get_and_post_are_rejected_before_application(self):
        for method in ("GET", "POST", "OPTIONS", "PUT", "DELETE"):
            calls, sent = await self.invoke({"type": "http",
                    "path": "/private-media/payment-proof", "method": method})
            self.assertEqual(calls, [])
            self.assertEqual(sent[0]["status"], 503)
            self.assertIn((b"cache-control", b"no-store"), sent[0]["headers"])
            self.assertIn((b"retry-after", b"60"), sent[0]["headers"])

    async def test_health_route_only_exemption(self):
        calls, sent = await self.invoke({"type": "http",
                                         "path": "/healthz/", "method": "GET"})
        self.assertEqual(len(calls), 1)
        self.assertEqual(sent[0]["status"], 200)
        calls, sent = await self.invoke({"type": "http",
                                         "path": "/readiness/", "method": "GET"})
        self.assertEqual(calls, [])
        self.assertEqual(sent[0]["status"], 503)

    async def test_head_cannot_access_media(self):
        calls, sent = await self.invoke({"type": "http",
                                        "path": "/media/secret", "method": "HEAD"})
        self.assertEqual(calls, [])
        self.assertEqual(sent[0]["status"], 503)
        self.assertEqual(sent[-1]["body"], b"")

    async def test_websockets_denied_before_auth(self):
        calls, sent = await self.invoke({"type": "websocket", "path": "/ws/matches/"})
        self.assertEqual(calls, [])
        self.assertEqual(sent, [{"type": "websocket.close", "code": 4403}])
