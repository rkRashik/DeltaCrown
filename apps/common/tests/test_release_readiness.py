"""Release guards using local memory services and disposable database fixtures."""
from datetime import timedelta
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import xml.etree.ElementTree as ET

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse
from django.template.loader import get_template, render_to_string
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import resolve, reverse
from django.utils import timezone

from apps.common.seo import build_seo, request_seo, schema_json
from apps.common import seo_views
from deltacrown.middleware.search_indexing import SearchIndexingMiddleware
from deltacrown.storage import RobustStaticFilesStorage


class SeoPolicyTests(SimpleTestCase):
    @override_settings(DEBUG=False, REQUIRE_PERSISTENT_MEDIA=True, STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}})
    def test_render_release_gate_rejects_ephemeral_media(self):
        from apps.siteui.checks import persistent_media_release_check
        self.assertEqual(persistent_media_release_check(None)[0].id, 'siteui.E001')

    def test_jsonld_cannot_close_script_or_inject_markup(self):
        value = '</script><img src=x onerror=alert(1)>&\u2028'
        encoded = schema_json({'name': value})[0]
        self.assertNotIn('<', encoded)
        self.assertNotIn('>', encoded)
        self.assertNotIn('&', encoded)
        self.assertEqual(json.loads(encoded)['name'], value)
        html = render_to_string('partials/seo_meta.html', {'seo': build_seo(schema={'name': value})})
        self.assertEqual(html.count('</script>'), 1)
        self.assertNotIn('<img', html)

    def test_canonical_switch_is_controlled_and_does_not_trust_request_host(self):
        for origin in ['https://deltacrown.xyz', 'https://ownlobby.com']:
            with self.subTest(origin=origin), override_settings(SITE_URL=origin):
                request = RequestFactory().get('/tournaments/?utm_source=qa&page=2', HTTP_HOST='www.ownlobby.com')
                seo = request_seo(request, build_seo(path='/tournaments/'))
                self.assertEqual(seo['canonical'], origin+'/tournaments/?page=2')
                self.assertEqual(seo['robots'], 'index, follow')

    def test_filter_parameters_are_parsed_and_noindexed(self):
        for query in ['%71=player', 'sort=newest', 'filter=live', 'page=bad', 'page=2&page=3', 'page='+'9'*1000]:
            request = RequestFactory().get('/teams/?'+query)
            self.assertIn('noindex', request_seo(request)['robots'])
        request = RequestFactory().get('/teams/?utm_source=search=example')
        self.assertNotIn('noindex', request_seo(request)['robots'])

    def test_private_endpoints_have_header_without_relying_on_robots(self):
        for path in ['/api/users/', '/me/settings/', '/tournaments/cup/hub/', '/account/login/', '/media/evidence.png']:
            response = SearchIndexingMiddleware(lambda r: HttpResponse('protected'))(RequestFactory().get(path))
            self.assertIn('noindex', response['X-Robots-Tag'])

    def test_robots_and_static_routes_use_selected_origin(self):
        for origin in ['https://deltacrown.xyz', 'https://ownlobby.com']:
            with override_settings(SITE_URL=origin):
                response = seo_views.robots_txt(RequestFactory().get('/robots.txt'))
                self.assertIn('Sitemap: '+origin+'/sitemap.xml', response.content.decode())
                self.assertIn('Disallow: /api/', response.content.decode())
                for row in seo_views._static_urls():
                    self.assertIsNotNone(resolve(row.loc.removeprefix(origin)))

    @override_settings(SITE_URL='https://ownlobby.com', PUBLIC_DOMAIN_REDIRECTS_ENABLED=True, ALLOWED_HOSTS=['deltacrown.xyz', 'www.ownlobby.com'])
    def test_redirects_only_public_successful_anonymous_html(self):
        middleware = SearchIndexingMiddleware(lambda r: HttpResponse('<html>Public</html>'))
        request = RequestFactory().get('/tournaments/?page=2', HTTP_HOST='deltacrown.xyz')
        request.user = AnonymousUser()
        result = middleware(request)
        self.assertEqual(result.status_code, 301)
        self.assertEqual(result['Location'], 'https://ownlobby.com/tournaments/?page=2')
        self.assertEqual(middleware(RequestFactory().get('/account/login/', HTTP_HOST='www.ownlobby.com')).status_code, 301)
        self.assertEqual(middleware(RequestFactory().get('/account/login/', HTTP_HOST='deltacrown.xyz')).status_code, 200)
        for path in ['/api/tournaments/', '/account/google/callback/', '/tournaments/qa/hub/', '/ws/homepage/live/']:
            self.assertEqual(middleware(RequestFactory().get(path, HTTP_HOST='deltacrown.xyz')).status_code, 200)
        for request in [RequestFactory().post('/tournaments/', HTTP_HOST='deltacrown.xyz'), RequestFactory().get('/tournaments/', HTTP_HOST='deltacrown.xyz')]:
            request.user = SimpleNamespace(is_authenticated=True)
            self.assertEqual(middleware(request).status_code, 200)
        for body in ['<meta name="robots" content="noindex, follow">', '<html>private</html>']:
            response = HttpResponse(body)
            if body.endswith('private</html>'):
                response.status_code = 403
            self.assertNotEqual(SearchIndexingMiddleware(lambda r: response)(RequestFactory().get('/teams/qa/', HTTP_HOST='www.ownlobby.com')).status_code, 301)

    @override_settings(SITE_URL='https://ownlobby.com', PUBLIC_DOMAIN_REDIRECTS_ENABLED=False)
    def test_redirects_remain_disabled_by_default(self):
        result = SearchIndexingMiddleware(lambda r: HttpResponse('public'))(RequestFactory().get('/', HTTP_HOST='www.ownlobby.com'))
        self.assertEqual(result.status_code, 200)

    def test_four_reachable_broken_templates_now_compile(self):
        for path in ['ecommerce/cart.html', 'ecommerce/product_detail.html', 'economy/wallet_dashboard.html', 'tournaments/groups/standings.html']:
            self.assertIsNotNone(get_template(path))

    def test_static_cycles_are_exposed_instead_of_suppressed(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'cycle.css').write_text('@import url("cycle.css");')
            storage = RobustStaticFilesStorage(location=folder)
            results = list(storage.post_process({'cycle.css': (FileSystemStorage(location=folder), 'cycle.css')}))
            self.assertTrue(any(isinstance(result[2], RuntimeError) for result in results))

    def test_explicit_websocket_origins_support_both_existing_formats(self):
        from apps.tournaments.realtime.consumers import TournamentConsumer
        from apps.match_engine.consumers import MatchConsumer
        for value in ['https://ownlobby.com,https://deltacrown.xyz', ['https://ownlobby.com', 'https://deltacrown.xyz']]:
            with override_settings(WS_ALLOWED_ORIGINS=value):
                self.assertEqual(TournamentConsumer.get_allowed_origins(), ['https://ownlobby.com', 'https://deltacrown.xyz'])
                self.assertEqual(MatchConsumer.get_allowed_origins(), ['https://ownlobby.com', 'https://deltacrown.xyz'])

    def test_provider_routes_and_google_discord_callback_origins_remain_compatible(self):
        from apps.accounts.views import _build_google_redirect_uri, _build_discord_redirect_uri
        paths = {
            'account:google_callback': '/account/google/callback/',
            'account:discord_callback': '/account/discord/callback/',
            'user_profile:riot_oauth_callback': '/api/oauth/riot/callback/',
            'user_profile:epic_oauth_callback': '/api/oauth/epic/callback/',
            'user_profile:steam_openid_callback': '/api/oauth/steam/callback/',
        }
        for name, path in paths.items():
            self.assertEqual(reverse(name), path)
        for origin in ['https://deltacrown.xyz', 'https://ownlobby.com']:
            with override_settings(SITE_URL=origin):
                request = RequestFactory().get('/', HTTP_HOST='ownlobby.com')
                self.assertEqual(_build_google_redirect_uri(request), origin+paths['account:google_callback'])
                self.assertEqual(_build_discord_redirect_uri(request), origin+paths['account:discord_callback'])


class PublicSitemapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user('release_owner', 'release_owner@example.com', 'qa-pass')
        cls.owner.profile.bio = 'Public competitive profile'
        cls.owner.profile.save(update_fields=['bio'])
        cls.second = User.objects.create_user('release_other', 'release_other@example.com', 'qa-pass')
        cls.second.profile.bio = 'Another public profile'
        cls.second.profile.save(update_fields=['bio'])

    def locations(self, section, query=''):
        response = self.client.get(reverse('sitemap_section', kwargs={'section': section})+query)
        self.assertEqual(response.status_code, 200, response.content[:100])
        tree = ET.fromstring(response.content)
        return [x.text for x in tree.findall('.//{*}loc')]

    @override_settings(SITE_URL='https://ownlobby.com')
    def test_profiles_exclude_private_accounts_private_presets_and_inactive_users(self):
        privacy = self.second.profile.privacy_settings
        privacy.is_private_account = True
        privacy.save(update_fields=['is_private_account'])
        urls = self.locations('profiles')
        self.assertIn('https://ownlobby.com/@release_owner/', urls)
        self.assertNotIn('https://ownlobby.com/@release_other/', urls)
        privacy.is_private_account = False
        privacy.visibility_preset = 'PRIVATE'
        privacy.save()
        self.assertNotIn('https://ownlobby.com/@release_other/', self.locations('profiles'))
        self.owner.is_active = False
        self.owner.save(update_fields=['is_active'])
        self.assertEqual(self.locations('profiles'), [])

    @patch('apps.common.seo_views.SITEMAP_PAGE_SIZE', 1)
    def test_pagination_is_discoverable_and_does_not_silently_truncate(self):
        self.assertEqual(len(self.locations('profiles')), 1)
        self.assertEqual(len(self.locations('profiles', '?page=2')), 1)
        index = self.client.get('/sitemap.xml')
        self.assertContains(index, 'sitemap-profiles.xml?page=2')
        self.assertEqual(self.client.get('/sitemap-profiles.xml?page=3').status_code, 404)
        self.assertEqual(self.client.get('/sitemap-profiles.xml?page=-1').status_code, 404)

    def test_tournament_sitemap_excludes_drafts_archives_and_deleted_records(self):
        from apps.games.models import Game
        from apps.tournaments.models import Tournament
        game = Game.objects.create(name='Readiness Game', slug='readiness-game', short_code='RDY', category='OTHER')
        now = timezone.now()
        for status in ['draft', 'pending_approval', 'published', 'archived']:
            Tournament.objects.create(name=status, slug='release-'+status, organizer=self.owner, game=game,
                participation_type='solo', status=status, max_participants=16,
                registration_start=now, registration_end=now+timedelta(days=1), tournament_start=now+timedelta(days=2))
        urls = self.locations('tournaments')
        self.assertEqual(len(urls), 1)
        self.assertTrue(urls[0].endswith('/tournaments/release-published/'))

    def test_team_sitemap_only_contains_active_public_meaningful_teams(self):
        from apps.organizations.models import Team
        for visibility in ['PUBLIC', 'PRIVATE', 'UNLISTED']:
            Team.objects.create(name='Release '+visibility, slug='release-'+visibility.lower(), created_by=self.owner,
                game_id=1, region='BD', visibility=visibility, description='Competitive roster', status='ACTIVE')
        urls = self.locations('teams')
        self.assertEqual(len(urls), 1)
        self.assertTrue(urls[0].endswith('/teams/release-public/'))

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', SITE_URL='https://ownlobby.com', DEFAULT_FROM_EMAIL='DeltaCrown <noreply@deltacrown.xyz>')
    def test_password_reset_and_otp_keep_verified_sender_but_use_canonical_links(self):
        from apps.accounts.emails import send_otp_email
        response = self.client.post(reverse('account:password_reset'), {'email': self.owner.email})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('https://ownlobby.com/account/reset/', mail.outbox[0].body)
        self.assertIn('OwnLobby', mail.outbox[0].subject)
        self.assertIn('noreply@deltacrown.xyz', mail.outbox[0].from_email)
        self.assertTrue(mail.outbox[0].from_email.startswith('OwnLobby <'))
        send_otp_email(self.owner, '123456')
        self.assertIn('https://ownlobby.com', mail.outbox[-1].body)
        self.assertNotIn('List-Unsubscribe', mail.outbox[-1].extra_headers)

    def test_newsletter_does_not_claim_success_or_collect_addresses(self):
        response = self.client.post(reverse('siteui:newsletter_subscribe'), {'email': self.owner.email})
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()['success'])

    def test_draft_detail_and_room_require_existing_organizer_access(self):
        from apps.games.models import Game
        from apps.tournaments.models import Tournament
        from apps.tournaments.security.visibility import can_join_tournament_room, can_receive_private_event
        game = Game.objects.create(name='Draft QA', slug='draft-qa', short_code='DRQA', category='OTHER')
        now = timezone.now()
        tournament = Tournament.objects.create(name='Private draft QA', slug='private-draft-qa', organizer=self.owner, game=game,
            participation_type='solo', status='draft', max_participants=16, registration_start=now,
            registration_end=now+timedelta(days=1), tournament_start=now+timedelta(days=2))
        response = self.client.get(reverse('tournaments:detail', kwargs={'slug': tournament.slug}))
        self.assertEqual(response.status_code, 404)
        self.assertFalse(can_join_tournament_room(self.second, tournament.pk))
        self.assertTrue(can_join_tournament_room(self.owner, tournament.pk))
        self.assertFalse(can_join_tournament_room(self.owner, tournament.pk+1000))
        self.assertFalse(can_receive_private_event(self.second, tournament.pk, {'tournament_id': tournament.pk, 'registration_id': 123}))
        self.assertTrue(can_receive_private_event(self.owner, tournament.pk, {'tournament_id': tournament.pk, 'registration_id': 123}))
        self.assertFalse(can_receive_private_event(self.owner, tournament.pk, {'tournament_id': tournament.pk+1}))

    def test_profile_wallet_sync_locks_rows_without_changing_the_ledger(self):
        from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
        from apps.user_profile.services.economy_sync import sync_wallet_to_profile
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=self.owner.profile)
        DeltaCrownTransaction.objects.create(wallet=wallet, amount=125,
            reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST, cached_balance_after=125,
            idempotency_key='release-sync-regression')
        before = list(wallet.transactions.values_list('pk', 'amount', 'reason', 'idempotency_key'))
        sync_wallet_to_profile(wallet.pk)
        sync_wallet_to_profile(wallet.pk)
        wallet.refresh_from_db()
        self.owner.profile.refresh_from_db()
        self.assertEqual(wallet.cached_balance, 125)
        self.assertEqual(self.owner.profile.deltacoin_balance, 125)
        self.assertEqual(list(wallet.transactions.values_list('pk', 'amount', 'reason', 'idempotency_key')), before)
