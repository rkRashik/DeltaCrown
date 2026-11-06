"""Small contract and Linux process tests for the default-OFF adapter."""
import asyncio
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
import unittest
from unittest.mock import patch

from apps.common import asgi_lifecycle as lifecycle
from apps.common.daphne_server import OwnLobbyServer
from daphne.server import Server
from twisted.internet import defer

ROOT = Path(__file__).resolve().parents[1]


class ConfigTests(unittest.TestCase):
    def test_real_asgi_default_and_coordinated_activation(self):
        code = r'''
import os, socket
import dotenv
dotenv.load_dotenv=lambda *a,**k:False
dotenv.dotenv_values=lambda *a,**k:{}
original=socket.socket.connect
def forbidden(sock,address):
    if isinstance(address,tuple) and address[0] not in {'127.0.0.1','localhost','::1'}:
        raise RuntimeError("External network forbidden in ASGI wiring unit check")
    return original(sock,address)
socket.socket.connect=forbidden
from apps.common.daphne_server import OwnLobbyCLI, OwnLobbyServer
from apps.common import asgi_lifecycle as lifecycle
from unittest.mock import patch
def inspect():
    import deltacrown.asgi as entry
    from deltacrown.cutover_lockdown import CutoverLockdown
    from channels.security.websocket import OriginValidator
    assert isinstance(entry.application,CutoverLockdown)
    router=entry.application.application
    if os.environ['A10_MODE']=='off':
        assert router.application_mapping['http'] is entry.django_asgi_app
        assert isinstance(router.application_mapping['websocket'],OriginValidator)
    else:
        assert router.application_mapping['http'] is lifecycle._runtime.http
        assert lifecycle._runtime.http.application is entry.django_asgi_app
        assert isinstance(router.application_mapping['websocket'],lifecycle.WebSocketShutdownGate)
        assert isinstance(router.application_mapping['websocket'].application,OriginValidator)
mode=os.environ['A10_MODE']
if mode=='adapter':
    with patch.object(OwnLobbyServer,'run',lambda self:inspect()):
        OwnLobbyCLI().run(['-b','127.0.0.1','-p','0','-v','0','deltacrown.asgi:application'])
elif mode=='stock':
    try:inspect()
    except RuntimeError as error:
        assert 'coordinated OwnLobby Daphne launcher' in str(error)
    else:raise AssertionError('Unsafe stock/active mismatch accepted')
else:inspect()
print('A10_ASGI_WIRING '+mode+' PASS')
'''
        for mode in ("off", "stock", "adapter"):
            env = {k:os.environ[k] for k in ("PATH","SYSTEMROOT","PYTHONPATH") if k in os.environ}
            env.update(DJANGO_SETTINGS_MODULE="deltacrown.settings_media_qa",OWNLOBBY_CUTOVER_LOCKDOWN="1",
                       DATABASE_URL_TEST="postgresql://synthetic@127.0.0.1:1/ownlobby_test",
                       DATABASE_URL="postgresql://synthetic@127.0.0.1:1/unused_test",
                       DJANGO_SECRET_KEY="synthetic-a10-wiring-not-production-0123456789-abcdefghijklmnopqrstuvwxyz",
                       REDIS_URL="",SENTRY_DSN="",AWS_EC2_METADATA_DISABLED="true",
                       DISABLE_INPROCESS_MATCH_REMINDER="1",ENABLE_CELERY_WORKER="0",ENABLE_CELERY_BEAT="0",
                       COMPETITION_APP_ENABLED="1",A10_MODE=mode,
                       OWNLOBBY_ASGI_LIFECYCLE_ENABLED="0" if mode=="off" else "1",
                       OWNLOBBY_HTTP_CAPACITY="2",OWNLOBBY_DRAIN_SECONDS=".1",OWNLOBBY_CLEANUP_SECONDS=".3",
                       OWNLOBBY_DECLARED_HOST_SHUTDOWN_SECONDS="1")
            result=subprocess.run([sys.executable,"-c",code],cwd=ROOT,env=env,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr[-1600:])
            print(result.stdout.strip().splitlines()[-1],flush=True)

    def test_default_off_and_required_budgets(self):
        self.assertIsNone(lifecycle.LifecycleConfig.from_environ({}))
        with self.assertRaises(ValueError):
            lifecycle.LifecycleConfig.from_environ({"OWNLOBBY_ASGI_LIFECYCLE_ENABLED":"invalid"})
        env = dict(OWNLOBBY_ASGI_LIFECYCLE_ENABLED="1", OWNLOBBY_HTTP_CAPACITY="2",
                   OWNLOBBY_DRAIN_SECONDS=".1", OWNLOBBY_CLEANUP_SECONDS=".3",
                   OWNLOBBY_DECLARED_HOST_SHUTDOWN_SECONDS="1")
        for key in tuple(env):
            invalid = dict(env)
            invalid.pop(key)
            if key != "OWNLOBBY_ASGI_LIFECYCLE_ENABLED":
                with self.assertRaises(ValueError):
                    lifecycle.LifecycleConfig.from_environ(invalid)
        for key, value in (("OWNLOBBY_HTTP_CAPACITY", "0"), ("OWNLOBBY_DRAIN_SECONDS", "nan"),
                           ("OWNLOBBY_CLEANUP_SECONDS", "inf"),
                           ("OWNLOBBY_DECLARED_HOST_SHUTDOWN_SECONDS", ".1")):
            with self.assertRaises(ValueError):
                lifecycle.LifecycleConfig.from_environ(dict(env, **{key: value}))
        config = lifecycle.LifecycleConfig.from_environ(env)
        with self.assertRaises(RuntimeError):
            lifecycle.require_runtime(config)

    @unittest.skipUnless(sys.platform == "linux", "Bash exec contract")
    def test_launcher_gate_and_original_arguments(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            for command in ("python", "daphne"):
                shim = folder / command
                shim.write_text('#!/bin/sh\nprintf "%s\\n" "' + command + '" "$@" > "$A10_CAPTURE"\n')
                shim.chmod(0o755)
            base = dict(PATH=str(folder)+os.pathsep+os.environ["PATH"], A10_CAPTURE=str(folder/"args"),
                        PORT="12789", ENABLE_CELERY_WORKER="0", OWNLOBBY_CUTOVER_LOCKDOWN="0")
            for gate in ("0", "1"):
                subprocess.run(["bash", str(ROOT/"start.sh")], env=dict(base, OWNLOBBY_ASGI_LIFECYCLE_ENABLED=gate),
                               check=True, capture_output=True, timeout=3)
                args = (folder/"args").read_text().splitlines()
                prefix = ["daphne"] if gate == "0" else ["python", "-m", "apps.common.daphne_server"]
                self.assertEqual(args[:len(prefix)], prefix)
                self.assertEqual(args[-1], "deltacrown.asgi:application")
                self.assertEqual(args[len(prefix):len(prefix)+4], ["-b", "0.0.0.0", "-p", "12789"])


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.state = lifecycle.LifecycleState(lifecycle.LifecycleConfig(2, .03, .3, 1))
        self.releases, self.tasks = [], []

        async def app(scope, receive, send):
            pass

        self.http, self.ws = self.state.attach(app, app)
        self.runtime_patch = patch.object(lifecycle, "_runtime", self.state)
        self.runtime_patch.start()
        self.server = OwnLobbyServer(application=app, endpoints=["tcp:port=0:interface=127.0.0.1"])
        self.server.connections = {object(): {}, object(): {"application_instance": None},
                                   object(): {"disconnected": 0}}
        completed = asyncio.get_running_loop().create_future()
        completed.set_result(None)
        self.server.connections[object()] = {"application_instance": completed}

    async def test_superclass_dispatch_is_tracked_without_transport_scan(self):
        protocol = object()
        self.server.protocol_connected(protocol)
        queue = self.server.create_application(protocol, {"type":"http"})
        self.assertIsInstance(queue, asyncio.Queue)
        task = self.server.connections[protocol]["application_instance"]
        self.assertIn(task, self.server.application_tasks)
        await task
        await asyncio.sleep(0)
        self.assertNotIn(task,self.server.application_tasks)

    async def test_pinned_restart_close_and_protocol_completion_are_distinct(self):
        from daphne.ws_protocol import WebSocketProtocol
        protocol = WebSocketProtocol()
        # Exact R1 failure: Daphne's original API rejects before writing a frame.
        with self.assertRaisesRegex(Exception, "invalid close code 1012"):
            protocol.serverClose(code=1012)
        protocol.state = protocol.STATE_OPEN
        self.server.protocol_connected(protocol)
        self.server.create_application(protocol, {"type": "websocket"})
        record = self.server.websocket_protocols[protocol]
        await record.application
        await asyncio.sleep(0)
        first = self.server.kill_all_applications()
        with patch.object(protocol, "sendCloseFrame") as frame:
            await self.server.handle_reply(protocol, {"type":"websocket.close", "code":1012})
            frame.assert_called_once_with(code=1012)
        self.assertTrue(record.close_requested)
        self.assertFalse(record.closed.done())
        await asyncio.sleep(.05)  # Past the soft budget; no false task-only drain.
        self.assertFalse(first.called)
        protocol.wasClean, protocol.remoteCloseCode = True, 1012
        self.server.protocol_disconnected(protocol)
        await asyncio.wait_for(asyncio.shield(self.server._shutdown_task), 1)
        self.assertTrue(first.called)
        self.assertTrue(record.complete)
        self.assertEqual(self.state.phase, "DRAINED")

    async def test_websocket_without_protocol_close_remains_incomplete(self):
        from daphne.ws_protocol import WebSocketProtocol
        protocol = WebSocketProtocol()
        self.server.protocol_connected(protocol)
        self.server.create_application(protocol, {"type":"websocket"})
        record = self.server.websocket_protocols[protocol]
        await record.application
        first = self.server.kill_all_applications()
        await asyncio.wait_for(asyncio.shield(self.server._shutdown_task), 1)
        self.assertFalse(first.called)
        self.assertEqual(self.state.phase, "SHUTDOWN_INCOMPLETE")
        self.assertFalse(record.complete)
        # Unit fixture teardown only; never masquerades as runtime cleanup.
        record.closed.set_result(dict(clean=False, code=1006))

    async def test_failed_websocket_cleanup_cannot_acknowledge_shutdown(self):
        session = lifecycle.WebSocketSession(accepted=True, disconnect_received=True,
                                             application_finished=True, failed=True)
        async def close():
            pass
        session.close = close
        self.state.websockets.add(session)
        first = self.server.kill_all_applications()
        await asyncio.wait_for(asyncio.shield(self.server._shutdown_task), 1)
        self.assertFalse(first.called)
        self.assertEqual(self.state.phase, "SHUTDOWN_INCOMPLETE")

    async def asyncTearDown(self):
        for release in self.releases:
            release.set()
        await asyncio.wait_for(asyncio.gather(*self.tasks, return_exceptions=True), 1)
        if self.server._shutdown_task:
            await asyncio.wait_for(asyncio.shield(self.server._shutdown_task), 1)
        self.runtime_patch.stop()

    async def test_no_missing_key_failure_and_one_shutdown_operation(self):
        stopped = []
        port = type("Port", (), {"stopListening": lambda s: (stopped.append(True), defer.succeed(None))[1]})()
        self.server.listen_success(port)
        release = asyncio.Event()
        self.releases.append(release)
        task = asyncio.create_task(release.wait())
        self.tasks.append(task)
        self.server.application_tasks.add(task)
        task.add_done_callback(self.server._application_done)
        with patch.object(Server, "kill_all_applications", side_effect=AssertionError("faulty method called")):
            first = self.server.kill_all_applications()
            self.assertIs(first, self.server.kill_all_applications())
            first.cancel()  # A repeated cancellation cannot falsely acknowledge drain completion.
            self.assertTrue(self.state.quiescing)
            await asyncio.sleep(.01)
            self.assertFalse(first.called)
            release.set()
            await asyncio.wait_for(asyncio.shield(first.asFuture(asyncio.get_running_loop())), 1)
        self.assertEqual(stopped, [True])
        self.assertEqual(self.state.phase, "DRAINED")

    async def test_quiescing_rejects_before_read_or_child(self):
        self.state.phase = "QUIESCING"
        messages = []

        async def forbidden():
            self.fail("body read after quiescing")

        async def send(message):
            messages.append(message)

        await self.http({"type": "http", "path": "/healthz/"}, forbidden, send)
        self.assertEqual(messages[0]["status"], 503)
        self.assertIn((b"cache-control", b"no-store"), messages[0]["headers"])
        self.assertEqual(self.http.active_count, 0)
        await self.ws({"type": "websocket"}, forbidden, send)
        self.assertEqual(messages[-1], {"type": "websocket.close", "code": 1012})

    async def test_failure_does_not_skip_other_work_and_deadline_is_incomplete(self):
        async def failed():
            raise RuntimeError("synthetic task failure")
        failure = asyncio.create_task(failed())
        self.tasks.append(failure)
        self.server.application_tasks.add(failure)
        failure.add_done_callback(self.server._application_done)
        release = asyncio.Event()
        self.releases.append(release)
        protected = asyncio.create_task(release.wait())
        self.tasks.append(protected)
        self.http._children.add(protected)
        protected.add_done_callback(self.http._children.discard)
        first = self.server.kill_all_applications()
        await asyncio.wait_for(asyncio.shield(self.server._shutdown_task), 1)
        await asyncio.sleep(0)
        self.assertEqual(self.state.phase, "SHUTDOWN_INCOMPLETE")
        self.assertFalse(first.called)
        self.assertFalse(protected.cancelled())


@unittest.skipUnless(sys.platform == "linux" and os.environ.get("DATABASE_URL_TEST"), "Isolated Linux PostgreSQL")
class ProcessTests(unittest.TestCase):
    def test_finite_mixed_and_blocked_recovery(self):
        import psycopg2
        from urllib.parse import urlsplit
        database = os.environ["DATABASE_URL_TEST"]
        parsed = urlsplit(database)
        self.assertEqual((parsed.hostname, parsed.path, parsed.query), ("127.0.0.1", "/ownlobby_test", ""))
        observer = psycopg2.connect(database, connect_timeout=2, options="-c statement_timeout=2000")
        observer.autocommit = True
        try:
            cases=("finite",) if os.environ.get("A10_FINITE_EVIDENCE_ONLY")=="1" else ("finite", "blocked", "saturation")
            for case in cases:
                with self.subTest(case=case), tempfile.TemporaryDirectory() as folder:
                    state_file = Path(folder)/"state.json"
                    with socket.socket() as port_socket:
                        port_socket.bind(("127.0.0.1", 0))
                        port = port_socket.getsockname()[1]
                    env = dict(PATH=os.environ["PATH"], PYTHONPATH=str(ROOT)+os.pathsep+str(ROOT/"tests"),
                               PYTHONUNBUFFERED="1", DJANGO_SETTINGS_MODULE="deltacrown.settings_media_qa",
                               DATABASE_URL_TEST=database, DATABASE_URL="postgresql://synthetic@127.0.0.1:1/unused_test",
                               DJANGO_SECRET_KEY="synthetic-a10-qa-only-not-a-production-key-0123456789",
                               REDIS_URL="", SENTRY_DSN="", DISABLE_INPROCESS_MATCH_REMINDER="1",
                               ENABLE_CELERY_WORKER="0", ENABLE_CELERY_BEAT="0", ENABLE_DISCORD_BOT="0",
                               COMPETITION_APP_ENABLED="1", AWS_EC2_METADATA_DISABLED="true",
                               OWNLOBBY_ASGI_LIFECYCLE_ENABLED="1", OWNLOBBY_HTTP_CAPACITY="2" if case=="saturation" else "4",
                               A11_QA_WS_CAPACITY="2",A11_QA_STALL_SECONDS=".2",A11_QA_LAG_SECONDS=".08",
                               OWNLOBBY_DRAIN_SECONDS=".2", OWNLOBBY_CLEANUP_SECONDS=".3" if case=="blocked" else "5",
                               OWNLOBBY_DECLARED_HOST_SHUTDOWN_SECONDS="10", A10_QA_CASE=case, A10_QA_STATE=str(state_file))
                    with (Path(folder)/"child.log").open("w") as log:
                        proc = subprocess.Popen([sys.executable,"-m","apps.common.daphne_server","-b","127.0.0.1",
                                                 "-p",str(port),"-v","0","asgi_shutdown_fixture:application"],
                                                cwd=ROOT,env=env,stdout=log,stderr=log)
                        peers=[]

                        def state():
                            try:
                                return json.loads(state_file.read_text())
                            except (FileNotFoundError,json.JSONDecodeError):
                                return {}

                        def wait(predicate, seconds=6, alive=True):
                            end=time.monotonic()+seconds
                            while time.monotonic()<end:
                                if predicate(): return
                                if alive and proc.poll() is not None:
                                    self.fail("QA child exited: " + str(proc.returncode))
                                time.sleep(.02)
                            self.fail("QA deadline: "+json.dumps(state()))

                        def sessions():
                            with observer.cursor() as cursor:
                                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE application_name=%s",
                                               ["ownlobby_a10_"+str(proc.pid)])
                                return cursor.fetchone()[0]

                        def opened(path, websocket=False):
                            s=socket.create_connection(("127.0.0.1",port),timeout=2)
                            peers.append(s)
                            extra=("Upgrade: websocket\r\nConnection: Upgrade\r\nOrigin: http://localhost\r\n"
                                   "Sec-WebSocket-Version: 13\r\nSec-WebSocket-Key: MDEyMzQ1Njc4OWFiY2RlZg==\r\n") if websocket else ""
                            s.sendall((f"GET {path} HTTP/1.1\r\nHost: localhost\r\n{extra}\r\n").encode())
                            if path!="/work/":
                                header=b""
                                while not header.endswith(b"\r\n\r\n"):
                                    byte=s.recv(1)
                                    self.assertTrue(byte)
                                    self.assertLess(len(header),4096)
                                    header+=byte
                                self.assertTrue(header.startswith(b"HTTP/1.1 101" if websocket else b"HTTP/1.1 200"))
                            return s

                        keep=http.client.HTTPConnection("127.0.0.1",port,timeout=2)
                        closer=None
                        wire=dict(close_received=False,close_code=None,close_reply_sent=False,
                                  frame_valid=False,error_type=None)
                        try:
                            def ready():
                                try:
                                    keep.request("GET","/healthz/")
                                    r=keep.getresponse();r.read()
                                    return r.status==200
                                except (OSError,http.client.HTTPException):
                                    keep.close()
                                    return False
                            wait(ready,10)
                            opened("/work/")
                            wait(lambda:any(e["event"]=="work_started" for e in state().get("events",[])))
                            peak_db_sessions=sessions()
                            if case=="saturation":
                                opened("/work/")
                                wait(lambda:sum(e["event"]=="work_started" for e in state().get("events",[]))==2)
                                peak_db_sessions=max(peak_db_sessions,sessions())
                                # Raw TCP accepts while real Django work is at capacity; no HTTP bypass.
                                with socket.create_connection(("127.0.0.1",port),timeout=1):
                                    tcp_responsive=True
                                before_ticks=state()["loop_ticks"]
                                keep.request("GET","/healthz/")
                                rejected=keep.getresponse();rejected.read()
                                self.assertEqual((rejected.status,rejected.getheader("Cache-Control")),(503,"no-store"))
                                wait(lambda:"SATURATED_NO_OBSERVED_PROGRESS" in state().get("signals_seen",[]))
                                stalled=state()
                                self.assertGreater(stalled["loop_ticks"],before_ticks)
                                self.assertLess(stalled["occupancy"]["loop_lag_seconds"],.08)
                                self.assertEqual(stalled["occupancy"]["http_active"],2)
                                wait(lambda:state().get("occupancy",{}).get("http_active")==0)
                                keep.request("GET","/healthz/")
                                recovered=keep.getresponse();recovered.read()
                                self.assertEqual(recovered.status,200)
                                recovered_state=state()
                                self.assertTrue({"CAPACITY_EXHAUSTED","SATURATED_NO_OBSERVED_PROGRESS",
                                                 "LOOP_LAG_OBSERVED"}<=set(recovered_state["signals_seen"]))
                                self.assertEqual(recovered_state["phase"],"RUNNING")
                                self.assertEqual(sessions(),0)
                                print("A11_SATURATION "+json.dumps(dict(tcp_responsive=tcp_responsive,
                                      rejected_health=503,recovered_health=200,peak_db_sessions=peak_db_sessions,
                                      stalled=stalled["occupancy"],recovered=recovered_state["occupancy"],
                                      peak_loop_lag_seconds=recovered_state["peak_loop_lag_seconds"])),flush=True)
                            if case!="blocked":
                                if case=="finite":opened("/stream/")
                                ws=opened("/ws/",True)
                                def close_peer():
                                    try:
                                        def exact(count):
                                            value=b""
                                            while len(value)<count:
                                                part=ws.recv(count-len(value))
                                                if not part:raise EOFError
                                                value+=part
                                            return value
                                        head=exact(2)
                                        if head[0]!=0x88 or not 2<=head[1]<=125:
                                            return  # Close must be FIN, unmasked and a valid control-frame length.
                                        payload=exact(head[1])
                                        if head[0]&15==8:
                                            wire.update(close_received=True,frame_valid=True,
                                                        close_code=int.from_bytes(payload[:2],"big") if len(payload)>=2 else None)
                                            mask=os.urandom(4)
                                            ws.sendall(bytes([0x88,0x80|len(payload)])+mask+
                                                       bytes(v^mask[i%4] for i,v in enumerate(payload)))
                                            wire["close_reply_sent"]=True
                                    except (OSError,EOFError) as error:
                                        wire["error_type"]=type(error).__name__
                                closer=threading.Thread(target=close_peer,daemon=True);closer.start()
                            proc.send_signal(signal.SIGTERM)
                            wait(lambda:state().get("phase")!="RUNNING" and bool(state()))
                            if case!="saturation":
                                keep.request("GET","/healthz/")
                                rejected=keep.getresponse(); rejected.read()
                                self.assertEqual(rejected.status,503)
                                self.assertEqual(rejected.getheader("Cache-Control"),"no-store")
                                proc.send_signal(signal.SIGTERM)
                            if case!="blocked":
                                proc.wait(timeout=8)
                                self.assertEqual(proc.returncode,0)
                                if closer:closer.join(timeout=1)
                                final=state()
                                print("A10_PROCESS_TERMINAL "+json.dumps(dict(
                                      case=case,snapshot=final,db_sessions=sessions(),peak_db_sessions=peak_db_sessions,
                                      websocket_client=wire,
                                      slow_django_closed=any(e==dict(event="django_closed",kind="/work/")
                                                            for e in final["events"]))),flush=True)
                                self.assertEqual((final["phase"],final["children"],final["executors"],
                                                  final["slots"],final["application_tasks"]),("DRAINED",0,0,0,0))
                                names={e["event"] for e in final["events"]}
                                expected={"work_finished","ws_disconnect_observed","ws_application_returned"}
                                if case=="finite":expected.update({"stream_finalized","stream_closed"})
                                self.assertTrue(expected<=names,"Missing terminal markers: "+
                                                json.dumps(sorted(expected-names)))
                                self.assertEqual(wire,dict(close_received=True,close_code=1012,
                                                           close_reply_sent=True,frame_valid=True,error_type=None))
                                self.assertEqual(len(final["websocket_protocols"]),1)
                                protocol=final["websocket_protocols"][0]
                                self.assertEqual(protocol,dict(close_requested=True,protocol_closed=True,
                                     protocol_outcome=dict(clean=True,code=1012),
                                     application_finished=True,application_cancelled=False))
                                self.assertEqual(final["websocket_sessions"],[dict(close_requested=True,
                                     disconnect_received=True,application_finished=True,failed=False)])
                                disconnects=[e for e in final["terminal_observations"]
                                             if e["event"]=="ws_disconnect_observed"]
                                self.assertEqual([e["code"] for e in disconnects],
                                                 [protocol["protocol_outcome"]["code"]])
                                drained=next(p["elapsed_ms"] for p in final["phase_observations"]
                                             if p["phase"]=="DRAINED")
                                required=[e for e in final["terminal_observations"]
                                          if e["event"] in expected or e["event"]=="django_closed"]
                                self.assertTrue(all(e["elapsed_ms"]<=drained and
                                                    (case=="saturation" or e["phase"]=="QUIESCING")
                                                    for e in required if e["kind"]!="/healthz/"))
                                self.assertTrue(any(e==dict(event="django_closed",kind="/work/") for e in final["events"]))
                                self.assertTrue(any(e["event"]=="django_closed" and e["kind"]=="/work/"
                                                    and e["db_closed"] and e["owning_thread"]
                                                    for e in final["terminal_observations"]))
                                self.assertEqual(sessions(),0)
                                self.assertEqual((final["occupancy"]["ws_slots"],
                                                  final["occupancy"]["retained_http_cleanup"]),(0,0))
                                self.assertEqual((final["owned_tasks"],final["ws_protocol_records"],
                                                  final["ws_protocol_bindings"]),(0,0,0))
                                print("A10_PROCESS "+case+" graceful=True retained=0 ws=1012",flush=True)
                            else:
                                wait(lambda:state().get("phase")=="SHUTDOWN_INCOMPLETE")
                                final=state()
                                self.assertIsNone(proc.poll())
                                self.assertEqual((final["children"],final["executors"],sessions()),(1,1,1))
                                self.assertEqual(final["occupancy"]["retained_http_cleanup"],1)
                                print("A11_BLOCKED_RESOURCE "+json.dumps(dict(snapshot=final,
                                      db_sessions=sessions(),graceful=False)),flush=True)
                                proc.kill();proc.wait(timeout=2)
                                wait(lambda:sessions()==0,alive=False)
                                print("A10_PROCESS blocked graceful=False supervisor_kill=True retained_before=1 db_after=0",flush=True)
                        finally:
                            keep.close()
                            for s in peers:s.close()
                            if proc.poll() is None:proc.kill()
                            proc.wait(timeout=2)
                            if closer:closer.join(timeout=1)
        finally:
            observer.close()
