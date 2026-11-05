"""Bounded local PostgreSQL/Daphne cancellation regression (OL-INC-01-A).

Requires DATABASE_URL_TEST for a disposable loopback database named ownlobby_test.
Uses synthetic SQL values, real Django middleware and Channels session middleware.
No production URL, table fixture, dotenv, external cache or provider credential is
used. Raw child logs live in a temporary directory removed on exit. Only aggregate
measurements are printed. --expect-blocked is an explicit old-dependency control;
the normal invocation must meet responsiveness AND cleanup/resource assertions.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
from contextvars import ContextVar
from concurrent.futures import ThreadPoolExecutor
import http.client
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SLOW_SECONDS = 10
CONCURRENCY = 3
REPEATS = 3


def require_local_database():
    value = os.environ.get("DATABASE_URL_TEST", "")
    parsed = urlsplit(value)
    if (parsed.scheme not in {"postgres", "postgresql"}
            or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parsed.path != "/ownlobby_test" or parsed.query or parsed.fragment):
        raise RuntimeError("Requires disposable loopback ownlobby_test; URL overrides forbidden")
    return value


def server(port, folder):
    """Child process: production middleware, synthetic URLs and bounded SQL only."""
    sys.path.insert(0, str(ROOT))
    import dotenv
    dotenv.load_dotenv = lambda *a, **k: False
    dotenv.dotenv_values = lambda *a, **k: {}
    require_local_database()
    original_connect = socket.socket.connect

    def local_connect(sock, address):
        if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
            raise RuntimeError("External sockets forbidden in cancellation QA")
        return original_connect(sock, address)

    socket.socket.connect = local_connect
    import django
    django.setup()
    from django.conf import settings
    from django.db import connection
    from django.http import HttpResponse
    from django.urls import path
    from django.core.asgi import get_asgi_application
    from django.core.signals import request_finished
    from django.db.backends.base.base import BaseDatabaseWrapper
    from django.db.backends.signals import connection_created
    from asgiref.sync import SyncToAsync
    from channels.auth import AuthMiddlewareStack
    from channels.generic.websocket import AsyncWebsocketConsumer
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.security.websocket import AllowedHostsOriginValidator
    from deltacrown.views import healthz
    from deltacrown.middleware.request_memory_probe import _rss_bytes
    from daphne.server import Server

    assert connection.settings_dict["HOST"] in {"localhost", "127.0.0.1", "::1"}
    assert connection.settings_dict["NAME"] == "ownlobby_test"
    settings.DATABASES["default"]["OPTIONS"] = {
        "application_name": "ownlobby_asgi_qa_" + str(os.getpid()),
        "connect_timeout": 3, "options": "-c statement_timeout=15000",
    }
    settings.ROOT_URLCONF = __name__
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
    state = {"started": 0, "finished": 0, "django_started": 0, "ws_open": 0, "loop_lag_ms": 0.0,
             "peak_rss_mib": 0.0, "peak_threads": 0}
    lock = threading.Lock()
    stop = threading.Event()
    request_kind = ContextVar("qa_request_kind", default="other")
    thread_labels = {}
    state["lifecycle"] = []

    def event(name, **details):
        kind = request_kind.get()
        if kind == "other":
            return
        with lock:
            ident = threading.get_ident()
            label = thread_labels.setdefault(ident, "T" + str(len(thread_labels) + 1))
            if len(state["lifecycle"]) < 100:
                state["lifecycle"].append(dict(kind=kind, event=name, thread=label, **details))

    # Observe the original lifecycle; never add a close, GC or signal dispatch.
    original_check = BaseDatabaseWrapper.close_if_unusable_or_obsolete
    original_close = BaseDatabaseWrapper.close

    def observed_check(db):
        event("close_check", open=db.connection is not None, max_age=db.settings_dict["CONN_MAX_AGE"])
        result = original_check(db)
        event("close_check_done", open=db.connection is not None)
        return result

    def observed_close(db):
        event("close", open=db.connection is not None)
        return original_close(db)

    BaseDatabaseWrapper.close_if_unusable_or_obsolete = observed_check
    BaseDatabaseWrapper.close = observed_close
    connection_created.connect(lambda **kw: event("connection_created"), weak=False)
    request_finished.connect(lambda **kw: event("finished_receiver"), weak=False)
    original_finished_asend = request_finished.asend

    async def observed_finished_asend(*a, **kw):
        event("finished_dispatch_enter")
        try:
            result = await original_finished_asend(*a, **kw)
        except asyncio.CancelledError:
            event("finished_dispatch_cancelled")
            raise
        event("finished_dispatch_done")
        return result

    request_finished.asend = observed_finished_asend

    def ordinary(request):
        assert not request.user.is_authenticated
        return HttpResponse("synthetic guest")

    def slow(request):
        with lock:
            state["started"] += 1
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT value, pg_sleep(%s) FROM (VALUES (1)) AS fixture(value)", [SLOW_SECONDS])
                assert cursor.fetchone()[0] == 1
            return ordinary(request)
        finally:
            # Deliberately do not close the connection here: verify Django cleanup.
            with lock:
                state["finished"] += 1
            event("view_finished")

    globals()["urlpatterns"] = [path("healthz/", healthz), path("qa/", ordinary), path("qa/slow/", slow)]
    if os.environ.get("QA_SQL_BOUNDS") == "1":
        from django.db import DatabaseError, transaction
        state["sql_results"] = {}

        def sql_bound(request, operation):
            assert operation in {"statement", "lock"}
            tag = request.META["HTTP_X_QA_KIND"]
            with connection.cursor() as cursor:
                cursor.execute("SHOW statement_timeout")
                original_statement = cursor.fetchone()[0]
                cursor.execute("SHOW lock_timeout")
                original_lock = cursor.fetchone()[0]
            began = None
            try:
                # Explicit synthetic work unit only, not a request-wide policy.
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("SET LOCAL statement_timeout = '3000ms'")
                        cursor.execute("SET LOCAL lock_timeout = '1500ms'")
                        began = time.monotonic()
                        if operation == "statement":
                            cursor.execute("SELECT pg_sleep(8)")
                        else:
                            cursor.execute("SELECT pg_advisory_xact_lock(84643, 312)")
            except DatabaseError as error:
                assert began is not None
                elapsed = (time.monotonic() - began) * 1000
                code = getattr(error.__cause__, "pgcode", None)
                assert code == ("57014" if operation == "statement" else "55P03")
            else:
                raise AssertionError("Synthetic operation did not time out")
            # The atomic block has rolled back before checking recovery/reset.
            assert connection.get_autocommit() and not connection.needs_rollback
            with connection.cursor() as cursor:
                cursor.execute("SHOW statement_timeout")
                assert cursor.fetchone()[0] == original_statement
                cursor.execute("SHOW lock_timeout")
                assert cursor.fetchone()[0] == original_lock
                cursor.execute("SELECT 1")
                assert cursor.fetchone()[0] == 1
            event("sql_timeout", code=code)
            with lock:
                state["sql_results"] = {**state["sql_results"], tag: {
                    "operation": operation, "sqlstate": code, "elapsed_ms": round(elapsed, 2),
                    "limits_restored": True, "connection_reusable": True}}
            return HttpResponse("Synthetic SQL timeout verified")

        urlpatterns.append(path("qa/sql/<str:operation>/", sql_bound))

    class Echo(AsyncWebsocketConsumer):
        async def connect(self):
            assert self.scope["user"].is_anonymous
            state["ws_open"] += 1
            await self.accept()

        async def receive(self, text_data=None, bytes_data=None):
            await self.send(text_data=text_data)

        async def disconnect(self, code):
            state["ws_open"] -= 1

    http_application = get_asgi_application()
    django_application = http_application

    async def counted_http(scope, receive, send):
        with lock:
            state["django_started"] += 1
        await django_application(scope, receive, send)

    http_application = counted_http
    wrapper = None
    if os.environ.get("QA_HTTP_LIFECYCLE_WRAP") == "1":
        from apps.common.asgi_lifecycle import HTTPDisconnectDrain
        capacity = os.environ.get("QA_HTTP_ADMISSION_CAPACITY")
        wrapper = HTTPDisconnectDrain(http_application, capacity=int(capacity) if capacity else None)
        http_application = wrapper
    router = ProtocolTypeRouter({
        "http": http_application,
        "websocket": AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter([path("qa/ws/", Echo.as_asgi())]))),
    })
    if os.environ.get("QA_REAL_ASGI") == "1":
        from scripts.asgi_real_qa import arrange
        router, wrapper = arrange(folder, slow, ordinary, os.environ.get("QA_REAL_LOCKDOWN") == "1")
    heartbeat_task = None

    async def heartbeat():
        previous = time.monotonic()
        while not stop.is_set():
            await asyncio.sleep(.02)
            now = time.monotonic()
            state["loop_lag_ms"] = max(state["loop_lag_ms"], (now - previous - .02) * 1000)
            state["loop_tasks"] = len(asyncio.all_tasks()) - 1  # Exclude this heartbeat.
            previous = now

    async def application(scope, receive, send):
        nonlocal heartbeat_task
        if heartbeat_task is None:
            heartbeat_task = asyncio.create_task(heartbeat())
        kind = "other"
        if scope.get("path") == "/qa/slow/" or scope.get("path", "").startswith("/qa/sql/"):
            kind = dict(scope.get("headers", [])).get(b"x-qa-kind", b"unknown").decode("ascii")
        token = request_kind.set(kind)
        try:
            await router(scope, receive, send)
        except asyncio.CancelledError:
            event("application_cancelled")
            raise
        finally:
            event("application_exit")
            request_kind.reset(token)

    def monitor():
        while not stop.wait(.05):
            if (folder / "stop").exists():
                from twisted.internet import reactor
                reactor.callFromThread(reactor.stop)
                return
            rss = _rss_bytes()
            threads = threading.enumerate()
            with lock:
                state["rss_mib"] = rss / 1048576 if rss is not None else None
                state["peak_rss_mib"] = max(state["peak_rss_mib"], state["rss_mib"] or 0)
                state["peak_threads"] = max(state["peak_threads"], len(threads))
                data = dict(state, thread_ids=[t.ident for t in threads],
                            thread_names={str(t.ident): t.name for t in threads},
                            wrapper_children=wrapper.active_count if wrapper else 0,
                            occupied_slots=wrapper.occupied_count if wrapper else 0,
                            peak_slots=wrapper.peak_occupied if wrapper else 0,
                            rejections=wrapper.rejections if wrapper else 0,
                            wrapper_receives=wrapper.pending_receives if wrapper else 0,
                            outer_cancellations=wrapper.cancellations if wrapper else 0,
                            request_executors=len(SyncToAsync.context_to_thread_executor))
            temporary = folder / "sample.tmp"
            temporary.write_text(json.dumps(data), encoding="utf-8")
            try:
                temporary.replace(folder / "sample.json")
            except PermissionError:
                # Windows readers briefly hold a non-delete-sharing handle.
                # Retry the next sample instead of killing the monitor thread.
                continue

    observer = threading.Thread(target=monitor, name="qa-resource-monitor", daemon=True)
    observer.start()
    (folder / "versions.json").write_text(json.dumps({
        "python": sys.version.split()[0],
        **{name: importlib.metadata.version(name) for name in ("Django", "asgiref", "daphne", "channels", "Twisted")},
    }), encoding="utf-8")
    try:
        Server(application=application, endpoints=[f"tcp:port={port}:interface=127.0.0.1"],
               http_timeout=3600, application_close_timeout=5, verbosity=0).run()
    finally:
        stop.set()
        observer.join(timeout=1)


def main(args):
    database = require_local_database()
    repeats = 1 if args.compare_wrapper or args.admission_prototype else REPEATS
    width = 2 if args.admission_prototype else CONCURRENCY
    import psycopg2
    # Explicitly inspect only this child application's connections in local QA.
    observer = psycopg2.connect(database, connect_timeout=3, options="-c statement_timeout=3000")
    observer.autocommit = True
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
    env = {key: os.environ[key] for key in
           ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA") if key in os.environ}
    env.update(DJANGO_SETTINGS_MODULE="deltacrown.settings_media_qa", DATABASE_URL_TEST=database,
               DATABASE_URL="postgresql://synthetic@127.0.0.1:1/unused_test",
               DJANGO_SECRET_KEY="synthetic-cancellation-qa-only-not-a-production-key-0123456789",
               DISABLE_INPROCESS_MATCH_REMINDER="1", ENABLE_DISCORD_BOT="0", ENABLE_CELERY_BEAT="0",
               COMPETITION_APP_ENABLED="1", SENTRY_DSN="", REDIS_URL="", AWS_EC2_METADATA_DISABLED="true",
               PYTHONUNBUFFERED="1", PYTHONPATH=str(ROOT))
    env["QA_HTTP_LIFECYCLE_WRAP"] = "1" if args.wrapped else "0"
    if args.real_asgi:
        env.update(QA_REAL_ASGI="1", QA_REAL_LOCKDOWN="1" if args.real_lockdown else "0",
                   DJANGO_DEBUG="0")
    if args.admission_prototype or args.sql_bounds:
        env["QA_HTTP_ADMISSION_CAPACITY"] = "2"  # Test fixture only; no production default.
    if args.sql_bounds:
        env["QA_SQL_BOUNDS"] = "1"
    if args.baseline_path:
        assert args.expect_blocked, "A baseline override requires explicit baseline mode"
        env["PYTHONPATH"] = str(Path(args.baseline_path).resolve()) + os.pathsep + str(ROOT)

    def get(path, timeout=2, headers=None):
        started = time.monotonic()
        client = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
        try:
            client.request("GET", path, headers=headers or {})
            response = client.getresponse()
            response.read()
            return {"status": response.status, "cache_control": response.getheader("Cache-Control"),
                    "ms": round((time.monotonic() - started) * 1000, 2)}
        except (TimeoutError, OSError, http.client.HTTPException) as exc:
            return {"error": type(exc).__name__, "ms": round((time.monotonic() - started) * 1000, 2)}
        finally:
            client.close()

    def websocket(real=False, denied=False, invalid_token=False):
        def exact(sock, count):
            data = b""
            while len(data) < count:
                part = sock.recv(count - len(data))
                assert part, "WebSocket closed early"
                data += part
            return data

        def frame(sock, opcode, value):
            mask = b"test"
            sock.sendall(bytes([0x80 | opcode, 0x80 | len(value)]) + mask
                         + bytes(c ^ mask[i % 4] for i, c in enumerate(value)))

        with socket.create_connection(("127.0.0.1", port), timeout=2) as sock:
            key = base64.b64encode(b"0123456789abcdef").decode()
            target = "/ws/homepage/live/" if real else "/qa/ws/"
            if invalid_token:
                target += "?token=synthetic-invalid-token"
            origin = "http://untrusted.invalid" if denied and not args.real_lockdown else "http://localhost"
            sock.sendall((f"GET {target} HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\n"
                          f"Connection: Upgrade\r\nOrigin: {origin}\r\nSec-WebSocket-Version: 13\r\n"
                          f"Sec-WebSocket-Key: {key}\r\n\r\n").encode())
            header = b""
            while not header.endswith(b"\r\n\r\n"):
                assert len(header) < 4096
                header += exact(sock, 1)
            if denied:
                assert header.startswith(b"HTTP/1.1 403"), "Real WebSocket denial failed"
                return
            assert header.startswith(b"HTTP/1.1 101")
            if real:
                head = exact(sock, 2)
                length = head[1] & 127
                if length == 126:
                    length = int.from_bytes(exact(sock, 2), "big")
                elif length == 127:
                    length = int.from_bytes(exact(sock, 8), "big")
                assert length < 65536 and head[0] & 15 == 1
                data = json.loads(exact(sock, length))
                assert data["type"] == ("error" if invalid_token else "live_update")
                if invalid_token:
                    assert data["close_code"] == 4003
                    close = exact(sock, 2)
                    assert close[0] & 15 == 8
                    assert int.from_bytes(exact(sock, close[1] & 127)[:2], "big") == 4003
                    return
                frame(sock, 8, b"\x03\xe8")
                assert exact(sock, 2)[0] & 15 == 8
                return
            frame(sock, 1, b"qa-echo")
            head = exact(sock, 2)
            assert head[0] & 15 == 1 and exact(sock, head[1] & 127) == b"qa-echo"
            frame(sock, 8, b"\x03\xe8")
            assert exact(sock, 2)[0] & 15 == 8

    with tempfile.TemporaryDirectory(prefix="ownlobby-asgi-qa-") as directory:
        folder = Path(directory)
        with (folder / "child.log").open("w", encoding="utf-8") as log:
            proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--serve", str(port), str(folder)],
                                    env=env, stdout=log, stderr=log,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

            def sample():
                return json.loads((folder / "sample.json").read_text(encoding="utf-8"))

            def connections():
                with observer.cursor() as cursor:
                    cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE application_name = %s",
                                   ["ownlobby_asgi_qa_" + str(proc.pid)])
                    return cursor.fetchone()[0]

            def session_states():
                with observer.cursor() as cursor:
                    cursor.execute("SELECT state, wait_event_type, wait_event, count(*) FROM pg_stat_activity "
                                   "WHERE application_name = %s GROUP BY state, wait_event_type, wait_event",
                                   ["ownlobby_asgi_qa_" + str(proc.pid)])
                    return [dict(state=s, wait_type=t, wait=w, count=n) for s, t, w, n in cursor.fetchall()]

            baseline_ids = set()
            round_evidence = {}

            def wait_for(predicate, seconds=8):
                deadline = time.monotonic() + seconds
                while time.monotonic() < deadline:
                    if args.real_asgi and proc.poll() is not None:
                        lines = (folder / "child.log").read_text(encoding="utf-8").splitlines()
                        raise AssertionError("Real QA child exited: " + (lines[-1] if lines else "no diagnostic"))
                    assert proc.poll() is None, "QA child exited unexpectedly"
                    try:
                        if predicate():
                            return
                    except (FileNotFoundError, json.JSONDecodeError):
                        pass
                    time.sleep(.05)
                measured = sample()
                ids = measured.pop("thread_ids", [])
                names = measured.pop("thread_names", {})
                measured["connections"] = connections()
                measured["sessions"] = session_states()
                measured["round"] = round_evidence
                measured["remaining_thread_names"] = [names.get(str(i), "unknown") for i in ids
                                                       if i not in baseline_ids]
                raise AssertionError("Bounded QA condition did not complete: " + json.dumps(measured))

            try:
                wait_for(lambda: get("/healthz/", .3).get("status") == 200, 90 if args.real_asgi else 30)
                versions = json.loads((folder / "versions.json").read_text(encoding="utf-8"))
                assert versions["asgiref"] == ("3.10.0" if args.expect_blocked else "3.12.1")
                assert {k: versions[k] for k in ("Django", "daphne", "channels")} == {
                    "Django": "5.2.18", "daphne": "4.2.3", "channels": "4.3.1"}
                if args.real_asgi:
                    if args.real_lockdown:
                        assert get("/qa/protected/")["status"] == 503
                        assert get("/files/user_profile.kycsubmission/document_front/1/")["status"] == 503
                        assert get("/qa/")["cache_control"] == "no-store"
                        websocket(real=True, denied=True)
                        wait_for(lambda: sample()["wrapper_children"] == 0
                                 and sample()["request_executors"] == 0 and connections() == 0)
                        print("REAL_ASGI_LOCKDOWN health=200 HTTP=503/no-store WS=denied cleanup=zero PASS", flush=True)
                        return
                    sys.path.insert(0, str(ROOT))
                    from scripts.asgi_real_qa import check_http
                    check_http(port, folder)
                    websocket(real=True)
                    websocket(real=True, denied=True)
                    websocket(real=True, invalid_token=True)
                    wait_for(lambda: sample()["request_executors"] == 0 and connections() == 0
                             and sample()["wrapper_children"] == 0 and sample()["wrapper_receives"] == 0)
                    time.sleep(.2)
                    baseline = sample()
                    baseline_ids = set(baseline["thread_ids"])
                    with socket.create_connection(("127.0.0.1", port), timeout=2) as sock:
                        sock.sendall(b"GET /qa/slow/ HTTP/1.1\r\nHost: localhost\r\nX-QA-Kind: real-disconnected\r\n\r\n")
                        wait_for(lambda: sample()["started"] == 1)
                    probes = []
                    until = time.monotonic() + SLOW_SECONDS + .5
                    while time.monotonic() < until:
                        probes.append(get("/healthz/"))
                        time.sleep(.2)
                    wait_for(lambda: sample()["finished"] == 1 and connections() == 0
                             and sample()["request_executors"] == 0 and sample()["wrapper_children"] == 0
                             and sample()["wrapper_receives"] == 0 and sample()["occupied_slots"] == 0
                             and set(sample()["thread_ids"]) <= baseline_ids
                             and sample()["loop_tasks"] <= baseline["loop_tasks"])
                    last = sample()
                    assert last["outer_cancellations"] > 0
                    assert all(p.get("status") == 200 for p in probes)
                    assert last["loop_lag_ms"] < 250 and last["peak_rss_mib"] < 384
                    assert last["rss_mib"] - baseline["rss_mib"] < 32
                    assert any(e["event"] == "finished_dispatch_done" for e in last["lifecycle"])
                    print("REAL_ASGI_QA " + json.dumps(dict(versions=versions, probes=len(probes),
                          health_errors=0, max_health_ms=max(p["ms"] for p in probes),
                          max_loop_lag_ms=round(last["loop_lag_ms"], 2), connections_after=connections(),
                          children_after=last["wrapper_children"], executors_after=last["request_executors"],
                          extra_threads_after=0, extra_loop_tasks_after=0, slots_after=last["occupied_slots"],
                          outer_cancellations=last["outer_cancellations"], baseline_threads=len(baseline_ids),
                          peak_threads=last["peak_threads"], baseline_rss_mib=baseline["rss_mib"],
                          peak_rss_mib=last["peak_rss_mib"])), flush=True)
                    return
                if args.sql_bounds:
                    wait_for(lambda: sample()["request_executors"] == 0 and sample()["occupied_slots"] == 0)
                    time.sleep(.2)
                    baseline = sample()
                    baseline_ids = set(baseline["thread_ids"])
                    rows = []
                    probes = []
                    with ThreadPoolExecutor(max_workers=1) as pool:
                        for operation in ("statement", "lock"):
                            for disconnected in (False, True):
                                tag = "sql-" + operation + ("-disconnected" if disconnected else "-connected")
                                path = "/qa/sql/" + operation + "/"
                                blocker = sock = None
                                try:
                                    if operation == "lock":
                                        blocker = psycopg2.connect(database, connect_timeout=3,
                                            application_name="ownlobby_sql_lock_fixture",
                                            options="-c statement_timeout=5000")
                                        blocker.autocommit = True
                                        with blocker.cursor() as cursor:
                                            cursor.execute("SELECT pg_advisory_lock(84643, 312)")
                                    if disconnected:
                                        sock = socket.create_connection(("127.0.0.1", port), timeout=2)
                                        sock.sendall((f"GET {path} HTTP/1.1\r\nHost: localhost\r\n"
                                                      f"X-QA-Kind: {tag}\r\nConnection: close\r\n\r\n").encode())
                                    else:
                                        response = pool.submit(get, path, 6, {"X-QA-Kind": tag})

                                    observed_wait = []

                                    def executing():
                                        with observer.cursor() as cursor:
                                            cursor.execute("SELECT wait_event_type, wait_event FROM pg_stat_activity "
                                                           "WHERE application_name = %s AND state = 'active'",
                                                           ["ownlobby_asgi_qa_" + str(proc.pid)])
                                            values = cursor.fetchall()
                                        wanted = [(t, w) for t, w in values if
                                                  (w == "PgSleep" if operation == "statement" else t == "Lock")]
                                        if wanted:
                                            observed_wait[:] = wanted[:1]
                                        return bool(wanted)

                                    wait_for(executing)
                                    if sock is not None:
                                        sock.close()  # SQL has demonstrably started before disconnect.
                                    began = time.monotonic()
                                    while tag not in sample()["sql_results"]:
                                        assert time.monotonic() - began < 7
                                        probe = get("/healthz/")
                                        assert probe.get("status") == 200
                                        probes.append(probe)
                                        time.sleep(.1)
                                    if not disconnected:
                                        assert response.result(timeout=6).get("status") == 200
                                    wait_for(lambda: connections() == 0 and sample()["request_executors"] == 0
                                             and sample()["wrapper_children"] == 0 and sample()["wrapper_receives"] == 0
                                             and sample()["occupied_slots"] == 0
                                             and set(sample()["thread_ids"]) <= baseline_ids
                                             and sample().get("loop_tasks", 0) <= baseline.get("loop_tasks", 0))
                                    after = sample()
                                    row = dict(after["sql_results"][tag], disconnected=disconnected)
                                    limit = 3000 if operation == "statement" else 1500
                                    assert limit * .8 <= row["elapsed_ms"] <= limit + 1500
                                    events = [e for e in after["lifecycle"] if e["kind"] == tag]
                                    owners = {e["thread"] for e in events if e["event"] == "connection_created"}
                                    closes = [e for e in events if e["event"] == "close" and e["open"]]
                                    assert len(closes) == 1 and closes[0]["thread"] in owners
                                    assert sum(e["event"] == "finished_receiver" for e in events) == 1
                                    rows.append(dict(row, configured_limit_ms=limit, observed_wait=observed_wait[0],
                                                     owning_thread_closed=True, connections_after=0, executors_after=0,
                                                     children_after=0, slots_after=0, extra_threads_after=0, extra_tasks_after=0))
                                finally:
                                    if sock is not None:
                                        sock.close()
                                    if blocker is not None:
                                        blocker.close()  # Test-only lock holder, never a Django request connection.
                    last = sample()
                    assert last["loop_lag_ms"] < 250 and last["peak_rss_mib"] < 384
                    assert last["rss_mib"] - baseline["rss_mib"] < 32
                    assert last["peak_threads"] <= len(baseline_ids) + 4 * CONCURRENCY + 8
                    print("SQL_BOUNDS_QA " + json.dumps(dict(versions=versions, cases=rows, health_probes=len(probes),
                          max_health_ms=max(p["ms"] for p in probes), max_loop_lag_ms=round(last["loop_lag_ms"], 2),
                          baseline_threads=len(baseline_ids), peak_threads=last["peak_threads"],
                          baseline_rss_mib=baseline["rss_mib"], peak_rss_mib=last["peak_rss_mib"])), flush=True)
                    return
                sequential = [get("/qa/") for _ in range(6)]
                with ThreadPoolExecutor(max_workers=width) as pool:
                    concurrent = list(pool.map(get, ["/qa/"] * width))
                assert all(r.get("status") == 200 for r in sequential + concurrent)
                websocket()
                wait_for(lambda: sample()["ws_open"] == 0 and sample()["request_executors"] == 0)
                time.sleep(.2)
                baseline = sample()
                baseline_ids = set(baseline["thread_ids"])
                rounds = []
                for number in range(repeats + 1):
                    disconnect = number > 0
                    before = sample()["started"]
                    sockets = []
                    held_during_cancellation = False
                    try:
                        for _ in range(width):
                            sock = socket.create_connection(("127.0.0.1", port), timeout=2)
                            sockets.append(sock)
                            kind = "disconnected" if disconnect else "connected"
                            sock.sendall(("GET /qa/slow/ HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n"
                                          f"X-QA-Kind: {kind}\r\n\r\n").encode())
                        wait_for(lambda: sample()["started"] == before + width)

                        def reject_without_django():
                            prior = sample()["django_started"]
                            response = get("/qa/slow/")
                            assert response["status"] == 503 and response["cache_control"] == "no-store"
                            time.sleep(.1)  # Allow the independent snapshot monitor to observe any bad admission.
                            assert sample()["django_started"] == prior
                            assert sample()["occupied_slots"] == width
                            return response

                        if args.admission_prototype:
                            reject_without_django()
                        cancellations_before = sample()["outer_cancellations"]
                        if disconnect:
                            for sock in sockets:
                                sock.close()
                        began = time.monotonic()
                        probes = []
                        while time.monotonic() - began < SLOW_SECONDS + .5:
                            probes.append(get("/healthz/"))
                            if (args.admission_prototype and disconnect and not held_during_cancellation
                                    and sample()["outer_cancellations"] >= cancellations_before + 2 * width
                                    and sample()["finished"] == before):
                                reject_without_django()
                                held_during_cancellation = True
                            time.sleep(.2)
                    finally:
                        for sock in sockets:
                            sock.close()
                    round_evidence = {"disconnected": disconnect,
                                      "health_timeouts": sum(p.get("error") == "TimeoutError" for p in probes),
                                      "unexpected_health_results": sum(p.get("status") != 200
                                          and p.get("error") != "TimeoutError" for p in probes)}
                    wait_for(lambda: sample()["finished"] == before + width)
                    wait_for(lambda: sample()["request_executors"] == 0
                             and set(sample()["thread_ids"]) <= baseline_ids and connections() == 0
                             and sample()["wrapper_children"] == 0 and sample()["wrapper_receives"] == 0
                             and sample()["occupied_slots"] == 0
                             and sample().get("loop_tasks", 0) <= baseline.get("loop_tasks", 0))
                    after = sample()
                    if args.admission_prototype:
                        assert not disconnect or held_during_cancellation
                        assert all(p.get("cache_control") == "no-store" for p in probes if p.get("status") == 503)
                        failures = sum(p.get("status") not in {200, 503} for p in probes)
                        assert any(p.get("status") == 503 for p in probes)
                    else:
                        failures = sum(p.get("status") != 200 for p in probes)
                    if not disconnect or not args.expect_blocked:
                        assert failures == 0, "Unrelated health request lost responsiveness"
                    else:
                        assert failures > 0, "Baseline control failed to demonstrate the old stall"
                    rounds.append({"disconnect": disconnect, "probes": len(probes), "timeouts_or_errors": failures,
                                   "max_health_ms": max(p["ms"] for p in probes), "rss_after_mib": after["rss_mib"],
                                   "extra_threads_after": len(set(after["thread_ids"]) - baseline_ids),
                                   "executors_after": after["request_executors"], "connections_after": connections(),
                                   "slots_after": after["occupied_slots"],
                                   "busy_health_responses": sum(p.get("status") == 503 for p in probes),
                                   "held_during_cancellation": held_during_cancellation,
                                   "children_after": after["wrapper_children"], "receives_after": after["wrapper_receives"],
                                   "extra_loop_tasks_after": max(0, after.get("loop_tasks", 0) - baseline.get("loop_tasks", 0))})
                websocket()
                wait_for(lambda: sample()["ws_open"] == 0 and sample()["request_executors"] == 0)
                last = sample()
                assert last["loop_lag_ms"] > 250 if args.expect_blocked else last["loop_lag_ms"] < 250
                assert last["peak_threads"] <= len(baseline_ids) + 4 * CONCURRENCY + 8
                if args.wrapped:
                    assert last["outer_cancellations"] >= 2 * width * repeats
                if args.admission_prototype:
                    assert last["peak_slots"] == 2 and get("/healthz/")["status"] == 200
                if sys.platform.startswith("linux"):
                    assert last["rss_mib"] is not None
                    assert last["peak_rss_mib"] < 384
                    assert max(r["rss_after_mib"] for r in rounds) - baseline["rss_mib"] < 32
                result = {"versions": versions, "wrapped": args.wrapped,
                          "outer_cancellations": last["outer_cancellations"], "expected_baseline_stall": args.expect_blocked,
                          "capacity": 2 if args.admission_prototype else None, "peak_slots": last["peak_slots"],
                          "rejections": last["rejections"],
                          "sequential_requests": len(sequential), "concurrent_requests": len(concurrent),
                          "slow_concurrency": width, "rounds": rounds, "websocket_cycles": 2,
                          "max_loop_lag_ms": round(last["loop_lag_ms"], 2), "baseline_threads": len(baseline_ids),
                          "peak_threads": last["peak_threads"], "baseline_rss_mib": baseline["rss_mib"],
                          "peak_rss_mib": last["peak_rss_mib"] if last["rss_mib"] is not None else None}
                print("ASGI_CANCELLATION_QA " + json.dumps(result, sort_keys=True), flush=True)
                return result
            finally:
                # Let the real interpreter exit, including Windows venv launchers.
                (folder / "stop").touch()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if os.name == "nt":
                        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                                       capture_output=True, timeout=5, check=True)
                    else:
                        proc.kill()
                    proc.wait(timeout=5)
                observer.close()


async def check_admission_contract():
    """C=2 is a deterministic fixture, never a production sizing recommendation."""
    sys.path.insert(0, str(ROOT))
    from apps.common.asgi_lifecycle import HTTPDisconnectDrain
    initial_tasks = set(asyncio.all_tasks())
    streaming = asyncio.Event()
    stream_release = asyncio.Event()
    cleaning = asyncio.Event()
    cleanup_release = asyncio.Event()
    starts = streams = cleanups = 0
    reads = [0] * 6
    responses = [[] for _ in range(6)]

    async def app(scope, receive, send):
        nonlocal starts, streams, cleanups
        starts += 1
        assert (await receive())["type"] == "http.request"
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"chunk", "more_body": True})
        streams += 1
        if streams == 2:
            streaming.set()
        await stream_release.wait()
        assert (await receive())["type"] == "http.disconnect"
        cleanups += 1
        if cleanups == 2:
            cleaning.set()
        await cleanup_release.wait()

    wrapper = HTTPDisconnectDrain(app, capacity=2)

    async def call(index):
        async def receive():
            assert index not in {2, 3}, "Rejected request body was read"
            reads[index] += 1
            return {"type": "http.request" if reads[index] == 1 else "http.disconnect"}

        async def send(message):
            responses[index].append(message)

        await wrapper({"type": "http"}, receive, send)

    def rejected(index):
        assert responses[index][0]["status"] == 503
        assert (b"cache-control", b"no-store") in responses[index][0]["headers"]
        assert reads[index] == 0 and starts == 2

    admissions = [asyncio.create_task(call(i)) for i in range(3)]
    try:
        await asyncio.wait_for(streaming.wait(), timeout=1)
        await asyncio.wait_for(asyncio.shield(admissions[2]), timeout=.5)
        rejected(2)
        assert wrapper.occupied_count == wrapper.active_count == 2
        for _ in range(3):
            admissions[0].cancel()
            admissions[1].cancel()
            await asyncio.sleep(0)
        assert wrapper.occupied_count == 2  # Still streaming, despite outer cancellation.
        stream_release.set()
        await asyncio.wait_for(cleaning.wait(), timeout=1)
        await asyncio.wait_for(call(3), timeout=.5)
        rejected(3)
        assert wrapper.occupied_count == wrapper.active_count == 2
    finally:
        stream_release.set()
        cleanup_release.set()
        for task in admissions:
            if not task.done():
                task.cancel()
        await asyncio.wait_for(asyncio.gather(*admissions, return_exceptions=True), timeout=1)
    assert wrapper.occupied_count == wrapper.active_count == wrapper.pending_receives == 0
    await asyncio.wait_for(asyncio.gather(call(4), call(5)), timeout=1)
    assert starts == 4 and wrapper.rejections == 2 and wrapper.peak_occupied == 2
    assert wrapper.occupied_count == wrapper.active_count == wrapper.pending_receives == 0
    assert set(asyncio.all_tasks()) <= initial_tasks
    print("ADMISSION_CONTRACT C=2 simultaneous/503-before-body/streaming/cancel-cleanup/reuse PASS", flush=True)


async def check_wrapper_contract():
    """Finite synthetic checks, including evidence of indefinite-retention risk."""
    sys.path.insert(0, str(ROOT))
    from apps.common.asgi_lifecycle import HTTPDisconnectDrain
    initial = set(asyncio.all_tasks())
    release = asyncio.Event()
    seen_disconnect = asyncio.Event()
    calls = 0

    async def receive():
        nonlocal calls
        calls += 1
        await asyncio.Event().wait()  # Cancelled/retrieved by the receive adapter.

    async def send(message):
        pass

    async def application(scope, receive, send):
        assert (await receive())["type"] == "http.disconnect"
        seen_disconnect.set()
        await release.wait()

    wrapper = HTTPDisconnectDrain(application)
    outer = asyncio.create_task(wrapper({"type": "http"}, receive, send))
    try:
        await asyncio.sleep(0)
        for _ in range(3):
            outer.cancel()
            await asyncio.sleep(0)
        await asyncio.wait_for(seen_disconnect.wait(), timeout=1)
        done, _ = await asyncio.wait({outer}, timeout=.05)
        assert not done and wrapper.active_count == 1
        print("WRAPPER_RETENTION_RISK pending work retains its lifecycle after cancellation", flush=True)
    finally:
        release.set()
        try:
            await asyncio.wait_for(asyncio.shield(outer), timeout=1)
        except asyncio.CancelledError:
            pass
    assert outer.cancelled() and wrapper.active_count == 0 and wrapper.pending_receives == 0
    assert calls <= 1

    marker = {"type": "http.disconnect"}

    async def real_disconnect():
        return marker

    async def real_application(scope, receive, send):
        assert await receive() is marker

    await HTTPDisconnectDrain(real_application)({"type": "http"}, real_disconnect, send)

    async def failure(scope, receive, send):
        await receive()
        raise ValueError("synthetic child failure")

    failed = asyncio.create_task(HTTPDisconnectDrain(failure)({"type": "http"}, receive, send))
    await asyncio.sleep(0)
    failed.cancel()
    done, _ = await asyncio.wait({failed}, timeout=1)
    assert failed in done
    try:
        failed.result()
    except asyncio.CancelledError as error:
        assert isinstance(error.__cause__, ValueError)
    else:
        raise AssertionError("Outer cancellation was not propagated")
    assert set(asyncio.all_tasks()) <= initial
    print("WRAPPER_CONTRACT real-disconnect/repeated-cancel/exception/task-cleanup PASS", flush=True)


def baseline_control(args):
    """Accept only the independently reproduced old-dependency failure profile."""
    assert args.expect_blocked and args.baseline_path
    assert not args.wrapped and not args.compare_wrapper and not args.admission_prototype and not args.sql_bounds
    try:
        main(args)
    except AssertionError as error:
        prefix = "Bounded QA condition did not complete: "
        assert str(error).startswith(prefix), str(error)
        evidence = json.loads(str(error)[len(prefix):])
        assert evidence["started"] == evidence["finished"] == 2 * CONCURRENCY
        assert evidence["connections"] == CONCURRENCY and evidence["request_executors"] == 0
        assert evidence["sessions"] == [{"state": "idle", "wait_type": "Client",
                                         "wait": "ClientRead", "count": CONCURRENCY}]
        assert not evidence["remaining_thread_names"]
        assert evidence["loop_lag_ms"] > 250
        assert evidence["round"]["disconnected"] and evidence["round"]["health_timeouts"] > 0
        assert evidence["round"]["unexpected_health_results"] == 0
        print("BASELINE_EXPECTED_FAILURE " + json.dumps({key: evidence[key] for key in
              ("connections", "sessions", "finished", "request_executors", "loop_lag_ms", "round")}), flush=True)
    else:
        raise AssertionError("Expected asgiref 3.10.0 failure was not reproduced")


def compare_wrapper(args):
    asyncio.run(check_wrapper_contract())
    assert not args.expect_blocked and not args.baseline_path
    args.wrapped = False
    try:
        main(args)
    except AssertionError as error:
        prefix = "Bounded QA condition did not complete: "
        assert str(error).startswith(prefix), str(error)
        evidence = json.loads(str(error)[len(prefix):])
        assert evidence["started"] == evidence["finished"] == 2 * CONCURRENCY
        assert evidence["connections"] == CONCURRENCY and evidence["request_executors"] == 0
        assert not evidence["remaining_thread_names"]
        print("UNWRAPPED_CLEANUP_CONTROL " + json.dumps({key: evidence[key] for key in
              ("connections", "sessions", "finished", "request_executors", "peak_threads", "peak_rss_mib", "loop_lag_ms")}), flush=True)
    else:
        raise AssertionError("Unwrapped cleanup failure was not reproduced")
    args.wrapped = True
    main(args)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        # Hard process lifetime also bounds unexpected event-loop/worker failures.
        watchdog = threading.Timer(120, lambda: os._exit(124))
        watchdog.daemon = True
        watchdog.start()
        try:
            server(int(sys.argv[2]), Path(sys.argv[3]))
        finally:
            watchdog.cancel()
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--expect-blocked", action="store_true")
        parser.add_argument("--baseline-path")
        parser.add_argument("--wrapped", action="store_true")
        parser.add_argument("--compare-wrapper", action="store_true")
        parser.add_argument("--admission-prototype", action="store_true")
        parser.add_argument("--sql-bounds", action="store_true")
        parser.add_argument("--real-asgi", action="store_true")
        args = parser.parse_args()
        args.real_lockdown = False
        if args.real_asgi:
            assert not any((args.expect_blocked, args.baseline_path, args.compare_wrapper,
                            args.admission_prototype, args.sql_bounds))
            args.wrapped = True
            main(args)
            args.real_lockdown = True
            main(args)
        elif args.expect_blocked:
            baseline_control(args)
        elif args.sql_bounds:
            assert not args.compare_wrapper and not args.expect_blocked and not args.baseline_path and not args.admission_prototype
            args.wrapped = True
            main(args)
        elif args.admission_prototype:
            assert not args.compare_wrapper and not args.expect_blocked and not args.baseline_path
            asyncio.run(check_admission_contract())
            args.wrapped = True
            main(args)
        else:
            compare_wrapper(args) if args.compare_wrapper else main(args)
