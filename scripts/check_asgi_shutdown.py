"""QA-only Daphne shutdown observations; no migrations or production wiring.

All seconds/capacity below are synthetic fixture bounds, not production policy.
The parent supervisor forcibly ends blocked children and reports that separately
from Django cleanup. PostgreSQL inspection is restricted to its tagged sessions.
"""
import asyncio
from contextvars import ContextVar
import http.client
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
WORK_SECONDS = 8
APP_CLOSE_SECONDS = 5  # Existing startup default; not a new production value.
CHILD_CEILING = 35


def serve(port, folder):
    sys.path.insert(0, str(ROOT))
    import dotenv
    dotenv.load_dotenv = lambda *a, **k: False
    dotenv.dotenv_values = lambda *a, **k: {}
    from scripts.check_asgi_cancellation import require_local_database
    require_local_database()
    original_connect = socket.socket.connect

    def local_connect(sock, address):
        if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
            raise RuntimeError("External sockets forbidden in shutdown QA")
        return original_connect(sock, address)

    socket.socket.connect = local_connect
    import django
    django.setup()
    from django.conf import settings
    from django.core.asgi import get_asgi_application
    from django.core.signals import request_finished
    from django.db import connection
    from django.http import HttpResponse, StreamingHttpResponse
    from django.urls import path
    from asgiref.sync import SyncToAsync
    from channels.generic.websocket import AsyncWebsocketConsumer
    from channels.routing import ProtocolTypeRouter, URLRouter
    from daphne.server import Server
    from apps.common.asgi_lifecycle import HTTPDisconnectDrain
    from deltacrown.middleware.request_memory_probe import _rss_bytes

    assert settings.DATABASES["default"]["HOST"] in {"127.0.0.1", "localhost", "::1"}
    assert settings.DATABASES["default"]["NAME"] == "ownlobby_test"
    assert settings.DATABASES["default"]["CONN_MAX_AGE"] == 0
    settings.DATABASES["default"]["OPTIONS"] = dict(application_name="ownlobby_shutdown_" + str(os.getpid()),
                                                   connect_timeout=3, options="-c statement_timeout=15000")
    settings.ROOT_URLCONF = __name__
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
    began = time.monotonic()
    kind = ContextVar("shutdown_qa_kind", default="process")
    mutex = threading.RLock()
    state = {"events": [], "loop_returned": False, "work_started": False, "work_finished": False,
             "shutdown_entered": False, "shutdown_wait_returned": False, "new_requests": 0,
             "loop_lag_ms": 0.0, "peak_rss_mib": 0.0, "peak_threads": 0}
    wrapper = None
    server = None

    def snapshot():
        with mutex:
            rss = (_rss_bytes() or 0) / 1048576
            state["peak_rss_mib"] = max(state["peak_rss_mib"], rss)
            state["peak_threads"] = max(state["peak_threads"], len(threading.enumerate()))
            value = dict(state, elapsed_ms=round((time.monotonic() - began) * 1000, 2),
                         children=wrapper.active_count if wrapper else 0,
                         slots=wrapper.occupied_count if wrapper else 0,
                         outer_cancellations=wrapper.cancellations if wrapper else 0,
                         executors=len(SyncToAsync.context_to_thread_executor),
                         receives=wrapper.pending_receives if wrapper else 0)
            temporary = folder / "sample.tmp"
            temporary.write_text(json.dumps(value), encoding="utf-8")
            temporary.replace(folder / "sample.json")

    def event(name, **details):
        with mutex:
            if len(state["events"]) < 96:
                state["events"].append(dict(event=name, kind=kind.get(),
                                           elapsed_ms=round((time.monotonic() - began) * 1000, 2), **details))
            snapshot()

    def finished(**kwargs):
        event("django_finished", db_closed=connection.connection is None)

    request_finished.connect(finished, weak=False)

    def health(request):
        if request.path == "/new/":
            state["new_requests"] += 1
        return HttpResponse("synthetic")

    def slow(request):
        state["work_started"] = True
        event("work_started")
        with connection.cursor() as cursor:
            if os.environ["QA_SHUTDOWN_CASE"] == "blocked":
                cursor.execute("SELECT 1")
                event("permanent_wait_entered")
                threading.Event().wait()  # Supervisor/watchdog, never cancellation, ends this process.
            else:
                cursor.execute("SELECT pg_sleep(%s)", [WORK_SECONDS])
        state["work_finished"] = True
        event("work_finished")
        return HttpResponse("finite synthetic work")

    def stream(request):
        async def chunks():
            event("stream_started")
            try:
                yield b"synthetic-stream"
                await asyncio.sleep(30)
                yield b"end"
            finally:
                event("stream_finalized")
        response = StreamingHttpResponse(chunks(), content_type="text/plain")
        response._resource_closers.append(lambda: event("stream_response_closed"))
        return response

    globals()["urlpatterns"] = [path("healthz/", health), path("new/", health),
                                 path("slow/", slow), path("stream/", stream)]

    class Socket(AsyncWebsocketConsumer):
        async def __call__(self, *args, **kwargs):
            try:
                await super().__call__(*args, **kwargs)
            finally:
                event("ws_application_finished")

        async def connect(self):
            await self.accept()
            event("ws_connected")

        async def disconnect(self, code):
            event("ws_disconnect_callback", code=code)

    wrapper = HTTPDisconnectDrain(get_asgi_application(), capacity=4)  # QA-only spare admission slot.
    router = ProtocolTypeRouter({"http": wrapper,
                                 "websocket": URLRouter([path("ws/", Socket.as_asgi())])})
    heartbeat = None

    async def beat():
        previous = time.monotonic()
        while True:
            await asyncio.sleep(.02)
            now = time.monotonic()
            state["loop_lag_ms"] = max(state["loop_lag_ms"], (now - previous - .02) * 1000)
            previous = now

    async def application(scope, receive, send):
        nonlocal heartbeat
        if heartbeat is None:
            heartbeat = asyncio.create_task(beat())
        token = kind.set(scope.get("path", "unknown"))
        try:
            await router(scope, receive, send)
        finally:
            event("application_finished")
            kind.reset(token)

    class ObservedServer(Server):
        def connection_summary(self):
            from daphne.http_protocol import WebRequest
            from daphne.ws_protocol import WebSocketProtocol
            groups = {name: dict(total=0, with_application_instance=0, without_application_instance=0,
                                 application_none=0, pending=0, completed=0, cancellation_requested=0)
                      for name in ("http", "websocket", "other")}
            for protocol, details in self.connections.items():
                category = "http" if isinstance(protocol, WebRequest) else \
                           "websocket" if isinstance(protocol, WebSocketProtocol) else "other"
                group = groups[category]
                group["total"] += 1
                if "application_instance" not in details:
                    group["without_application_instance"] += 1
                    continue
                group["with_application_instance"] += 1
                task = details["application_instance"]
                if task is None:
                    group["application_none"] += 1
                else:
                    group["completed" if task.done() else "pending"] += 1
                    group["cancellation_requested"] += bool(getattr(task, "cancelling", lambda: 0)())
            return dict(total=sum(g["total"] for g in groups.values()), categories=groups)

        def kill_all_applications(self):
            state["shutdown_entered"] = True
            event("shutdown_entered")
            boundary = dict(before=self.connection_summary(), original_returned=False,
                            original_raised=False, exception_type=None, returned_deferred=False,
                            deferred_fired=False)
            state["shutdown_boundary"] = boundary
            event("shutdown_original_call", summary=boundary["before"])
            try:
                result = super().kill_all_applications()  # Original cancellation and gather semantics.
            except BaseException as error:
                origin = error.__traceback__
                while origin.tb_next is not None:
                    origin = origin.tb_next
                boundary.update(original_raised=True, exception_type=type(error).__name__,
                                raise_site_is_original=origin.tb_frame.f_code is Server.kill_all_applications.__code__,
                                raise_details_missing_application=isinstance(origin.tb_frame.f_locals.get("details"), dict)
                                    and "application_instance" not in origin.tb_frame.f_locals["details"],
                                after=self.connection_summary())
                del origin
                # Booleans only: no exception args, raw traceback or frame locals.
                event("shutdown_original_raised", exception_type=boundary["exception_type"])
                raise
            from twisted.internet.defer import Deferred
            boundary.update(original_returned=True, returned_deferred=isinstance(result, Deferred),
                            after=self.connection_summary())
            event("shutdown_original_returned", returned_deferred=boundary["returned_deferred"])

            def observed(value):
                state["shutdown_wait_returned"] = True
                boundary["deferred_fired"] = True
                event("shutdown_wait_returned")
                return value

            result.addBoth(observed)
            return result

    def monitor():
        handled = set()
        while True:
            snapshot()
            for n in range(3):
                command = folder / f"cancel-{n}"
                if command.exists() and n not in handled:
                    handled.add(n)
                    from twisted.internet import reactor

                    def cancel_outer():
                        event("qa_repeated_outer_cancel")
                        for details in list(server.connections.values()):
                            task = details.get("application_instance")
                            if task is not None and not task.done():
                                task.cancel()  # Only Daphne-owned outers, never protected children.

                    reactor.callFromThread(cancel_outer)
            time.sleep(.05)

    server = ObservedServer(application=application, endpoints=[f"tcp:port={port}:interface=127.0.0.1"],
                            http_timeout=3600, application_close_timeout=APP_CLOSE_SECONDS, verbosity=0)
    from twisted.internet import reactor
    reactor.addSystemEventTrigger("during", "shutdown", lambda: event("reactor_shutdown_during"))
    reactor.addSystemEventTrigger("after", "shutdown", lambda: event("reactor_shutdown_after"))
    threading.Thread(target=monitor, name="qa-shutdown-monitor", daemon=True).start()
    try:
        server.run()
    finally:
        state["loop_returned"] = True
        event("reactor_returned")
        # Daemon observer stays alive during Python executor atexit joins.


