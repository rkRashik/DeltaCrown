"""Pinned-library I/O contracts. Loopback/synthetic only; no migrations."""
import asyncio
from datetime import timedelta
from importlib.metadata import version
import json
import os
import socket
import smtplib
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

from io_loopback import Loopback, blackhole, redis_replies, relay
from apps.common.io_bounds import transaction_timeouts, redis_socket_options, channels_redis_host, s3_socket_config


def setup_django():
    from django.conf import settings
    if settings.configured:
        return
    database = {"ENGINE":"django.db.backends.dummy"}
    if os.environ.get("DATABASE_URL_TEST"):
        url = urlsplit(os.environ["DATABASE_URL_TEST"])
        assert (url.hostname, url.path, url.query) == ("127.0.0.1", "/ownlobby_test", "")
        database = dict(ENGINE="django.db.backends.postgresql", NAME="ownlobby_test", HOST="127.0.0.1",
                        PORT=url.port, USER=url.username, PASSWORD=url.password, CONN_MAX_AGE=0,
                        OPTIONS=dict(connect_timeout=2, application_name="ownlobby_io_"+str(os.getpid()),
                                     options="-c statement_timeout=3000 -c lock_timeout=1000"))
    settings.configure(SECRET_KEY="synthetic-io-qa-only-key", INSTALLED_APPS=["django.contrib.sessions"],
                       DATABASES={"default":database}, USE_TZ=True, SESSION_CACHE_ALIAS="default",
                       CACHES={"default":{"BACKEND":"django.core.cache.backends.locmem.LocMemCache"}})
    import django
    django.setup()


def report(kind, **facts):
    print("IO_BOUND "+json.dumps(dict(kind=kind, **facts)), flush=True)


