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
    state = {"started": 0, "finished": 0, "ws_open": 0, "loop_lag_ms": 0.0,
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
    wrapper = None
    if os.environ.get("QA_HTTP_LIFECYCLE_WRAP") == "1":
        from apps.common.asgi_lifecycle import HTTPDisconnectDrain
        wrapper = HTTPDisconnectDrain(http_application)
        http_application = wrapper
    router = ProtocolTypeRouter({
        "http": http_application,
        "websocket": AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter([path("qa/ws/", Echo.as_asgi())]))),
    })
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
        if scope.get("path") == "/qa/slow/":
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
    repeats = 1 if args.compare_wrapper else REPEATS
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
    if args.baseline_path:
        assert args.expect_blocked, "A baseline override requires explicit baseline mode"
        env["PYTHONPATH"] = str(Path(args.baseline_path).resolve()) + os.pathsep + str(ROOT)

    def get(path, timeout=2):
        started = time.monotonic()
        client = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
        try:
            client.request("GET", path)
            response = client.getresponse()
            response.read()
            return {"status": response.status, "ms": round((time.monotonic() - started) * 1000, 2)}
        except (TimeoutError, OSError, http.client.HTTPException) as exc:
            return {"error": type(exc).__name__, "ms": round((time.monotonic() - started) * 1000, 2)}
        finally:
            client.close()

    def websocket():
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
            sock.sendall(("GET /qa/ws/ HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\n"
                          "Connection: Upgrade\r\nOrigin: http://localhost\r\nSec-WebSocket-Version: 13\r\n"
                          f"Sec-WebSocket-Key: {key}\r\n\r\n").encode())
            header = b""
            while not header.endswith(b"\r\n\r\n"):
                assert len(header) < 4096
                header += exact(sock, 1)
            assert header.startswith(b"HTTP/1.1 101")
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

            def wait_for(predicate, seconds=8):
                deadline = time.monotonic() + seconds
                while time.monotonic() < deadline:
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
                measured["remaining_thread_names"] = [names.get(str(i), "unknown") for i in ids
                                                       if i not in baseline_ids]
                raise AssertionError("Bounded QA condition did not complete: " + json.dumps(measured))

            try:
                wait_for(lambda: get("/healthz/", .3).get("status") == 200, 30)
                versions = json.loads((folder / "versions.json").read_text(encoding="utf-8"))
                assert versions["asgiref"] == ("3.10.0" if args.expect_blocked else "3.12.1")
                assert {k: versions[k] for k in ("Django", "daphne", "channels")} == {
                    "Django": "5.2.18", "daphne": "4.2.3", "channels": "4.3.1"}
                sequential = [get("/qa/") for _ in range(6)]
                with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
                    concurrent = list(pool.map(get, ["/qa/"] * CONCURRENCY))
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
                    try:
                        for _ in range(CONCURRENCY):
                            sock = socket.create_connection(("127.0.0.1", port), timeout=2)
                            sockets.append(sock)
                            kind = "disconnected" if disconnect else "connected"
                            sock.sendall(("GET /qa/slow/ HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n"
                                          f"X-QA-Kind: {kind}\r\n\r\n").encode())
                        wait_for(lambda: sample()["started"] == before + CONCURRENCY)
                        if disconnect:
                            for sock in sockets:
                                sock.close()
                        began = time.monotonic()
                        probes = []
                        while time.monotonic() - began < SLOW_SECONDS + .5:
                            probes.append(get("/healthz/"))
                            time.sleep(.2)
                    finally:
                        for sock in sockets:
                            sock.close()
                    wait_for(lambda: sample()["finished"] == before + CONCURRENCY)
                    wait_for(lambda: sample()["request_executors"] == 0
                             and set(sample()["thread_ids"]) <= baseline_ids and connections() == 0
                             and sample()["wrapper_children"] == 0 and sample()["wrapper_receives"] == 0
                             and sample().get("loop_tasks", 0) <= baseline.get("loop_tasks", 0))
                    after = sample()
                    failures = sum(p.get("status") != 200 for p in probes)
                    if not disconnect or not args.expect_blocked:
                        assert failures == 0, "Unrelated health request lost responsiveness"
                    else:
                        assert failures > 0, "Baseline control failed to demonstrate the old stall"
                    rounds.append({"disconnect": disconnect, "probes": len(probes), "timeouts_or_errors": failures,
                                   "max_health_ms": max(p["ms"] for p in probes), "rss_after_mib": after["rss_mib"],
                                   "extra_threads_after": len(set(after["thread_ids"]) - baseline_ids),
                                   "executors_after": after["request_executors"], "connections_after": connections(),
                                   "children_after": after["wrapper_children"], "receives_after": after["wrapper_receives"],
                                   "extra_loop_tasks_after": max(0, after.get("loop_tasks", 0) - baseline.get("loop_tasks", 0))})
                websocket()
                wait_for(lambda: sample()["ws_open"] == 0 and sample()["request_executors"] == 0)
                last = sample()
                assert last["loop_lag_ms"] > 250 if args.expect_blocked else last["loop_lag_ms"] < 250
                assert last["peak_threads"] <= len(baseline_ids) + 4 * CONCURRENCY + 8
                if args.wrapped:
                    assert last["outer_cancellations"] >= 2 * CONCURRENCY * repeats
                if sys.platform.startswith("linux"):
                    assert last["rss_mib"] is not None
                    assert last["peak_rss_mib"] < 384
                    assert max(r["rss_after_mib"] for r in rounds) - baseline["rss_mib"] < 32
                result = {"versions": versions, "wrapped": args.wrapped,
                          "outer_cancellations": last["outer_cancellations"], "expected_baseline_stall": args.expect_blocked,
                          "sequential_requests": len(sequential), "concurrent_requests": len(concurrent),
                          "slow_concurrency": CONCURRENCY, "rounds": rounds, "websocket_cycles": 2,
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
        args = parser.parse_args()
        compare_wrapper(args) if args.compare_wrapper else main(args)
