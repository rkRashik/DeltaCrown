"""Gated HTTP lifecycle protection; activation is coordinated with our adapter.

Finite cancellation cleanup is verified in research PR #43 (CI #78).
Blocked work and mixed-protocol shutdown remain unresolved (CI #79/#80).
Cancellation cannot stop synchronous work. This wrapper retains the Django task
until it finishes, including its original cleanup. Optional admission bounds the
number of children, not execution time or memory per request. Permanently blocked
work can occupy capacity indefinitely. No production capacity is selected here.
"""
import asyncio
from dataclasses import dataclass
import math
import time


@dataclass(frozen=True)
class LifecycleConfig:
    capacity: int
    drain_seconds: float
    cleanup_seconds: float
    host_seconds: float  # Operator declaration, not verification of Render settings.

    @classmethod
    def from_environ(cls, environ):
        gate = environ.get("OWNLOBBY_ASGI_LIFECYCLE_ENABLED", "0")
        if gate == "0":
            return None
        if gate != "1":
            raise ValueError("OWNLOBBY_ASGI_LIFECYCLE_ENABLED must be 0 or 1")
        try:
            config = cls(int(environ["OWNLOBBY_HTTP_CAPACITY"]),
                         float(environ["OWNLOBBY_DRAIN_SECONDS"]),
                         float(environ["OWNLOBBY_CLEANUP_SECONDS"]),
                         float(environ["OWNLOBBY_DECLARED_HOST_SHUTDOWN_SECONDS"]))
        except (KeyError, ValueError):
            raise ValueError("Enabled lifecycle requires explicit capacity and shutdown budgets") from None
        if (config.capacity <= 0 or any(not math.isfinite(v) or v <= 0 for v in
                (config.drain_seconds, config.cleanup_seconds, config.host_seconds))
                or config.drain_seconds + config.cleanup_seconds >= config.host_seconds):
            raise ValueError("Lifecycle budgets must be positive, finite, and fit inside the declared host window")
        return config


class LifecycleState:
    def __init__(self, config, *, websocket_capacity=None):
        self.config = config
        self.phase = "RUNNING"
        self.http = None
        self.websockets = set()
        self._websocket_owners = set()
        self._websocket_closures = {}  # Actual Daphne task -> protocol-closed future.
        self.websocket_capacity = None
        if websocket_capacity is not None:
            self.configure_websocket_capacity(websocket_capacity)
        self.ws_peak = self.ws_pending_peak = self.ws_accepted_peak = 0
        self.ws_rejections = self.ws_quiescing_rejections = 0
        self.ws_completed = self.ws_failed = 0
        self.attached = False

    def configure_websocket_capacity(self, capacity):
        """QA supplies this explicitly before attach; no env/default activation."""
        if getattr(self, "attached", False):
            raise RuntimeError("Configure admission before attaching applications")
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("WebSocket capacity must be a positive integer")
        self.websocket_capacity = capacity

    def _ws_counts(self):
        owners = tuple(self._websocket_owners)
        accepted = sum(session.accepted for session in owners)
        return len(owners)-accepted, accepted

    def _ws_changed(self):
        pending, accepted = self._ws_counts()
        self.ws_peak = max(self.ws_peak, pending+accepted)
        self.ws_pending_peak = max(self.ws_pending_peak, pending)
        self.ws_accepted_peak = max(self.ws_accepted_peak, accepted)

    def observe(self, *, stall_after, loop_lag, lag_threshold, now=None):
        """Pull-only observation: no timers, health changes or recovery actions.

        Progress means HTTP body bytes forwarded or a child completing, not an
        assumption that all application/DB work is healthy. Lag is sampled by
        the QA caller; an independent observer is needed during a blocked loop.
        """
        if any(not math.isfinite(v) or v <= 0 for v in (stall_after, lag_threshold)):
            raise ValueError("Explicit positive observation thresholds required")
        if not math.isfinite(loop_lag) or loop_lag < 0:
            raise ValueError("Loop lag must be finite and nonnegative")
        now = time.monotonic() if now is None else now
        http = self.http
        pending, accepted = self._ws_counts()
        full = http.capacity is not None and http.occupied_count >= http.capacity
        no_progress = max(0, now-max(http.full_since, http.last_progress)) if full else 0
        ws_full = self.websocket_capacity is not None and pending+accepted >= self.websocket_capacity
        signal = "AVAILABLE"
        if self.quiescing:
            signal = self.phase
        elif loop_lag >= lag_threshold:
            signal = "LOOP_LAG_OBSERVED"
        elif full and no_progress >= stall_after:
            signal = "SATURATED_NO_OBSERVED_PROGRESS"
        elif full or ws_full:
            signal = "CAPACITY_EXHAUSTED"
        return dict(signal=signal, phase=self.phase, http_active=http.active_count,
                    http_peak=http.peak_active, http_slots=http.occupied_count,
                    http_rejections=http.rejections, http_quiescing_rejections=http.quiescing_rejections,
                    http_completed=http.completed, http_progress=http.progress,
                    http_no_progress_seconds=round(no_progress, 4),
                    retained_http_cleanup=len(http._retained), ws_pending=pending, ws_accepted=accepted,
                    ws_slots=pending+accepted, ws_peak=self.ws_peak, ws_pending_peak=self.ws_pending_peak,
                    ws_accepted_peak=self.ws_accepted_peak, ws_rejections=self.ws_rejections,
                    ws_completed=self.ws_completed, ws_failed=self.ws_failed,
                    ws_quiescing_rejections=self.ws_quiescing_rejections,
                    retained_ws_cleanup=sum(s.closing or s.disconnect_received or s.application_ended
                                            for s in tuple(self._websocket_owners)), loop_lag_seconds=loop_lag)

    @property
    def quiescing(self):
        return self.phase != "RUNNING"

    def attach(self, http, websocket):
        if self.attached:
            raise RuntimeError("Lifecycle wrappers already attached")
        self.http = HTTPDisconnectDrain(http, capacity=self.config.capacity, lifecycle=self)
        self.attached = True
        return self.http, WebSocketShutdownGate(websocket, self)