class ClientTests(unittest.TestCase):
    def test_actual_pins_and_inactive_helpers(self):
        expected={"Django":"5.2.18","redis":"7.0.1","channels_redis":"4.3.0",
                  "psycopg2-binary":"2.9.11","requests":"2.34.2","botocore":"1.40.71"}
        self.assertEqual({p:version(p) for p in expected},expected)
        for value in (0,-1,True,float("inf")):
            with self.assertRaises(ValueError):
                redis_socket_options(connect_seconds=value,read_seconds=.1,max_connections=1,retries=0)
        with self.assertRaises(ValueError):
            channels_redis_host("redis://127.0.0.1:1/15",connect_seconds=.1,read_seconds=.1,max_connections=1,retries=0)
        report("pins",versions=expected,production_wiring=False)

    def test_redis_read_attempt_budget_and_recovery(self):
        import redis
        def command_stall(peer,number,server):redis_replies(peer,number,server,stall_ping=True)
        for stage,retries in (("handshake",1),("command",0),("command",1)):
            with Loopback(blackhole if stage=="handshake" else command_stall) as server:
                client=redis.Redis(host="127.0.0.1",port=server.port,
                    **redis_socket_options(connect_seconds=.1,read_seconds=.08,max_connections=1,retries=retries))
                began=time.monotonic()
                try:
                    with self.assertRaises(redis.exceptions.TimeoutError):client.ping()
                    elapsed=time.monotonic()-began
                    self.assertLess(elapsed,2)
                    self.assertEqual(server.count,1 if stage=="handshake" else retries+1)
                    self.assertFalse(client.connection_pool._in_use_connections)
                    report("redis_read",stage=stage,retries=retries,attempts=server.count,elapsed_ms=round(elapsed*1000,2))
                finally:client.close();client.connection_pool.disconnect()
        def fail_once(peer, number, server):
            redis_replies(peer,number,server,stall_ping=number==1)
        with Loopback(fail_once) as server:
            client=redis.Redis(host="127.0.0.1",port=server.port,
                **redis_socket_options(connect_seconds=.1,read_seconds=.08,max_connections=1,retries=1))
            try:
                self.assertTrue(client.ping())
                self.assertEqual(server.count,2)
            finally:client.close();client.connection_pool.disconnect()
        report("redis_recovery",reconnected=True)

    def test_redis_connect_deadline_and_pool_exhaustion(self):
        import redis
        fake=Mock()
        def timed_connect(address):
            time.sleep(.04)
            raise socket.timeout()
        fake.connect.side_effect=timed_connect
        options=redis_socket_options(connect_seconds=.04,read_seconds=.1,max_connections=1,retries=0)
        options.pop("max_connections")  # Pool argument, not a standalone connection argument.
        connection=redis.Connection(host="127.0.0.1",port=1,**options)
        with patch("redis.connection.socket.getaddrinfo",return_value=[(socket.AF_INET,socket.SOCK_STREAM,0,"",("127.0.0.1",1))]), \
             patch("redis.connection.socket.socket",return_value=fake):
            began=time.monotonic()
            with self.assertRaises(redis.exceptions.TimeoutError):connection.connect()
            self.assertLess(time.monotonic()-began,1)
            fake.settimeout.assert_any_call(.04)
        with Loopback(redis_replies) as server:
            pool=redis.ConnectionPool(host="127.0.0.1",port=server.port,
                **redis_socket_options(connect_seconds=.1,read_seconds=.1,max_connections=1,retries=0))
            held=pool.get_connection()
            try:
                began=time.monotonic()
                with self.assertRaises(redis.exceptions.ConnectionError):pool.get_connection()
                self.assertLess(time.monotonic()-began,.5)
            finally:pool.release(held)
            client=redis.Redis(connection_pool=pool)
            try:self.assertTrue(client.ping())
            finally:client.close();pool.disconnect()
        report("redis_acquisition",exhaustion="fail_fast",recovered=True,connect_test="controlled_socket")

    def test_cached_db_read_fallback_and_persistent_outage_control(self):
        setup_django()
        from django.contrib.sessions.backends.cached_db import SessionStore
        from django.utils import timezone
        from redis.exceptions import TimeoutError as RedisTimeout
        store=SessionStore("synthetic-session-key-123456789")
        data={"_auth_user_id":"synthetic", "qa_marker":True}
        record=SimpleNamespace(session_data=store.encode(data),expire_date=timezone.now()+timedelta(hours=1))
        store._cache=Mock()
        store._cache.get.side_effect=RedisTimeout("synthetic")
        with patch.object(store,"_get_session_from_db",return_value=record):
            self.assertEqual(store.load(),data)
            store._cache.set.side_effect=RedisTimeout("synthetic")
            with self.assertRaises(RedisTimeout):store.load()
        report("session_compatibility",read_fallback=True,persistent_cache_outage="BLOCKED_existing_behavior")

    def test_django_cache_accepts_pinned_socket_and_retry_options(self):
        setup_django()
        from django.core.cache.backends.redis import RedisCache
        from redis.exceptions import TimeoutError as RedisTimeout
        with Loopback(blackhole) as server:
            cache=RedisCache(f"redis://127.0.0.1:{server.port}/0",{"OPTIONS":
                redis_socket_options(connect_seconds=.1,read_seconds=.08,max_connections=1,retries=0)})
            began=time.monotonic()
            try:
                with self.assertRaises(RedisTimeout):cache.get("synthetic")
                self.assertLess(time.monotonic()-began,2)
                pool=cache._cache.get_client().connection_pool
                self.assertFalse(pool._in_use_connections)
                report("django_cache",read_failure_bounded=True,options_supported=True)
            finally:
                for pool in cache._cache._pools.values():pool.disconnect()


class AsyncRedisTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_connect_limit_and_cancellation_cleanup(self):
        from redis.asyncio.connection import Connection
        from redis.exceptions import TimeoutError as RedisTimeout
        options=redis_socket_options(connect_seconds=.04,read_seconds=.1,max_connections=1,retries=0,asynchronous=True)
        options.pop("max_connections")
        connection=Connection(host="127.0.0.1",port=1,**options)
        async def slow_connect(**kwargs):await asyncio.sleep(2)
        began=time.monotonic()
        with patch("redis.asyncio.connection.asyncio.open_connection",side_effect=slow_connect):
            with self.assertRaises(RedisTimeout):await connection.connect()
        self.assertLess(time.monotonic()-began,1)
        await connection.disconnect()
        report("redis_async_connect",elapsed_ms=round((time.monotonic()-began)*1000,2),transport="controlled")

    @unittest.skipUnless(os.environ.get("REDIS_URL_TEST"),"Disposable Redis is supplied by Linux CI")
    async def test_channels_supported_host_deadline_reconnect_receive_and_pool(self):
        from channels_redis.core import RedisChannelLayer
        from redis.exceptions import ConnectionError as RedisConnectionError
        url=urlsplit(os.environ["REDIS_URL_TEST"])
        self.assertEqual((url.hostname,url.path,url.query),("127.0.0.1","/15",""))
        before=set(asyncio.all_tasks())
        fault=[True]
        def proxy(peer,number,server):
            if fault[0]:blackhole(peer,number,server)
            else:relay(peer,number,server,url.port)
        with Loopback(proxy) as server:
            host=channels_redis_host(f"redis://127.0.0.1:{server.port}/15",connect_seconds=.1,
                                    read_seconds=6,max_connections=1,retries=0)
            layer=RedisChannelLayer(hosts=[host],prefix="ownlobby_io_"+str(os.getpid()),capacity=2,expiry=10)
            try:
                began=time.monotonic()
                with self.assertRaises(TimeoutError):
                    await asyncio.wait_for(layer.send("qa.channel",{"type":"qa.synthetic"}),.2)
                elapsed=time.monotonic()-began
                self.assertLess(elapsed,2)
                self.assertFalse(layer.connection(0).connection_pool._in_use_connections)
                fault[0]=False
                await asyncio.wait_for(layer.send("qa.channel",{"type":"qa.synthetic"}),2)
                self.assertEqual((await asyncio.wait_for(layer.receive("qa.channel"),2))["type"],"qa.synthetic")
                await asyncio.wait_for(layer.wait_received(),2)
                channel=await layer.new_channel()
                with self.assertRaises(TimeoutError):await asyncio.wait_for(layer.receive(channel),.15)
                self.assertEqual(layer.receive_count,0)
                self.assertIsNone(layer.receive_lock)
                pool=layer.connection(0).connection_pool
                self.assertFalse(pool._in_use_connections)
                held=await pool.get_connection()
                try:
                    with self.assertRaises(RedisConnectionError):
                        await asyncio.wait_for(layer.send("qa.channel",{"type":"qa.synthetic"}),.3)
                finally:await pool.release(held)
                await asyncio.wait_for(layer.send(channel,{"type":"qa.recovered"}),2)
                self.assertEqual((await asyncio.wait_for(layer.receive(channel),2))["type"],"qa.recovered")
                report("channels",cancel_deadline_ms=200,measured_ms=round(elapsed*1000,2),
                       reconnect=True,receive_recovered=True,pool="fail_fast_after_internal_lock")
            finally:await asyncio.wait_for(layer.flush(),2)
        await asyncio.sleep(0)
        self.assertFalse(set(asyncio.all_tasks())-before-{asyncio.current_task()})


