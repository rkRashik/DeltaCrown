"""Pinned, repository-owned Daphne adapter. No installed-package mutation.

Only the coordinated default-OFF launcher enables this contract. Incomplete
shutdown leaves the reactor alive for external termination, never false success.
"""
# Daphne must install its reactor before application/framework imports.
from daphne.server import Server
from daphne.cli import CommandLineInterface
from twisted.internet import defer
import asyncio
from dataclasses import dataclass
from importlib.metadata import version
import logging
import os

from . import asgi_lifecycle as lifecycle

logger = logging.getLogger(__name__)


class _ShutdownDeferred(defer.Deferred):
    def cancel(self):
        # Cancelling an acknowledgement must not authorize reactor exit while
        # cleanup is retained. External process termination remains independent.
        pass


@dataclass(eq=False)
class _WebSocketOutcome:
    application: object
    closed: object
    close_requested: bool = False

    @property
    def complete(self):
        return (self.closed.done() and self.application.done()
                and not self.application.cancelled() and self.application.exception() is None
                and (not self.close_requested or self.closed.result()["clean"]))


class OwnLobbyServer(Server):
    def __init__(self, *args, **kwargs):
        self.lifecycle = lifecycle._runtime
        if (version("daphne") != "4.2.3" or self.lifecycle is None
                or not self.lifecycle.attached):
            raise RuntimeError("OwnLobby adapter requires pinned Daphne and coordinated ASGI wrappers")
        self.application_tasks = set()
        self.http_tasks = set()
        self.websocket_protocols = {}
        self._shutdown_websockets = ()
        self._shutdown_protocols = []
        self.listening_ports = []
        self._shutdown_deferred = None
        self._shutdown_task = None
        super().__init__(*args, **kwargs)

    def listen_success(self, port):
        self.listening_ports.append(port)
        return super().listen_success(port)

    def create_application(self, protocol, scope):
        queue = super().create_application(protocol, scope)
        task = self.connections.get(protocol, {}).get("application_instance")
        if task is not None:
            self.application_tasks.add(task)
            task.add_done_callback(self._application_done)
            if scope["type"] == "http":
                self.http_tasks.add(task)
                task.add_done_callback(self.http_tasks.discard)
            elif scope["type"] == "websocket":
                closed = asyncio.get_event_loop().create_future()
                if "disconnected" in self.connections.get(protocol, {}):
                    closed.set_result(None)
                record = _WebSocketOutcome(task, closed)
                self.websocket_protocols[protocol] = record
                self.lifecycle._websocket_closures[task] = closed
                if self.lifecycle.quiescing:
                    self._shutdown_protocols.append(record)
                task.add_done_callback(lambda _: self._forget_websocket(protocol))
        return queue

    async def handle_reply(self, protocol, message):
        if (self.lifecycle.quiescing and message.get("type") == "websocket.close"
                and message.get("code") == 1012
                and protocol in self.websocket_protocols
                and protocol.state == protocol.STATE_OPEN):
            details = self.connections.get(protocol)
            if details is not None and "disconnected" not in details:
                # Pinned Autobahn 26.7.1 sendClose rejects registered code 1012.
                # Its frame primitive preserves the ordinary handshake/state/
                # timer path. This narrow adapter bridge does not imply delivery.
                if version("autobahn") != "26.7.1":
                    raise RuntimeError("Restart close requires reviewed Autobahn pin")
                self.websocket_protocols[protocol].close_requested = True
                protocol.sendCloseFrame(code=1012)
                return
        return await super().handle_reply(protocol, message)

    def protocol_disconnected(self, protocol):
        super().protocol_disconnected(protocol)
        record = self.websocket_protocols.get(protocol)
        if record is not None and not record.closed.done():
            # Daphne onClose, not an invented ASGI event. EOF is not a clean
            # restart handshake, even if the application subsequently exits.
            record.closed.set_result(dict(clean=protocol.wasClean, code=protocol.remoteCloseCode))
        self._forget_websocket(protocol)

    def _forget_websocket(self, protocol):
        record = self.websocket_protocols.get(protocol)
        if record is not None and record.application.done() and record.closed.done():
            del self.websocket_protocols[protocol]
            self.lifecycle._websocket_closures.pop(record.application, None)

    def _application_done(self, task):
        self.application_tasks.discard(task)
        if not task.cancelled():
            error = task.exception()
            if error is not None:
                logger.error("application_finished error_type=%s", type(error).__name__)

    def kill_all_applications(self):
        if self._shutdown_deferred is None:
            self.lifecycle.phase = "QUIESCING"  # No await: reject existing keep-alive work immediately.
            self._shutdown_protocols = list(self.websocket_protocols.values())
            self._shutdown_deferred = _ShutdownDeferred()
            self._shutdown_task = asyncio.get_event_loop().create_task(self._shutdown())
            self._shutdown_task.add_done_callback(self._shutdown_result)
        return self._shutdown_deferred

    def _pending(self):
        return {t for t in (*self.application_tasks, *self.lifecycle.http._children,
                           *(record.closed for record in self.websocket_protocols.values())) if not t.done()}

    async def _wait_drained(self, deadline):
        while True:
            pending = self._pending()
            if not pending:
                await asyncio.sleep(0)  # Include dispatches already queued before quiescing.
                if not self._pending():
                    return True
                continue
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                return False
            await asyncio.wait(pending, timeout=remaining)  # Never cancels protected children.

    async def _shutdown(self):
        loop = asyncio.get_running_loop()
        config = self.lifecycle.config
        drain_end = loop.time() + config.drain_seconds
        cleanup_end = drain_end + config.cleanup_seconds
        listeners = [defer.maybeDeferred(port.stopListening).asFuture(loop)
                     for port in self.listening_ports]
        self._shutdown_websockets = tuple(self.lifecycle.websockets)
        closes = [asyncio.create_task(session.close()) for session in self._shutdown_websockets]
        self.application_tasks.update(closes)
        for task in closes:
            task.add_done_callback(self._application_done)
        if listeners:
            done, pending = await asyncio.wait(listeners, timeout=max(0, drain_end - loop.time()))
            if pending or any(task.exception() is not None for task in done):
                return False
        if await self._wait_drained(drain_end):
            return True
        # HTTP outers only. Cancelling a WS consumer could interrupt its genuine
        # disconnect/group/DB cleanup; it must finish or remain incomplete.
        for task in tuple(self.http_tasks):
            if not task.done():
                task.cancel()
        return await self._wait_drained(cleanup_end)

    def _shutdown_result(self, task):
        try:
            complete = task.result()
        except BaseException as error:
            logger.error("shutdown_incomplete error_type=%s", type(error).__name__)
            complete = False
        if (complete and not self._pending()
                and not self.lifecycle._websocket_owners
                and all(session.cleaned for session in self._shutdown_websockets)
                and all(record.complete for record in self._shutdown_protocols)):
            self.lifecycle.phase = "DRAINED"
            if not self._shutdown_deferred.called:
                self._shutdown_deferred.callback(None)
        else:
            self.lifecycle.phase = "SHUTDOWN_INCOMPLETE"
            logger.error("shutdown_incomplete applications=%d children=%d",
                         len(self.application_tasks), self.lifecycle.http.active_count)
            # Intentionally pending: Render owns forced termination, not Django.


class OwnLobbyCLI(CommandLineInterface):
    server_class = OwnLobbyServer

    def run(self, args):
        config = lifecycle.LifecycleConfig.from_environ(os.environ)
        if config is None or lifecycle._runtime is not None:
            raise RuntimeError("OwnLobby launcher requires an enabled, single lifecycle runtime")
        lifecycle._runtime = lifecycle.LifecycleState(config)
        return super().run(args)


if __name__ == "__main__":
    OwnLobbyCLI.entrypoint()
