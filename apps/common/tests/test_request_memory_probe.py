from unittest.mock import Mock, patch
from django.test import SimpleTestCase, RequestFactory
from deltacrown.middleware.request_memory_probe import RequestMemoryProbeMiddleware


class RequestMemoryProbeTests(SimpleTestCase):
    def test_disabled_does_not_read_rss(self):
        with patch.dict('os.environ', {'ENABLE_REQUEST_MEMORY_PROBE': '0'}):
            mw = RequestMemoryProbeMiddleware(lambda request: 'ok')
        with patch('deltacrown.middleware.request_memory_probe._rss_bytes') as rss:
            self.assertEqual(mw(RequestFactory().get('/private/?secret=value')), 'ok')
            rss.assert_not_called()

    def test_sample_logs_route_name_not_raw_url(self):
        with patch.dict('os.environ', {'ENABLE_REQUEST_MEMORY_PROBE': '1',
                                       'REQUEST_MEMORY_SAMPLE_EVERY': '1'}):
            mw = RequestMemoryProbeMiddleware(lambda request: 'ok')
        request = RequestFactory().get('/private/?secret=value')
        request.resolver_match = Mock(view_name='safe_test_route')
        with patch('deltacrown.middleware.request_memory_probe._rss_bytes', side_effect=[104857600, 105906176]), patch('deltacrown.middleware.request_memory_probe.logger.info') as log:
            self.assertEqual(mw(request), 'ok')
            fmt, *args = log.call_args.args
            self.assertEqual(args[0], 'safe_test_route')
            self.assertAlmostEqual(args[2], 1.0)
            self.assertNotIn('secret', fmt)

    def test_sampling_interval(self):
        with patch.dict('os.environ', {'ENABLE_REQUEST_MEMORY_PROBE': '1',
                                       'REQUEST_MEMORY_SAMPLE_EVERY': '2'}):
            mw = RequestMemoryProbeMiddleware(lambda request: 'ok')
        with patch('deltacrown.middleware.request_memory_probe._rss_bytes', return_value=1) as rss:
            mw(RequestFactory().get('/'))
            self.assertEqual(rss.call_count, 0)
            mw(RequestFactory().get('/'))
            self.assertEqual(rss.call_count, 2)