def main(mixed_only=False):
    assert sys.platform == "linux", "Signal/process contract requires disposable Linux QA"
    sys.path.insert(0, str(ROOT))
    from scripts.check_asgi_cancellation import require_local_database
    import psycopg2
    database = require_local_database()
    observer = psycopg2.connect(database, connect_timeout=3, options="-c statement_timeout=2000")
    observer.autocommit = True
    results = []
    try:
        for case in (("mixed",) if mixed_only else ("finite", "blocked", "mixed")):
            with tempfile.TemporaryDirectory(prefix="ownlobby-shutdown-") as directory:
                folder = Path(directory)
                with socket.socket() as reserved:
                    reserved.bind(("127.0.0.1", 0))
                    port = reserved.getsockname()[1]
                env = {k: os.environ[k] for k in ("PATH", "SYSTEMROOT", "TEMP", "TMP") if k in os.environ}
                env.update(DATABASE_URL_TEST=database, DATABASE_URL="postgresql://synthetic@127.0.0.1:1/unused_test",
                           DJANGO_SETTINGS_MODULE="deltacrown.settings_media_qa", DJANGO_DEBUG="0",
                           DJANGO_SECRET_KEY="synthetic-shutdown-qa-only-not-a-production-key-0123456789",
                           DISABLE_INPROCESS_MATCH_REMINDER="1", ENABLE_CELERY_WORKER="0",
                           ENABLE_CELERY_BEAT="0", ENABLE_DISCORD_BOT="0", REDIS_URL="", SENTRY_DSN="",
                           COMPETITION_APP_ENABLED="1", AWS_EC2_METADATA_DISABLED="true",
                           PYTHONPATH=str(ROOT), PYTHONUNBUFFERED="1", QA_SHUTDOWN_CASE=case)
                with (folder / "child.log").open("w", encoding="utf-8") as log:
                    proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--serve",
                                             str(port), str(folder)], env=env, stdout=log, stderr=log)
                    sockets = []
                    samples = []
                    forced = False
                    parent_started = time.monotonic()

                    def read():
                        try:
                            return json.loads((folder / "sample.json").read_text(encoding="utf-8"))
                        except (FileNotFoundError, json.JSONDecodeError):
                            return {}

                    def db():
                        with observer.cursor() as cursor:
                            cursor.execute("SELECT state,wait_event_type,wait_event,count(*) FROM pg_stat_activity "
                                           "WHERE application_name=%s GROUP BY state,wait_event_type,wait_event",
                                           ["ownlobby_shutdown_" + str(proc.pid)])
                            return [dict(state=s, wait_type=t, wait=w, count=n) for s,t,w,n in cursor.fetchall()]

                    def get(path):
                        client = http.client.HTTPConnection("127.0.0.1", port, timeout=.4)
                        try:
                            client.request("GET", path)
                            response = client.getresponse()
                            response.read()
                            return response.status
                        except (OSError, http.client.HTTPException):
                            return "unavailable"
                        finally:
                            client.close()

                    def until(predicate, seconds, allow_exited=False):
                        deadline = time.monotonic() + seconds
                        while time.monotonic() < deadline:
                            if predicate():
                                return
                            assert allow_exited or proc.poll() is None, "QA child exited before its bounded observation"
                            time.sleep(.05)
                        raise AssertionError("QA observation deadline: " + json.dumps(dict(case=case, snapshot=read())))

                    def opened(path, websocket=False):
                        sock = socket.create_connection(("127.0.0.1", port), timeout=2)
                        sockets.append(sock)
                        extra = ("Upgrade: websocket\r\nConnection: Upgrade\r\nOrigin: http://localhost\r\n"
                                 "Sec-WebSocket-Version: 13\r\nSec-WebSocket-Key: MDEyMzQ1Njc4OWFiY2RlZg==\r\n") if websocket else ""
                        sock.sendall((f"GET {path} HTTP/1.1\r\nHost: localhost\r\n{extra}\r\n").encode())
                        if websocket or path == "/stream/":
                            header = b""
                            while not header.endswith(b"\r\n\r\n"):
                                part = sock.recv(1)
                                assert part and len(header) < 4096
                                header += part
                            assert header.startswith(b"HTTP/1.1 101" if websocket else b"HTTP/1.1 200")
                        return sock

                    try:
                        until(lambda: get("/healthz/") == 200, 15)
                        slow = opened("/slow/")
                        until(lambda: read().get("work_started") and bool(db()), 3)
                        if case == "mixed":
                            opened("/stream/")
                            opened("/ws/", websocket=True)
                            until(lambda: {"stream_started", "ws_connected"} <=
                                  {e["event"] for e in read().get("events", [])}, 3)
                        timeout_evidence = None
                        if case == "blocked":
                            until(lambda: any(e["event"] == "permanent_wait_entered" for e in read().get("events", [])), 3)
                            slow.close()
                            until(lambda: read().get("outer_cancellations", 0) >= 2, APP_CLOSE_SECONDS + 4)
                            timeout_evidence = dict(snapshot=read(), db=db(), health=get("/healthz/"))
                            assert timeout_evidence["snapshot"]["children"] == 1 and timeout_evidence["db"]
                        signalled = time.monotonic()
                        proc.send_signal(signal.SIGTERM)
                        until(lambda: read().get("shutdown_entered"), 2)
                        before_new = read().get("new_requests", 0)
                        admission = get("/new/")
                        time.sleep(.15)
                        new_started = read().get("new_requests", 0) > before_new
                        for n in range(3):
                            (folder / f"cancel-{n}").touch()
                            time.sleep(.12)
                        if proc.poll() is None:
                            proc.send_signal(signal.SIGTERM)
                        grace_observation = 3 if case == "blocked" else WORK_SECONDS + 3
                        while proc.poll() is None and time.monotonic() - signalled < grace_observation:
                            samples.append(dict(after_signal_ms=round((time.monotonic()-signalled)*1000, 2),
                                                snapshot=read(), db=db()))
                            time.sleep(.15)
                        pre_force = dict(snapshot=read(), db=db())
                        if proc.poll() is None:
                            forced = True
                            proc.kill()
                        proc.wait(timeout=3)
                        until(lambda: not db(), 2, allow_exited=True)
                        last = read()
                        finished = [e for e in last.get("events", []) if e["event"] == "django_finished" and e["kind"] == "/slow/"]
                        cleanup = bool(finished and all(e["db_closed"] for e in finished)
                                       and last.get("children") == 0 and last.get("executors") == 0)
                        peer = []
                        for sock in sockets:
                            if sock.fileno() < 0:
                                continue
                            sock.settimeout(.2)
                            try:
                                payload = sock.recv(4096)
                                peer.append("eof" if not payload else "buffered_bytes")
                            except (OSError, TimeoutError):
                                peer.append("unavailable")
                        result = dict(case=case, forced=forced, process_exit=proc.returncode,
                                      signal_to_final_observation_ms=round((time.monotonic()-signalled)*1000, 2),
                                      termination="supervisor_sigkill" if forced else
                                          "signal_exit" if proc.returncode < 0 else "process_returned",
                                      graceful_django_cleanup=cleanup, admission_status=admission,
                                      admitted_new_view=new_started, app_close_timeout=timeout_evidence,
                                      before_termination=pre_force, final_snapshot=last,
                                      db_after_exit=db(), peer_outcomes=peer,
                                      samples=len(samples), parent_elapsed_ms=round((time.monotonic()-parent_started)*1000,2))
                        boundary = last.get("shutdown_boundary", {})
                        result["hypothesis"] = ("PASS" if boundary.get("exception_type") == "KeyError"
                            and boundary.get("raise_site_is_original")
                            and boundary.get("raise_details_missing_application") else
                            "REJECTED" if boundary.get("original_returned") else "UNRESOLVED")
                        print("SHUTDOWN_QA " + json.dumps(result), flush=True)
                        assert case != "blocked" or not cleanup, "Never-returning work must not be called graceful"
                        results.append(result)
                    finally:
                        for sock in sockets:
                            sock.close()
                        if proc.poll() is None:
                            proc.kill()
                        proc.wait(timeout=3)
    finally:
        observer.close()
    print("SHUTDOWN_QA_COMPLETE " + json.dumps(dict(cases=len(results))), flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        watchdog = threading.Timer(CHILD_CEILING, lambda: os._exit(124))
        watchdog.daemon = True
        watchdog.start()
        # Leave this armed across interpreter executor joins; normal exit does
        # not wait for a daemon timer. The independent parent normally ends first.
        serve(int(sys.argv[2]), Path(sys.argv[3]))
    else:
        assert sys.argv[1:] in ([], ["--mixed-only"]), "Unknown shutdown QA mode"
        main(mixed_only=sys.argv[1:] == ["--mixed-only"])
