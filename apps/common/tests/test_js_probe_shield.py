from django.test import SimpleTestCase, RequestFactory, override_settings

from deltacrown.middleware.bot_probe import is_bot_probe_path, BotProbeShieldMiddleware


class JsProbeShieldTests(SimpleTestCase):
    def test_known_scanner_scripts_rejected(self):
        for path in ('/bot-connect.js', '/licensor.js', '/js/lkk_ch.js',
                     '/js/antibot-client.js', '/js/qrcode_twint.js',
                     '/js/twint_ch.js', '/js/raif_ch.js'):
            with self.subTest(path=path):
                self.assertTrue(is_bot_probe_path(path))
                result = BotProbeShieldMiddleware(lambda request: None).process_request(
                    RequestFactory().get(path))
                self.assertEqual(result.status_code, 404)

    def test_normal_app_paths_pass(self):
        for path in ('/static/js/app.js', '/media/file.js', '/js/app.js',
                     '/tournaments/', '/assets/js/auth.js', '/bot-connect.jsx'):
            with self.subTest(path=path):
                self.assertFalse(is_bot_probe_path(path))

    @override_settings(BOT_PROBE_SHIELD_ENABLED=False)
    def test_shield_can_be_disabled(self):
        result = BotProbeShieldMiddleware(lambda request: None).process_request(
            RequestFactory().get('/bot-connect.js'))
        self.assertIsNone(result)
