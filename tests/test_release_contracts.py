"""Release deltas only; synthetic sessions use loopback disposable PostgreSQL."""
import asyncio
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from apps.common.asgi_lifecycle import LifecycleConfig, LifecycleState


class ReadinessTests(unittest.IsolatedAsyncioTestCase):
    async def test_burst_stall_progress_recovery_and_quiescing(self):
        state = LifecycleState(LifecycleConfig(1, .1, .2, 1, 2, .5))
        started, release = asyncio.Event(), asyncio.Event()

        async def app(scope, receive, send):
            started.set()
            await release.wait()

        async def forbidden():
            self.fail("Management/rejected request must not read a body")

        async def send(message):
            pass

        http, _ = state.attach(app, app)
        task = asyncio.create_task(http({"type": "http", "path": "/work/"}, forbidden, send))

        async def probe(path="/healthz/", method="GET"):
            messages = []
            async def collect(message):
                messages.append(message)
            await http({"type": "http", "path": path, "method": method}, forbidden, collect)
            self.assertIn((b"cache-control", b"no-store"), messages[0]["headers"])
            return messages

        try:
            await asyncio.wait_for(started.wait(), 1)
            self.assertEqual((await probe())[0]["status"], 200)  # Brief full capacity is legitimate.
            self.assertEqual((await probe("/private/"))[0]["status"], 503)
            self.assertEqual((await probe(method="POST"))[0]["status"], 503)
            self.assertEqual(http.occupied_count, 1)
            with patch("apps.common.asgi_lifecycle.time.monotonic",
                       return_value=max(http.full_since, http.last_progress) + 1):
                self.assertEqual((await probe())[0]["status"], 503)
                http._progress()  # Response-body progress observed by the real forwarder.
                self.assertEqual((await probe())[0]["status"], 200)
            self.assertEqual((await probe(method="HEAD"))[1]["body"], b"")
            release.set()
            await asyncio.wait_for(task, 1)
            self.assertEqual(http.occupied_count, 0)
            self.assertEqual((await probe())[0]["status"], 200)
            state.phase = "QUIESCING"
            self.assertEqual((await probe())[0]["status"], 503)
            self.assertEqual((await probe("/private/"))[0]["status"], 503)
            self.assertFalse(http._children or http._retained)
            self.assertEqual(state.websocket_capacity, 2)
        finally:
            release.set()
            await asyncio.wait_for(task, 1)


class ReleaseSessionTests(unittest.TestCase):
    def run_offline(self, code):
        preamble = "import dotenv\ndotenv.load_dotenv=lambda *a,**k:False\ndotenv.dotenv_values=lambda *a,**k:{}\n"
        env = dict(os.environ, DATABASE_URL="postgresql://synthetic@127.0.0.1:1/unused",
                   DJANGO_SECRET_KEY="synthetic-release-only-0123456789-abcdefghijklmnopqrstuvwxyz",
                   DEBUG="False", REDIS_URL="", SENTRY_DSN="", OWNLOBBY_ASGI_LIFECYCLE_ENABLED="0")
        result = subprocess.run([sys.executable, "-c", preamble + code],
                                cwd=Path(__file__).resolve().parents[1], env=env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr[-1500:])

    @unittest.skipUnless(os.getenv("DATABASE_URL_TEST"), "Requires disposable PostgreSQL")
    def test_cached_db_sessions_survive_cache_outage_and_revoke_without_migration(self):
        # Separate process keeps minimal settings isolated from the application's
        # registry. No app migrations or external services are needed for this contract.
        code = r'''
import os
from urllib.parse import urlsplit, unquote
url=urlsplit(os.environ['DATABASE_URL_TEST'])
assert url.scheme in {'postgres','postgresql'} and url.hostname in {'127.0.0.1','localhost','::1'}
assert url.path=='/ownlobby_test'
from django.conf import settings
settings.configure(SECRET_KEY='synthetic-session-contract-only',USE_TZ=True,
    INSTALLED_APPS=['django.contrib.sessions'],
    CACHES={'default':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache'}},
    DATABASES={'default':{'ENGINE':'django.db.backends.postgresql','NAME':'ownlobby_test',
        'HOST':url.hostname,'PORT':url.port or 5432,'USER':unquote(url.username or ''),
        'PASSWORD':unquote(url.password or ''),'CONN_MAX_AGE':0}})
import django
django.setup()
from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.cached_db import SessionStore as Cached
from django.contrib.sessions.backends.db import SessionStore as Database
from django.core.cache import cache
from django.db import connection
from unittest.mock import patch
assert Session._meta.db_table not in connection.introspection.table_names()
with connection.schema_editor() as editor: editor.create_model(Session)
try:
    legacy=Cached()
    legacy.update({'_auth_user_id':'synthetic','_auth_user_backend':'synthetic.backend',
                   '_auth_user_hash':'synthetic-hash','qa_marker':True})
    legacy.save()
    old_key=legacy.session_key
    with (patch.object(cache,'get',side_effect=TimeoutError('synthetic')),
          patch.object(cache,'set',side_effect=TimeoutError('synthetic'))):
        current=Database(old_key)
        assert current['qa_marker'] and current['_auth_user_id']=='synthetic'
        current.cycle_key()
        assert not Database(old_key).load()
        assert Database(current.session_key)['qa_marker']
        new_key=current.session_key
        current.flush()
        assert not Database(new_key).load()
    assert not Session.objects.exists()
    print('SESSION_CONTRACT existing_auth_fields=True cache_independent=True revoked=True rows_remaining=0')
finally:
    with connection.schema_editor() as editor: editor.delete_model(Session)
    connection.close()
assert connection.connection is None
'''
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
        print(result.stdout.strip(), flush=True)

    def test_active_homepage_processor_never_touches_legacy_cache(self):
        self.run_offline('''
from types import SimpleNamespace
from unittest.mock import patch
from apps.common.context_homepage import homepage_context
class NoCache:
    def get(self,*a,**k): raise AssertionError('legacy cache')
with patch('apps.common.context_homepage.cache',NoCache()):
    assert homepage_context(SimpleNamespace(path='/',_ownlobby_home_v3=True))=={}
''')

    def test_default_session_backend_is_database(self):
        self.run_offline('''
import os
os.environ.pop('SESSION_ENGINE',None)
from deltacrown import settings
assert settings.SESSION_ENGINE=='django.contrib.sessions.backends.db'
print('Default DB session backend verified')
''')