_runtime = None


def require_runtime(config):
    if _runtime is None or _runtime.config != config:
        raise RuntimeError("Enabled ASGI lifecycle requires the coordinated OwnLobby Daphne launcher")
    return _runtime


class WebSocketShutdownGate:
    def __init__(self, application, lifecycle):
        self.application, self.lifecycle = application, lifecycle

    async def __call__(self, scope, receive, send):
        if self.lifecycle.quiescing:
            self.lifecycle.ws_quiescing_rejections += 1
            await send({"type": "websocket.close", "code": 1012})
            return
        if (self.lifecycle.websocket_capacity is not None
                and len(self.lifecycle._websocket_owners) >= self.lifecycle.websocket_capacity):
            self.lifecycle.ws_rejections += 1
            await send({"type": "websocket.close", "code": 1013})
            return  # Before auth/routing/receive; Daphne rejects an unaccepted handshake.
        session = WebSocketSession()
        self.lifecycle._websocket_owners.add(session)  # Atomic on the ASGI loop.
        self.lifecycle._ws_changed()
        closed = self.lifecycle._websocket_closures.get(asyncio.current_task())

        def release_slot(_=None):
            protocol_done = (closed.done() and not closed.cancelled()) if closed is not None else session.disconnect_received
            if session.application_ended and protocol_done and session in self.lifecycle._websocket_owners:
                self.lifecycle._websocket_owners.remove(session)
                self.lifecycle.ws_completed += 1
                self.lifecycle.ws_failed += session.failed

        if closed is not None:
            closed.add_done_callback(release_slot)

        async def close():
            if session.accepted and not session.closing:
                session.closing = True
                session.close_requested = True
                try:
                    await send({"type": "websocket.close", "code": 1012})
                except BaseException:
                    session.failed = True
                    raise

        session.close = close

        async def incoming():
            message = await receive()
            if message["type"] == "websocket.disconnect":
                session.disconnect_received = True
            return message  # Only the original protocol may supply disconnect.

        async def forward(message):
            if message["type"] == "websocket.accept":
                if self.lifecycle.quiescing:
                    await send({"type": "websocket.close", "code": 1012})
                    return
                session.accepted = True
                self.lifecycle._ws_changed()
            if message["type"] == "websocket.close":
                session.closing = True
            if session.closing and message["type"] == "websocket.send":
                return
            await send(message)

        self.lifecycle.websockets.add(session)
        try:
            await self.application(scope, incoming, forward)
        except BaseException:
            session.failed = True
            raise
        else:
            session.application_finished = True
        finally:
            session.application_ended = True
            self.lifecycle.websockets.remove(session)
            release_slot()  # A close request or application exit alone never frees a slot.


