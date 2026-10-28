"""Public game artwork browser cache policy must never cover private media."""
from unittest.mock import Mock, patch
from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse, Http404
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from apps.common.media import views


class PublicGameCacheTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = AnonymousUser()

    def test_only_explicit_public_game_artwork_has_browser_cache(self):
        for field_name in ('icon', 'logo', 'banner', 'card_image'):
            with self.subTest(field_name=field_name):
                model = Mock()
                model._meta.get_field.return_value = Mock(spec=views.MediaImageField)
                model._default_manager = Mock()
                model._meta.label_lower = 'games.game'
                obj = SimpleNamespace(pk=7)
                blob = Mock()
                response = HttpResponse(b'public artwork', content_type='image/png')
                response['Cache-Control'] = 'private, no-store'
                with patch.object(views.apps, 'get_model', return_value=model), patch.object(
                    views, 'get_object_or_404', return_value=obj
                ), patch.object(views, 'can_download', return_value=True), patch.object(
                    views, 'serve_blob', return_value=response
                ), patch.object(views, 'enabled', return_value=True):
                    setattr(obj, field_name, blob)
                    result = views.download.cls.as_view()(self.factory.get('/files/'), 'games.game', field_name, 7)
                    self.assertEqual(result.status_code, 200)
                    self.assertEqual(result['Cache-Control'], 'private, max-age=900, must-revalidate')

    def test_sensitive_records_and_errors_remain_no_store(self):
        # The pure branch in the view can be tested by comparing a gated
        # request for a private model, without connecting to storage.
        model = Mock()
        model._meta.get_field.return_value = Mock(spec=views.MediaImageField)
        model._default_manager = Mock()
        model._meta.label_lower = 'user_profile.userprofile'
        obj = SimpleNamespace(pk=1, avatar=Mock())
        response = HttpResponse(b'private', content_type='image/png')
        response['Cache-Control'] = 'private, no-store'
        with patch.object(views.apps, 'get_model', return_value=model), patch.object(
            views, 'get_object_or_404', return_value=obj
        ), patch.object(views, 'can_download', return_value=True), patch.object(
            views, 'serve_blob', return_value=response
        ), patch.object(views, 'enabled', return_value=True):
            result = views.download.cls.as_view()(self.factory.get('/files/'), 'user_profile.userprofile', 'avatar', 1)
            self.assertEqual(result['Cache-Control'], 'private, no-store')
        response = HttpResponse(b'Origin unavailable', status=503)
        response['Cache-Control'] = 'private, no-store'
        with patch.object(views.apps, 'get_model', return_value=model), patch.object(
            views, 'get_object_or_404', return_value=obj
        ), patch.object(views, 'can_download', return_value=True), patch.object(
            views, 'serve_blob', return_value=response
        ), patch.object(views, 'enabled', return_value=True):
            model._meta.label_lower = 'games.game'
            obj.card_image = Mock()
            result = views.download.cls.as_view()(self.factory.get('/files/'), 'games.game', 'card_image', 1)
            self.assertEqual(result.status_code, 503)
            self.assertEqual(result['Cache-Control'], 'private, no-store')
