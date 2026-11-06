"""Finite, framework-independent HTTP lifecycle contracts; no DB or services."""
import asyncio
import unittest

from apps.common.asgi_lifecycle import HTTPDisconnectDrain


class HTTPDisconnectDrainTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.before = set(asyncio.all_tasks())
        self.tasks = []
        self.releases = []
        self.errors = []
        self.loop = asyncio.get_running_loop()
        self.old_handler = self.loop.get_exception_handler()
        self.loop.set_exception_handler(lambda loop, context: self.errors.append(context))

    async def asyncTearDown(self):
        for release in self.releases:
            release.set()
        for task in self.tasks:
            if not task.done():
                task.cancel()
        await asyncio.wait_for(asyncio.gather(*self.tasks, return_exceptions=True), 1)
        await asyncio.sleep(0)
        self.loop.set_exception_handler(self.old_handler)
        self.assertFalse(set(asyncio.all_tasks()) - self.before - {asyncio.current_task()})
        self.assertFalse(self.errors, "Unhandled task/receive exception")

    def spawn(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.tasks.append(task)
        return task

    def release(self):
        event = asyncio.Event()
        self.releases.append(event)
        return event

    async def send(self, message):
        pass

    async def test_body_and_real_disconnect_are_forwarded(self):
        messages = [{"type": "http.request", "body": b"fixture", "more_body": True},
                    {"type": "http.disconnect"}]
        queue = asyncio.Queue()
        for message in messages:
            queue.put_nowait(message)

        async def app(scope, receive, send):
            self.assertEqual([await receive(), await receive()], messages)
            return "done"

        wrapper = HTTPDisconnectDrain(app)
        self.assertEqual(await wrapper({"type": "http"}, queue.get, self.send), "done")
        await asyncio.sleep(0)
        self.assertEqual((wrapper.active_count, wrapper.occupied_count), (0, 0))

    async def test_repeated_outer_cancellation_drains_before_propagating(self):
        started, cleaning, release = asyncio.Event(), asyncio.Event(), self.release()

        async def receive():
            started.set()
            await asyncio.Event().wait()

        async def app(scope, receive, send):
            self.assertEqual(await receive(), {"type": "http.disconnect"})
            cleaning.set()
            await release.wait()

        wrapper = HTTPDisconnectDrain(app, capacity=1)
        outer = self.spawn(wrapper({"type": "http"}, receive, self.send))
        await asyncio.wait_for(started.wait(), 1)
        outer.cancel()
        await asyncio.wait_for(cleaning.wait(), 1)
        for _ in range(3):
            outer.cancel()
            await asyncio.sleep(0)
            self.assertFalse(outer.done())
            self.assertEqual((wrapper.active_count, wrapper.occupied_count), (1, 1))
        release.set()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(outer, 1)
        self.assertEqual((wrapper.active_count, wrapper.occupied_count), (0, 0))

    async def test_admission_is_atomic_and_held_through_stream_and_cleanup(self):
        streaming, release_stream, cleaning, release_cleanup = (asyncio.Event(), self.release(),
                                                               asyncio.Event(), self.release())
        starts, reads, replies = [], [], []

        async def receive():
            reads.append(True)
            return {"type": "http.request", "body": b""}

        async def send(message):
            replies.append(message)

        async def app(scope, receive, send):
            starts.append(True)
            await receive()
            await send({"type": "http.response.body", "body": b"chunk", "more_body": True})
            if len(starts) == 2:
                streaming.set()
            await release_stream.wait()
            cleaning.set()
            await release_cleanup.wait()

        wrapper = HTTPDisconnectDrain(app, capacity=2)  # Synthetic capacity only.
        admitted = [self.spawn(wrapper({"type": "http"}, receive, send)) for _ in range(2)]
        await asyncio.wait_for(streaming.wait(), 1)
        await wrapper({"type": "http"}, receive, send)
        self.assertEqual((len(starts), len(reads), wrapper.occupied_count), (2, 2, 2))
        rejection = next(m for m in replies if m.get("status") == 503)
        self.assertIn((b"cache-control", b"no-store"), rejection["headers"])
        admitted[0].cancel()
        release_stream.set()
        await asyncio.wait_for(cleaning.wait(), 1)
        self.assertEqual(wrapper.occupied_count, 2)
        release_cleanup.set()
        results = await asyncio.wait_for(asyncio.gather(*admitted, return_exceptions=True), 1)
        self.assertIsInstance(results[0], asyncio.CancelledError)
        self.assertEqual((wrapper.active_count, wrapper.occupied_count), (0, 0))

    async def test_child_errors_are_retrieved_including_after_outer_cancel(self):
        started, release = asyncio.Event(), self.release()

        async def receive():
            return {"type": "http.request"}

        async def app(scope, receive, send):
            started.set()
            await release.wait()
            raise ValueError("synthetic failure")

        wrapper = HTTPDisconnectDrain(app)
        outer = self.spawn(wrapper({"type": "http"}, receive, self.send))
        await asyncio.wait_for(started.wait(), 1)
        outer.cancel()
        await asyncio.sleep(0)
        release.set()
        with self.assertRaises(asyncio.CancelledError) as caught:
            await asyncio.wait_for(outer, 1)
        self.assertIsInstance(caught.exception.__cause__, ValueError)
        with self.assertRaisesRegex(ValueError, "synthetic failure"):
            await wrapper({"type": "http"}, receive, self.send)
        self.assertEqual((wrapper.active_count, wrapper.occupied_count), (0, 0))

    async def test_receive_errors_and_concurrent_receive_do_not_leave_helpers(self):
        async def failed_receive():
            raise LookupError("synthetic receive failure")

        async def app(scope, receive, send):
            await receive()

        wrapper = HTTPDisconnectDrain(app)
        with self.assertRaises(LookupError):
            await wrapper({"type": "http"}, failed_receive, self.send)
        started = asyncio.Event()

        async def blocked_receive():
            started.set()
            await asyncio.Event().wait()

        async def concurrent(scope, receive, send):
            first = self.spawn(receive())
            try:
                await asyncio.wait_for(started.wait(), 1)
                with self.assertRaisesRegex(RuntimeError, "Concurrent HTTP receive"):
                    await receive()
            finally:
                first.cancel()
                await asyncio.gather(first, return_exceptions=True)

        wrapper = HTTPDisconnectDrain(concurrent)
        await wrapper({"type": "http"}, blocked_receive, self.send)
        self.assertEqual((wrapper.active_count, wrapper.occupied_count), (0, 0))

    async def test_self_cancellation_and_http_only_validation(self):
        async def app(scope, receive, send):
            raise asyncio.CancelledError

        wrapper = HTTPDisconnectDrain(app)
        with self.assertRaises(asyncio.CancelledError):
            await wrapper({"type": "http"}, None, self.send)
        self.assertEqual((wrapper.active_count, wrapper.occupied_count), (0, 0))
        with self.assertRaises(ValueError):
            await wrapper({"type": "websocket"}, None, self.send)
        for value in (True, 0, -1, 1.5):
            with self.assertRaises(ValueError):
                HTTPDisconnectDrain(app, capacity=value)