@dataclass(eq=False)
class WebSocketSession:
    accepted: bool = False
    closing: bool = False
    close_requested: bool = False
    disconnect_received: bool = False
    application_finished: bool = False
    application_ended: bool = False
    failed: bool = False
    close: object = None

    @property
    def cleaned(self):
        return (self.application_finished and not self.failed
                and (not self.accepted or self.disconnect_received))


class HTTPDisconnectDrain:
    """One event-loop-owned HTTP wrapper; capacity is optional, never a deadline."""

    def __init__(self, application, *, capacity=None, lifecycle=None):
        if capacity is not None and (type(capacity) is not int or capacity <= 0):
            raise ValueError("HTTP capacity must be a positive integer or None")
        self.application = application
        self.capacity = capacity
        self.lifecycle = lifecycle
        self._children = set()
        self._occupied = 0
        self._retained = set()
        self.peak_active = self.rejections = self.quiescing_rejections = self.completed = self.progress = 0
        self.last_progress = time.monotonic()
        self.full_since = self.last_progress

    def _progress(self):
        self.progress += 1
        self.last_progress = time.monotonic()

    @property
    def active_count(self):
        return len(self._children)

    @property
    def occupied_count(self):
        return self._occupied

    def _child_finished(self, child):
        self._children.remove(child)
        self._retained.discard(child)
        self._occupied -= 1  # Exactly one callback, only after terminal completion.
        self.completed += 1
        self._progress()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            raise ValueError("HTTPDisconnectDrain accepts HTTP only")
        if (self.lifecycle is not None and self.lifecycle.quiescing
                or self.capacity is not None and self._occupied >= self.capacity):
            if self.lifecycle is not None and self.lifecycle.quiescing:
                self.quiescing_rejections += 1
            else:
                self.rejections += 1
            await send({"type": "http.response.start", "status": 503,
                        "headers": [(b"cache-control", b"no-store")]})
            await send({"type": "http.response.body", "body": b"Service busy."})
            return
        abort = asyncio.Event()
        receiving = False

        async def receive_one():
            nonlocal receiving
            if receiving:
                raise RuntimeError("Concurrent HTTP receive calls are unsupported")
            if abort.is_set():
                return {"type": "http.disconnect"}
            receiving = True
            incoming = asyncio.create_task(receive(), name="ownlobby-http-receive")
            interrupted = asyncio.create_task(abort.wait(), name="ownlobby-http-abort")
            try:
                await asyncio.wait((incoming, interrupted), return_when=asyncio.FIRST_COMPLETED)
                if abort.is_set():
                    return {"type": "http.disconnect"}
                message = incoming.result()
                if message["type"] == "http.disconnect":
                    abort.set()
                    self._retained.add(child)
                elif message.get("body"):
                    self._progress()
                return message
            finally:
                for task in (incoming, interrupted):
                    if not task.done():
                        task.cancel()
                await asyncio.gather(incoming, interrupted, return_exceptions=True)
                receiving = False

        # No await between the capacity check, reservation and child registration.
        # One ASGI event loop owns these counters; rejected calls never read a body.
        self._occupied += 1
        if self.capacity is not None and self._occupied == self.capacity:
            self.full_since = time.monotonic()

        async def forward(message):
            await send(message)
            if message["type"] == "http.response.body" and message.get("body"):
                self._progress()

        try:
            child = asyncio.create_task(self.application(scope, receive_one, forward),
                                        name="ownlobby-http-lifecycle")
        except BaseException:
            self._occupied -= 1
            raise
        self._children.add(child)
        self.peak_active = max(self.peak_active, len(self._children))
        child.add_done_callback(self._child_finished)
        cancelled = False
        while not child.done():
            try:
                await asyncio.shield(child)
            except asyncio.CancelledError:
                if asyncio.current_task().cancelling():
                    cancelled = True
                    abort.set()
                    if not child.done():
                        self._retained.add(child)
                elif not child.done():
                    raise
            except Exception:
                break  # Retrieve and propagate the child's exception below.
        try:
            result = child.result()
        except BaseException as error:
            if cancelled:
                raise asyncio.CancelledError from error
            raise
        if cancelled:
            raise asyncio.CancelledError
        return result
