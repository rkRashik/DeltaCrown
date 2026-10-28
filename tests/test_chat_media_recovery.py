"""Regression: chat history never reuses stale Cloudinary CDN avatar URLs."""
import unittest
from types import SimpleNamespace

from apps.match_engine.chat_media import hydrate_history_avatars


class AvatarField:
    def __init__(self, url):
        self.url = url

    def __bool__(self):
        return True


class HistoryRecoveryTests(unittest.TestCase):
    def test_rehydrates_present_avatar_without_mutating_profile(self):
        messages = [{"user_id": 4, "avatar_url": "https://res.cloudinary.com/stale/avatar.png"}]
        profile = SimpleNamespace(avatar=AvatarField("/media/record/user_profile.userprofile/avatar/45/"))
        result = hydrate_history_avatars(messages, {4: profile})
        self.assertEqual(result[0]["avatar_url"], "/media/record/user_profile.userprofile/avatar/45/")

    def test_missing_and_deleted_users_never_replay_old_cdn(self):
        messages = [
            {"user_id": 4, "avatar_url": "https://res.cloudinary.com/stale/x.png"},
            {"user_id": 0, "avatar_url": "https://res.cloudinary.com/stale/y.png"},
        ]
        result = hydrate_history_avatars(messages, {})
        self.assertEqual([x["avatar_url"] for x in result], ["", ""])

    def test_external_and_protocol_relative_urls_are_rejected(self):
        for url in ("https://example.com/stale.png", "//example.com/stale.png", ""):
            with self.subTest(url=url):
                msg = [{"user_id": 2, "avatar_url": "https://res.cloudinary.com/stale/x.png"}]
                hydrate_history_avatars(msg, {2: SimpleNamespace(avatar=AvatarField(url))})
                self.assertEqual(msg[0]["avatar_url"], "")

    def test_field_url_failure_fails_closed(self):
        class BrokenAvatar:
            @property
            def url(self):
                raise ValueError("not saved")
            def __bool__(self):
                return True
        msg = [{"user_id": 2, "avatar_url": "https://res.cloudinary.com/stale/x.png"}]
        hydrate_history_avatars(msg, {2: SimpleNamespace(avatar=BrokenAvatar())})
        self.assertEqual(msg[0]["avatar_url"], "")


if __name__ == "__main__":
    unittest.main()
