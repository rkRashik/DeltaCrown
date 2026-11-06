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
    def __init__(self, config):
        self.config = config
        self.phase = "RUNNING"
        self.http = None
        self.websockets = set()
        self.attached = False

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
            await send({"type": "websocket.close", "code": 1012})
            return
        accepted = False
        closing = False

        async def close():
            nonlocal closing
            if accepted and not closing:
                closing = True
                await send({"type": "websocket.close", "code": 1012})

        async def forward(message):
            nonlocal accepted, closing
            if message["type"] == "websocket.accept":
                if self.lifecycle.quiescing:
                    await send({"type": "websocket.close", "code": 1012})
                    return
                accepted = True
            if message["type"] == "websocket.close":
                closing = True
            if closing and message["type"] == "websocket.send":
                return
            await send(message)

        self.lifecycle.websockets.add(close)
        try:
            await self.application(scope, receive, forward)
        finally:
            self.lifecycle.websockets.remove(close)


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

    @property
    def active_count(self):
        return len(self._children)

    @property
    def occupied_count(self):
        return self._occupied

    def _child_finished(self, child):
        self._children.remove(child)
        self._occupied -= 1  # Exactly one callback, only after terminal completion.

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            raise ValueError("HTTPDisconnectDrain accepts HTTP only")
        if (self.lifecycle is not None and self.lifecycle.quiescing
                or self.capacity is not None and self._occupied >= self.capacity):
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
        try:
            child = asyncio.create_task(self.application(scope, receive_one, send),
                                        name="ownlobby-http-lifecycle")
        except BaseException:
            self._occupied -= 1
            raise
        self._children.add(child)
        child.add_done_callback(self._child_finished)
        cancelled = False
        while not child.done():
            try:
                await asyncio.shield(child)
            except asyncio.CancelledError:
                if asyncio.current_task().cancelling():
                    cancelled = True
                    abort.set()
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
