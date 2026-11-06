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
events = []
observations = []
phases = []
began = time.monotonic()
work_thread = None
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
    with mutex:
        if not phases or phases[-1]["phase"] != runtime.phase:
            phases.append(dict(phase=runtime.phase, elapsed_ms=round((time.monotonic()-began)*1000,2)))
        value = dict(phase=runtime.phase, events=list(events), children=runtime.http.active_count if runtime.http else 0,
                     slots=runtime.http.occupied_count if runtime.http else 0,
                     executors=len(SyncToAsync.context_to_thread_executor),
                     terminal_observations=list(observations), phase_observations=list(phases))
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(json.dumps(value), encoding="utf-8")
        temporary.replace(destination)


def finished(**kwargs):
    emit("django_closed" if connection.connection is None else "django_open",
         db_closed=connection.connection is None,
         owning_thread=threading.get_ident()==work_thread if tag.get()=="/work/" else None)


request_finished.connect(finished, weak=False)


def health(request):
    return HttpResponse("synthetic")


def work(request):
    global work_thread
    work_thread = threading.get_ident()
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
    while True:
        snapshot()
        await asyncio.sleep(.02)


async def application(scope, receive, send):
    global heartbeat
    if heartbeat is None:
        heartbeat = asyncio.create_task(monitor())
    token = tag.set(scope["path"])
    try:
        await router(scope, receive, send)
    finally:
        tag.reset(token)


atexit.register(snapshot)
