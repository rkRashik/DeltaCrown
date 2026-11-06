"""Small synthetic capacity/observation contracts; no providers or database."""
import asyncio
import unittest

from apps.common.asgi_lifecycle import LifecycleConfig, LifecycleState


class AdmissionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.before = set(asyncio.all_tasks())
        self.tasks, self.releases, self.protocols = [], [], []
        self.state = LifecycleState(LifecycleConfig(1, .1, .2, 1), websocket_capacity=1)

    async def asyncTearDown(self):
        for event in self.releases:
            event.set()
        for future in self.protocols:
            if not future.done():
                future.set_result(None)
        for task in self.tasks:
            if not task.done():
                task.cancel()
        await asyncio.wait_for(asyncio.gather(*self.tasks, return_exceptions=True), 1)
        await asyncio.sleep(0)
        self.assertFalse(set(asyncio.all_tasks())-self.before-{asyncio.current_task()})
        self.assertFalse(self.state._websocket_owners)
        self.assertEqual(self.state.http.occupied_count, 0)

    def event(self):
        event = asyncio.Event()
        self.releases.append(event)
        return event

    def spawn(self, coroutine, *, websocket=False):
        task = asyncio.create_task(coroutine)
        self.tasks.append(task)
        if websocket:
            closed = asyncio.get_running_loop().create_future()
            self.protocols.append(closed)
            self.state._websocket_closures[task] = closed
        return task

    async def send(self, message):
        pass

    async def forbidden(self):
        self.fail("Rejected work read receive")

    def snapshot(self, **kwargs):
        return self.state.observe(stall_after=.2, lag_threshold=.05, loop_lag=0, **kwargs)

    async def test_pending_accepted_and_protocol_ownership_are_independent_of_http(self):
        http_started, ws_started, accepted = asyncio.Event(), asyncio.Event(), asyncio.Event()
        release_http, accept_ws, release_ws = self.event(), self.event(), self.event()

        async def http(scope, receive, send):
            http_started.set()
            await release_http.wait()

        async def socket(scope, receive, send):
            ws_started.set()
            await accept_ws.wait()
            await send({"type":"websocket.accept"})
            accepted.set()
            await release_ws.wait()

        h, w = self.state.attach(http, socket)
        one = self.spawn(h({"type":"http"}, self.forbidden, self.send))
        await asyncio.wait_for(http_started.wait(), 1)
        two = self.spawn(w({"type":"websocket"}, self.forbidden, self.send), websocket=True)
        await asyncio.wait_for(ws_started.wait(), 1)
        self.assertEqual((self.snapshot()["http_slots"], self.snapshot()["ws_pending"]), (1, 1))
        replies = []
        async def collect(message):
            replies.append(message)
        await asyncio.gather(h({"type":"http"}, self.forbidden, collect),
                             w({"type":"websocket"}, self.forbidden, collect))
        self.assertEqual((self.snapshot()["http_rejections"], self.snapshot()["ws_rejections"]), (1, 1))
        accept_ws.set()
        await asyncio.wait_for(accepted.wait(), 1)
        self.assertEqual((self.snapshot()["ws_pending"], self.snapshot()["ws_accepted"]), (0, 1))
        session = next(iter(self.state.websockets))
        await session.close()
        self.assertEqual(self.snapshot()["ws_slots"], 1)
        release_http.set()
        await asyncio.wait_for(one, 1)
        self.assertEqual((self.snapshot()["http_slots"], self.snapshot()["ws_slots"]), (0, 1))
        await h({"type":"http"}, self.forbidden, self.send)
        self.assertEqual(self.snapshot()["http_completed"], 2)  # Full WS pool does not reject HTTP.
        release_ws.set()
        await asyncio.wait_for(two, 1)
        self.assertEqual(self.snapshot()["ws_slots"], 1)  # App exit is not protocol termination.
        self.protocols[0].set_result(None)
        await asyncio.sleep(0)
        self.assertEqual(self.snapshot()["ws_slots"], 0)
        self.assertEqual((self.state.ws_pending_peak, self.state.ws_accepted_peak, self.state.ws_completed), (1,1,1))

    async def test_protocol_close_does_not_release_slow_application_cleanup(self):
        started, release = asyncio.Event(), self.event()
        async def app(scope, receive, send):
            await send({"type":"websocket.accept"})
            started.set()
            await release.wait()
        _, w = self.state.attach(app, app)
        task = self.spawn(w({"type":"websocket"}, self.forbidden, self.send), websocket=True)
        await asyncio.wait_for(started.wait(), 1)
        self.protocols[0].set_result(None)
        await asyncio.sleep(0)
        self.assertEqual(self.snapshot()["ws_slots"], 1)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        self.assertEqual((self.snapshot()["ws_slots"], self.state.ws_failed), (0, 1))

    async def test_quiescing_and_failed_handshakes_do_not_leak_slots(self):
        async def failed(scope, receive, send):
            raise ValueError("synthetic handshake failure")
        h, w = self.state.attach(failed, failed)
        task = self.spawn(w({"type":"websocket"}, self.forbidden, self.send), websocket=True)
        with self.assertRaises(ValueError):
            await task
        self.assertEqual(self.snapshot()["ws_pending"], 1)
        self.protocols[0].set_result(None)
        await asyncio.sleep(0)
        self.state.phase = "QUIESCING"
        await asyncio.gather(h({"type":"http"}, self.forbidden, self.send),
                             w({"type":"websocket"}, self.forbidden, self.send))
        sample = self.snapshot()
        self.assertEqual((sample["http_slots"], sample["ws_slots"]), (0, 0))
        self.assertEqual((sample["http_quiescing_rejections"], sample["ws_quiescing_rejections"]), (1,1))
        self.assertEqual(sample["signal"], "QUIESCING")

    async def test_observation_distinguishes_saturation_progress_lag_and_quiescing(self):
        started, release = asyncio.Event(), self.event()
        async def app(scope, receive, send):
            started.set()
            await release.wait()
        h, _ = self.state.attach(app, app)
        task = self.spawn(h({"type":"http"}, self.forbidden, self.send))
        await asyncio.wait_for(started.wait(), 1)
        base = max(h.full_since, h.last_progress)
        self.assertEqual(self.snapshot(now=base+.1)["signal"], "CAPACITY_EXHAUSTED")
        self.assertEqual(self.snapshot(now=base+.3)["signal"], "SATURATED_NO_OBSERVED_PROGRESS")
        sample = self.state.observe(stall_after=.2, lag_threshold=.05, loop_lag=.1, now=base+.3)
        self.assertEqual(sample["signal"], "LOOP_LAG_OBSERVED")
        self.assertEqual(self.state.phase, "RUNNING")  # Observation cannot restart or quiesce.
        self.state.phase = "QUIESCING"
        self.assertEqual(self.snapshot(now=base+.3)["signal"], "QUIESCING")
        release.set()
        await asyncio.wait_for(task, 1)
        self.assertEqual(self.snapshot()["http_peak"], 1)

    async def test_retained_http_cleanup_and_repeated_cancel_keep_capacity(self):
        started, cleaning, release = asyncio.Event(), asyncio.Event(), self.event()
        async def receive():
            started.set()
            await asyncio.Event().wait()
        async def app(scope, receive, send):
            await receive()
            cleaning.set()
            await release.wait()
        h, _ = self.state.attach(app, app)
        task = self.spawn(h({"type":"http"}, receive, self.send))
        await asyncio.wait_for(started.wait(), 1)
        task.cancel()
        await asyncio.wait_for(cleaning.wait(), 1)
        for _ in range(3):
            task.cancel()
            await asyncio.sleep(0)
        self.assertEqual((self.snapshot()["http_slots"], self.snapshot()["retained_http_cleanup"]), (1,1))
        release.set()
        await asyncio.gather(task, return_exceptions=True)
        self.assertEqual((self.snapshot()["http_slots"], self.snapshot()["retained_http_cleanup"]), (0,0))

    async def test_invalid_explicit_capacity_and_thresholds(self):
        async def app(scope, receive, send):
            pass
        for value in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                LifecycleState(self.state.config, websocket_capacity=value)
        self.state.attach(app, app)
        with self.assertRaises(RuntimeError):
            self.state.configure_websocket_capacity(2)
        with self.assertRaises(ValueError):
            self.state.observe(stall_after=0, lag_threshold=.1, loop_lag=0)
