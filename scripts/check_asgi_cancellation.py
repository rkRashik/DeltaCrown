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

    router = ProtocolTypeRouter({
        "http": get_asgi_application(),
        "websocket": AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter([path("qa/ws/", Echo.as_asgi())]))),
    })
    heartbeat_task = None

    async def heartbeat():
        previous = time.monotonic()
        while not stop.is_set():
            await asyncio.sleep(.02)
            now = time.monotonic()
            state["loop_lag_ms"] = max(state["loop_lag_ms"], (now - previous - .02) * 1000)
            previous = now

    async def application(scope, receive, send):
        nonlocal heartbeat_task
        if heartbeat_task is None:
            heartbeat_task = asyncio.create_task(heartbeat())
        await router(scope, receive, send)

    def monitor():
        while not stop.wait(.05):
            rss = _rss_bytes()
            threads = threading.enumerate()
            with lock:
                state["rss_mib"] = rss / 1048576 if rss is not None else None
                state["peak_rss_mib"] = max(state["peak_rss_mib"], state["rss_mib"] or 0)
                state["peak_threads"] = max(state["peak_threads"], len(threads))
                data = dict(state, thread_ids=[t.ident for t in threads],
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
                measured.pop("thread_ids", None)
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
                for number in range(REPEATS + 1):
                    disconnect = number > 0
                    before = sample()["started"]
                    sockets = []
                    try:
                        for _ in range(CONCURRENCY):
                            sock = socket.create_connection(("127.0.0.1", port), timeout=2)
                            sockets.append(sock)
                            sock.sendall(b"GET /qa/slow/ HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
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
                             and set(sample()["thread_ids"]) <= baseline_ids and connections() == 0)
                    after = sample()
                    failures = sum(p.get("status") != 200 for p in probes)
                    if not disconnect or not args.expect_blocked:
                        assert failures == 0, "Unrelated health request lost responsiveness"
                    else:
                        assert failures > 0, "Baseline control failed to demonstrate the old stall"
                    rounds.append({"disconnect": disconnect, "probes": len(probes), "timeouts_or_errors": failures,
                                   "max_health_ms": max(p["ms"] for p in probes), "rss_after_mib": after["rss_mib"],
                                   "extra_threads_after": len(set(after["thread_ids"]) - baseline_ids),
                                   "executors_after": after["request_executors"], "connections_after": connections()})
                websocket()
                wait_for(lambda: sample()["ws_open"] == 0 and sample()["request_executors"] == 0)
                last = sample()
                assert last["loop_lag_ms"] > 250 if args.expect_blocked else last["loop_lag_ms"] < 250
                assert last["peak_threads"] <= len(baseline_ids) + 4 * CONCURRENCY + 8
                if sys.platform.startswith("linux"):
                    assert last["rss_mib"] is not None
                    assert last["peak_rss_mib"] < 384
                    assert max(r["rss_after_mib"] for r in rounds) - baseline["rss_mib"] < 32
                result = {"versions": versions, "expected_baseline_stall": args.expect_blocked,
                          "sequential_requests": len(sequential), "concurrent_requests": len(concurrent),
                          "slow_concurrency": CONCURRENCY, "rounds": rounds, "websocket_cycles": 2,
                          "max_loop_lag_ms": round(last["loop_lag_ms"], 2), "baseline_threads": len(baseline_ids),
                          "peak_threads": last["peak_threads"], "baseline_rss_mib": baseline["rss_mib"],
                          "peak_rss_mib": last["peak_rss_mib"] if last["rss_mib"] is not None else None}
                print("ASGI_CANCELLATION_QA " + json.dumps(result, sort_keys=True), flush=True)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
                observer.close()


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
        main(parser.parse_args())
