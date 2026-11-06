"""HTTP lifecycle-drain prototype; deliberately not wired into production.

Cancellation cannot stop synchronous work. This wrapper retains the Django task
until it finishes, including its original cleanup. Optional admission bounds the
number of children, not execution time or memory per request. Permanently blocked
work can occupy capacity indefinitely. No production capacity is selected here.
"""
import asyncio


class HTTPDisconnectDrain:
    def __init__(self, application, *, capacity=None):
        if capacity is not None and (type(capacity) is not int or capacity <= 0):
            raise ValueError("HTTP capacity must be a positive integer or None")
        self.application = application
        self.capacity = capacity
        self._children = set()
        self._occupied = 0
        self.peak_occupied = 0
        self.rejections = 0
        self.pending_receives = 0
        self.cancellations = 0

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
        if self.capacity is not None and self._occupied >= self.capacity:
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
            self.pending_receives += 1
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
                self.pending_receives -= 1
                receiving = False

        # No await between the capacity check, reservation and child registration.
        # One ASGI event loop owns these counters; rejected calls never read a body.
        self._occupied += 1
        self.peak_occupied = max(self.peak_occupied, self._occupied)
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
                    self.cancellations += 1
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