class ExternalTests(unittest.TestCase):
    @staticmethod
    def http_handler(mode):
        def handle(peer,number,server):
            request=peer.makefile("rb")
            while True:
                line=request.readline()
                if line in (b"\r\n",b""):break
            if mode=="stall":
                server.stop.wait(4)
                return
            if mode=="retry" and number==1:
                body=b"<Error><Code>SlowDown</Code></Error>"
                peer.sendall(b"HTTP/1.1 503 Slow\r\nConnection: close\r\nContent-Length: "+
                             str(len(body)).encode()+b"\r\n\r\n"+body)
                return
            body=b"fixture" if mode=="drip" else b"qa"
            peer.sendall(b"HTTP/1.1 200 OK\r\nConnection: close\r\nContent-Length: "+
                         str(len(body)).encode()+b"\r\n\r\n")
            if mode=="body_stall":
                peer.sendall(body[:1])
                server.stop.wait(4)
                return
            for byte in body:
                peer.sendall(bytes([byte]))
                if mode=="drip" and server.stop.wait(.1):break
        return handle

    def test_http_inactivity_retry_and_slow_progress_are_distinct(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        session=requests.Session()
        session.trust_env=False  # Never use real proxy/auth configuration.
        try:
            with Loopback(self.http_handler("stall")) as server:
                began=time.monotonic()
                with self.assertRaises(requests.exceptions.ReadTimeout):
                    session.get(f"http://127.0.0.1:{server.port}/qa",timeout=(.1,.08))
                elapsed=time.monotonic()-began
                self.assertLess(elapsed,2)
                report("http_inactivity",elapsed_ms=round(elapsed*1000,2),read_limit_ms=80)
            with Loopback(self.http_handler("drip")) as server:
                began=time.monotonic()
                response=session.get(f"http://127.0.0.1:{server.port}/qa",timeout=(.1,.4))
                self.assertEqual(response.content,b"fixture")
                elapsed=time.monotonic()-began
                self.assertGreater(elapsed,.4)
                self.assertLess(elapsed,3)
                report("http_slow_progress",elapsed_ms=round(elapsed*1000,2),read_limit_ms=400,whole_deadline="NOT_ENFORCED")
            session.mount("http://",HTTPAdapter(max_retries=Retry(total=1,backoff_factor=0,
                                        status_forcelist=[503],allowed_methods={"GET"})))
            with Loopback(self.http_handler("retry")) as server:
                began=time.monotonic()
                self.assertEqual(session.get(f"http://127.0.0.1:{server.port}/qa",timeout=(.1,.2)).content,b"qa")
                self.assertEqual(server.count,2)
                report("http_retry",attempts=server.count,elapsed_ms=round((time.monotonic()-began)*1000,2),methods="synthetic_GET_only")
        finally:session.close()

    def test_s3_stream_lifetime_and_pre_response_retry_budget(self):
        import boto3
        from botocore.config import Config
        from botocore.exceptions import ReadTimeoutError
        def client(server,read,attempts):
            with patch.dict(os.environ,{"AWS_CONFIG_FILE":os.devnull,"AWS_SHARED_CREDENTIALS_FILE":os.devnull,
                                        "AWS_EC2_METADATA_DISABLED":"true"},clear=True):
                return boto3.client("s3",endpoint_url=f"http://127.0.0.1:{server.port}",region_name="us-east-1",
                    aws_access_key_id="synthetic",aws_secret_access_key="synthetic",
                    config=s3_socket_config(connect_seconds=.1,read_seconds=read,attempts=attempts).merge(Config(proxies={})))
        with Loopback(self.http_handler("drip")) as server:
            api=client(server,.4,1)
            began=time.monotonic()
            try:
                body=api.get_object(Bucket="synthetic",Key="fixture")["Body"]
                try:self.assertEqual(body.read(),b"fixture")
                finally:body.close()
                elapsed=time.monotonic()-began
                self.assertGreater(elapsed,.4)
                self.assertLess(elapsed,3)
                report("s3_stream",elapsed_ms=round(elapsed*1000,2),read_limit_ms=400,whole_lifetime="UNKNOWN")
            finally:api.close()
        with Loopback(self.http_handler("stall")) as server:
            api=client(server,.08,1)
            began=time.monotonic()
            try:
                with self.assertRaises(ReadTimeoutError):api.get_object(Bucket="synthetic",Key="fixture")
                self.assertEqual(server.count,1)
                self.assertLess(time.monotonic()-began,2)
            finally:api.close()
        with Loopback(self.http_handler("body_stall")) as server:
            api=client(server,.08,2)
            try:
                body=api.get_object(Bucket="synthetic",Key="fixture")["Body"]
                began=time.monotonic()
                try:
                    with self.assertRaises(ReadTimeoutError):body.read()
                finally:body.close()
                self.assertEqual(server.count,1)  # SDK cannot replay a delivered streaming body.
                self.assertLess(time.monotonic()-began,2)
                report("s3_body_read",attempts=1,body_closed=True,automatic_replay=False)
            finally:api.close()
        with Loopback(self.http_handler("retry")) as server:
            api=client(server,.2,2)
            began=time.monotonic()
            try:
                body=api.get_object(Bucket="synthetic",Key="fixture")["Body"]
                try:self.assertEqual(body.read(),b"qa")
                finally:body.close()
                self.assertEqual(server.count,2)
                elapsed=time.monotonic()-began
                self.assertLess(elapsed,4)
                report("s3_retry",attempts=server.count,elapsed_ms=round(elapsed*1000,2),backoff="SDK_standard_unmodified")
            finally:api.close()

    def test_smtp_greeting_inactivity_without_sending_email(self):
        with Loopback(blackhole) as server:
            began=time.monotonic()
            with self.assertRaises((TimeoutError,smtplib.SMTPServerDisconnected)):
                smtplib.SMTP("127.0.0.1",server.port,timeout=.08)
            elapsed=time.monotonic()-began
            self.assertLess(elapsed,2)
            report("smtp_greeting",elapsed_ms=round(elapsed*1000,2),email_sent=False,whole_transaction="UNKNOWN")


@unittest.skipUnless(os.environ.get("DATABASE_URL_TEST"),"Disposable PostgreSQL is supplied by Linux CI")
class PostgreSQLTests(unittest.TestCase):
    def test_statement_lock_rollback_local_settings_and_owner_cleanup(self):
        setup_django()
        import psycopg2
        from psycopg2.extensions import TRANSACTION_STATUS_IDLE
        from django.db import connection, transaction, OperationalError
        url=urlsplit(os.environ["DATABASE_URL_TEST"])
        self.assertEqual((url.hostname,url.path,url.query),("127.0.0.1","/ownlobby_test",""))
        observer=psycopg2.connect(os.environ["DATABASE_URL_TEST"],connect_timeout=2,
                                  options="-c statement_timeout=3000")
        observer.autocommit=True
        def settings():
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_setting('statement_timeout'),current_setting('lock_timeout')")
                return cursor.fetchone()
        try:
            baseline=settings()
            results={}
            with transaction_timeouts(statement_ms=200,lock_ms=80):
                self.assertEqual(settings(),("200ms","80ms"))
            self.assertEqual(settings(),baseline)
            for kind,statement in (("statement","SELECT pg_sleep(2)"),("lock","SELECT pg_advisory_xact_lock(986421)")):
                if kind=="lock":
                    with observer.cursor() as cursor:cursor.execute("SELECT pg_advisory_lock(986421)")
                began=time.monotonic()
                try:
                    with self.assertRaises(OperationalError) as caught:
                        with transaction_timeouts(statement_ms=200,lock_ms=80):
                            with connection.cursor() as cursor:cursor.execute(statement)
                    elapsed=time.monotonic()-began
                    self.assertLess(elapsed,2)
                    self.assertEqual(caught.exception.__cause__.pgcode,"57014" if kind=="statement" else "55P03")
                    self.assertEqual(connection.connection.get_transaction_status(),TRANSACTION_STATUS_IDLE)
                    self.assertFalse(connection.needs_rollback)
                    self.assertEqual(settings(),baseline)
                    results[kind+"_ms"]=round(elapsed*1000,2)
                finally:
                    if kind=="lock":
                        with observer.cursor() as cursor:cursor.execute("SELECT pg_advisory_unlock(986421)")
            with transaction.atomic():
                with self.assertRaises(RuntimeError):
                    with transaction_timeouts(statement_ms=200,lock_ms=80):pass
            connection.close()  # Owning-thread normal teardown, never cross-thread force close.
            with observer.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE application_name=%s",
                               ["ownlobby_io_"+str(os.getpid())])
                self.assertEqual(cursor.fetchone()[0],0)
            report("postgresql",**results,rollback_idle=True,no_setting_leak=True,owner_sessions=0,
                   pooler_pg17_parity="UNVERIFIED",commit_rollback_network_deadline="UNKNOWN")
        finally:connection.close();observer.close()

    def test_libpq_startup_wait_is_separate_from_sql_and_pool_acquisition(self):
        import psycopg2
        with Loopback(blackhole) as server:
            began=time.monotonic()
            with self.assertRaises(psycopg2.OperationalError):
                psycopg2.connect(host="127.0.0.1",port=server.port,dbname="ownlobby_test",
                                 user="synthetic",connect_timeout=2,sslmode="disable")
            elapsed=time.monotonic()-began
            self.assertLess(elapsed,5)
            self.assertGreaterEqual(server.count,1)
            report("libpq_startup",elapsed_ms=round(elapsed*1000,2),tcp_accepted=True,pool_acquisition="UNKNOWN")
