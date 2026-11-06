"""Compact loopback-only A10 process fixture. No migrations or application rows."""
import atexit
import asyncio
from contextvars import ContextVar
import json
import os
from pathlib import Path
import socket
import threading
import time
import resource

import dotenv
dotenv.load_dotenv = lambda *a, **k: False
dotenv.dotenv_values = lambda *a, **k: {}
from urllib.parse import urlsplit
url = urlsplit(os.environ.get("DATABASE_URL_TEST", ""))
assert url.hostname == "127.0.0.1" and url.path == "/ownlobby_test" and not url.query
original_connect = socket.socket.connect


def local_connect(sock, address):
    if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
        raise RuntimeError("External connection forbidden in A10 QA")
    return original_connect(sock, address)


socket.socket.connect = local_connect
watchdog = threading.Timer(15, lambda: os._exit(124))  # QA-only, remains armed during executor exit joins.
watchdog.daemon = True
watchdog.start()

import django
django.setup()
from django.conf import settings
from django.core.asgi import get_asgi_application
from django.core.signals import request_finished
from django.db import connection
from django.http import HttpResponse, StreamingHttpResponse
from django.urls import path
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.routing import ProtocolTypeRouter, URLRouter
from asgiref.sync import SyncToAsync
from apps.common.asgi_lifecycle import require_runtime

assert connection.settings_dict["NAME"] == "ownlobby_test" and connection.settings_dict["HOST"] == "127.0.0.1"
connection.settings_dict["OPTIONS"] = dict(application_name="ownlobby_a10_" + str(os.getpid()), connect_timeout=2)
settings.ROOT_URLCONF = __name__
runtime = require_runtime(settings.OWNLOBBY_ASGI_LIFECYCLE)
runtime.configure_websocket_capacity(int(os.environ["A11_QA_WS_CAPACITY"]))
stall_after = float(os.environ["A11_QA_STALL_SECONDS"])
lag_threshold = float(os.environ["A11_QA_LAG_SECONDS"])
events = []
observations = []
phases = []
began = time.monotonic()
work_threads = set()
observed_server = None
loop_lag = peak_loop_lag = 0.0
ticks = peak_threads = peak_os_threads = 0
signals_seen = set()
qa_loop = None
tag = ContextVar("a10_request", default="process")
mutex = threading.RLock()
destination = Path(os.environ["A10_QA_STATE"])


def emit(name, **facts):
    with mutex:
        events.append(dict(event=name, kind=tag.get()))
        observations.append(dict(event=name, kind=tag.get(), phase=runtime.phase,
                                 elapsed_ms=round((time.monotonic()-began)*1000,2), **facts))
        snapshot()


def snapshot():
    global peak_threads, peak_os_threads
    with mutex:
        peak_threads = max(peak_threads, threading.active_count())
        os_threads = next(int(line.split()[1]) for line in Path('/proc/self/status').read_text().splitlines()
                          if line.startswith('Threads:'))
        peak_os_threads = max(peak_os_threads, os_threads)
        occupancy = runtime.observe(stall_after=stall_after, lag_threshold=lag_threshold, loop_lag=loop_lag)
        signals_seen.add(occupancy['signal'])
        if not phases or phases[-1]["phase"] != runtime.phase:
            phases.append(dict(phase=runtime.phase, elapsed_ms=round((time.monotonic()-began)*1000,2)))
        value = dict(phase=runtime.phase, events=list(events), children=runtime.http.active_count if runtime.http else 0,
                     slots=runtime.http.occupied_count if runtime.http else 0,
                     executors=len(SyncToAsync.context_to_thread_executor),
                     terminal_observations=list(observations), phase_observations=list(phases),
                     occupancy=occupancy, signals_seen=sorted(signals_seen), loop_ticks=ticks,
                     peak_loop_lag_seconds=peak_loop_lag, rss_peak_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                     peak_python_threads=peak_threads, peak_os_threads=peak_os_threads,
                     owned_tasks=sum(not task.done() and task.get_name().startswith('ownlobby-')
                                     for task in asyncio.all_tasks(qa_loop)) if qa_loop else 0,
                     ws_protocol_records=len(observed_server.websocket_protocols) if observed_server else 0,
                     ws_protocol_bindings=len(runtime._websocket_closures),
                     application_tasks=sum(not task.done() for task in observed_server.application_tasks)
                         if observed_server else 0,
                     websocket_protocols=[dict(close_requested=record.close_requested,
                         protocol_closed=record.closed.done(),
                         protocol_outcome=record.closed.result() if record.closed.done() else None,
                         application_finished=record.application.done(),
                         application_cancelled=record.application.cancelled())
                         for record in observed_server._shutdown_protocols] if observed_server else [],
                     websocket_sessions=[dict(close_requested=session.close_requested,
                         disconnect_received=session.disconnect_received,
                         application_finished=session.application_finished, failed=session.failed)
                         for session in observed_server._shutdown_websockets] if observed_server else [])
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(json.dumps(value), encoding="utf-8")
        temporary.replace(destination)


def finished(**kwargs):
    emit("django_closed" if connection.connection is None else "django_open",
         db_closed=connection.connection is None,
         owning_thread=threading.get_ident() in work_threads if tag.get()=="/work/" else None)


request_finished.connect(finished, weak=False)


def health(request):
    return HttpResponse("synthetic")


def work(request):
    work_threads.add(threading.get_ident())
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        emit("work_started")
        if os.environ["A10_QA_CASE"] == "blocked":
            threading.Event().wait()
        else:
            cursor.execute("SELECT pg_sleep(2)")
    emit("work_finished")
    return HttpResponse("finite")


def stream(request):
    async def chunks():
        try:
            emit("stream_started")
            yield b"synthetic-stream"
            await asyncio.sleep(60)
        finally:
            emit("stream_finalized")
    response = StreamingHttpResponse(chunks())
    response._resource_closers.append(lambda: emit("stream_closed"))
    return response


class Socket(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        emit("ws_connected")

    async def disconnect(self, code):
        emit("ws_disconnect_observed", code=code)
        emit("ws_closed_1012" if code == 1012 else "ws_other_close")


urlpatterns = [path("healthz/", health), path("work/", work), path("stream/", stream)]
http, ws = runtime.attach(get_asgi_application(), URLRouter([path("ws/", Socket.as_asgi())]))
router = ProtocolTypeRouter({"http": http, "websocket": ws})
heartbeat = None


async def monitor():
    global loop_lag, peak_loop_lag, ticks
    previous = asyncio.get_running_loop().time()
    while True:
        now = asyncio.get_running_loop().time()
        loop_lag = max(0, now-previous-.02)
        peak_loop_lag = max(peak_loop_lag, loop_lag)
        previous = now
        ticks += 1
        snapshot()
        await asyncio.sleep(.02)


async def application(scope, receive, send):
    global heartbeat, observed_server, qa_loop
    observed_server = send.func.__self__  # QA-only reference to the real adapter.
    qa_loop = asyncio.get_running_loop()
    if heartbeat is None:
        heartbeat = asyncio.create_task(monitor())
        if os.environ["A10_QA_CASE"] == "saturation":
            # Finite QA-only loop pause; observer records lag on resumption.
            asyncio.get_running_loop().call_later(.7, time.sleep, .15)
    token = tag.set(scope["path"])
    try:
        await router(scope, receive, send)
        if scope["type"] == "websocket":
            emit("ws_application_returned")
    finally:
        tag.reset(token)


atexit.register(snapshot)
