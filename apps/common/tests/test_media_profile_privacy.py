"""Profile-media authorization regressions; no database or provider access."""
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from rest_framework.test import force_authenticate

from apps.common.media.views import download


@override_settings(
    OWNLOBBY_MEDIA_MODE='hybrid',
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'private_media': {'BACKEND': 'apps.common.media.storage.ProtectedFileSystemStorage'},
    },
    MEDIA_READ_RATE='10000/min',
)
class ProfileMediaPrivacyTests(SimpleTestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User(pk=901, username='media-owner')
        self.other = User(pk=902, username='media-viewer')
        self.profile = apps.get_model('user_profile.UserProfile')(
            pk=903, user=self.owner, avatar='synthetic/avatar.png',
            banner='synthetic/banner.png',
        )
        self.privacy = apps.get_model('user_profile.PrivacySettings')(
            user_profile=self.profile, visibility_preset='PRIVATE',
            is_private_account=False,
        )
        self.game = apps.get_model('user_profile.GameProfile')(
            pk=904, user=self.owner, visibility='PUBLIC',
            rank_image='synthetic/rank.png',
        )
        self.factory = RequestFactory()
        self.follow = self.enterContext(patch.object(
            apps.get_model('user_profile.Follow').objects, 'filter',
        ))
        self.follow.return_value.exists.return_value = False

    def check_delivery(self, obj, field, user, allowed):
        for method in ('get', 'head'):
            with self.subTest(method=method, field=field, viewer=getattr(user, 'pk', None)):
                request = getattr(self.factory, method)('/files/synthetic/', REMOTE_ADDR='127.0.0.1')
                force_authenticate(request, user=user)
                # Only record lookup and the origin boundary are substituted.
                # The actual Django field, view and authorization policy execute.
                with patch('apps.common.media.views.get_object_or_404', return_value=obj), patch(
                    'apps.common.media.views.serve_blob', return_value=HttpResponse(b'synthetic'),
                ) as origin:
                    response = download(request, obj._meta.label_lower, field, str(obj.pk))
                self.assertEqual(response.status_code, 200 if allowed else 404)
                if allowed:
                    origin.assert_called_once_with(getattr(obj, field))
                else:
                    origin.assert_not_called()
                response.close()

    def test_private_preset_denies_anonymous_and_unrelated_profile_media(self):
        for preset in ('PRIVATE', 'private'):
            self.privacy.visibility_preset = preset
            for field in ('avatar', 'banner'):
                for user in (AnonymousUser(), self.other):
                    self.check_delivery(self.profile, field, user, False)

    def test_private_account_flag_denies_even_with_public_preset(self):
        self.privacy.visibility_preset = 'PUBLIC'
        self.privacy.is_private_account = True
        for field in ('avatar', 'banner'):
            self.check_delivery(self.profile, field, AnonymousUser(), False)
            self.check_delivery(self.profile, field, self.other, False)

    def test_owner_retains_private_profile_and_game_media(self):
        for field in ('avatar', 'banner'):
            self.check_delivery(self.profile, field, self.owner, True)
        self.game.visibility = 'PRIVATE'
        self.check_delivery(self.game, 'rank_image', self.owner, True)
        self.follow.assert_not_called()

    def test_approved_follower_retains_private_profile_media(self):
        self.follow.return_value.exists.return_value = True
        for field in ('avatar', 'banner'):
            self.check_delivery(self.profile, field, self.other, True)
        self.follow.assert_called_with(follower_id=self.other.pk, following_id=self.owner.pk)

    def test_public_profile_and_public_game_presets_remain_readable(self):
        self.privacy.visibility_preset = 'PUBLIC'
        for field in ('avatar', 'banner'):
            self.check_delivery(self.profile, field, AnonymousUser(), True)
        for visibility in ('PUBLIC', 'public'):
            self.game.visibility = visibility
            self.check_delivery(self.game, 'rank_image', AnonymousUser(), True)

    def test_public_game_inherits_profile_privacy_and_follower_access(self):
        self.check_delivery(self.game, 'rank_image', AnonymousUser(), False)
        self.check_delivery(self.game, 'rank_image', self.other, False)
        self.follow.return_value.exists.return_value = True
        self.check_delivery(self.game, 'rank_image', self.other, True)
        self.follow.assert_called_with(follower_id=self.other.pk, following_id=self.owner.pk)

    def test_nonpublic_game_does_not_gain_access_from_following(self):
        self.follow.return_value.exists.return_value = True
        for visibility in ('PRIVATE', 'private', 'PROTECTED'):
            self.game.visibility = visibility
            self.check_delivery(self.game, 'rank_image', AnonymousUser(), False)
            self.check_delivery(self.game, 'rank_image', self.other, False)
            self.check_delivery(self.game, 'rank_image', self.owner, True)

    def test_inactive_follower_is_not_authorized(self):
        self.other.is_active = False
        self.follow.return_value.exists.return_value = True
        for field in ('avatar', 'banner'):
            self.check_delivery(self.profile, field, self.other, False)
        self.check_delivery(self.game, 'rank_image', self.other, False)
        self.follow.assert_not_called()
