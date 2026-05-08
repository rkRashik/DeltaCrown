"""
Signal handlers for user_profile.

Phase 12 (egress rescue): wires cache.invalidate hooks for the cached
`build_public_profile_context` payload. Any time a model that contributes
to the public-profile payload changes, we bump the per-username version
counter — an O(1) eviction of every cached variant for that profile.

Models covered:
    - UserProfile (basic profile data, bio, avatar, banner, level/xp)
    - UserProfileStats (stats section)
    - UserActivity (activity feed section)
    - SocialLink (social section, stream platforms)
    - GameProfile (games section)
    - PrivacySettings (visibility flags affect ALL roles' visible_fields)
    - HardwareGear (hardware section, owner-and-public)
    - Follow (follower-role bucket — invalidate the followee profile)
    - TeamMembership (teams render in profile body — owner's team list)
    - UserBadge (badge showcase)
    - HighlightClip / PinnedHighlight (highlight section)
    - CommunityPost (post-tab content)

Failures are logged and swallowed: cache invalidation must never break
the originating write.
"""
from __future__ import annotations

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from apps.user_profile.services.profile_context import invalidate_public_profile_cache

logger = logging.getLogger(__name__)


def _safe_invalidate(username: str | None) -> None:
    if not username:
        return
    try:
        invalidate_public_profile_cache(username)
    except Exception as exc:  # noqa: BLE001 — invalidation must never raise
        logger.warning("profile_cache_invalidate_failed user=%s err=%s", username, exc)


def _username_from_user_profile(instance) -> str | None:
    """Profile-owning models: walk to UserProfile.user.username."""
    try:
        profile = getattr(instance, 'user_profile', None)
        if profile is None:
            profile = instance  # if instance IS a UserProfile
        user = getattr(profile, 'user', None)
        return getattr(user, 'username', None)
    except Exception:
        return None


def _username_from_user_fk(instance) -> str | None:
    """Models with a direct user FK: read user.username."""
    try:
        user = getattr(instance, 'user', None)
        return getattr(user, 'username', None)
    except Exception:
        return None


# ---- Wire receivers lazily so unit tests with --keepdb / minimal apps work. ---

def _connect_receivers() -> None:
    from apps.user_profile.models import (
        UserProfile, UserProfileStats, UserActivity, PrivacySettings,
    )

    @receiver(post_save, sender=UserProfile, dispatch_uid='profile_cache:userprofile_save')
    def _userprofile_changed(sender, instance, **kwargs):  # noqa: ANN001
        _safe_invalidate(_username_from_user_profile(instance))

    @receiver(post_save, sender=UserProfileStats, dispatch_uid='profile_cache:stats_save')
    def _stats_changed(sender, instance, **kwargs):  # noqa: ANN001
        _safe_invalidate(_username_from_user_profile(instance))

    @receiver(post_save, sender=UserActivity, dispatch_uid='profile_cache:activity_save')
    def _activity_changed(sender, instance, **kwargs):  # noqa: ANN001
        _safe_invalidate(_username_from_user_profile(instance))

    @receiver(post_save, sender=PrivacySettings, dispatch_uid='profile_cache:privacy_save')
    def _privacy_changed(sender, instance, **kwargs):  # noqa: ANN001
        _safe_invalidate(_username_from_user_profile(instance))

    # Optional models — wire only if importable so this file stays robust
    # even when the DELTA_MINIMAL_TEST_APPS feature flag prunes installed apps.
    try:
        from apps.user_profile.models import SocialLink, HardwareGear

        @receiver(post_save, sender=SocialLink, dispatch_uid='profile_cache:social_save')
        @receiver(post_delete, sender=SocialLink, dispatch_uid='profile_cache:social_delete')
        def _social_changed(sender, instance, **kwargs):  # noqa: ANN001
            _safe_invalidate(_username_from_user_fk(instance))

        @receiver(post_save, sender=HardwareGear, dispatch_uid='profile_cache:gear_save')
        @receiver(post_delete, sender=HardwareGear, dispatch_uid='profile_cache:gear_delete')
        def _gear_changed(sender, instance, **kwargs):  # noqa: ANN001
            _safe_invalidate(_username_from_user_fk(instance))
    except ImportError:
        pass

    try:
        from apps.user_profile.models import Follow

        @receiver(post_save, sender=Follow, dispatch_uid='profile_cache:follow_save')
        @receiver(post_delete, sender=Follow, dispatch_uid='profile_cache:follow_delete')
        def _follow_changed(sender, instance, **kwargs):  # noqa: ANN001
            # Bump the FOLLOWEE — its follower-bucket payload may now
            # include/exclude this viewer. Followers/visitors on the
            # follower's own profile are unaffected.
            try:
                followee = getattr(instance, 'following', None)
                _safe_invalidate(getattr(followee, 'username', None))
            except Exception:
                pass
    except ImportError:
        pass

    try:
        from apps.user_profile.models import GameProfile

        @receiver(post_save, sender=GameProfile, dispatch_uid='profile_cache:gameprofile_save')
        @receiver(post_delete, sender=GameProfile, dispatch_uid='profile_cache:gameprofile_delete')
        def _game_profile_changed(sender, instance, **kwargs):  # noqa: ANN001
            _safe_invalidate(_username_from_user_profile(instance))
    except ImportError:
        pass

    try:
        from apps.user_profile.models import UserBadge

        @receiver(post_save, sender=UserBadge, dispatch_uid='profile_cache:badge_save')
        @receiver(post_delete, sender=UserBadge, dispatch_uid='profile_cache:badge_delete')
        def _badge_changed(sender, instance, **kwargs):  # noqa: ANN001
            _safe_invalidate(_username_from_user_profile(instance))
    except ImportError:
        pass

    try:
        from apps.user_profile.models import HighlightClip, PinnedHighlight

        @receiver(post_save, sender=HighlightClip, dispatch_uid='profile_cache:clip_save')
        @receiver(post_delete, sender=HighlightClip, dispatch_uid='profile_cache:clip_delete')
        def _clip_changed(sender, instance, **kwargs):  # noqa: ANN001
            _safe_invalidate(_username_from_user_fk(instance))

        @receiver(post_save, sender=PinnedHighlight, dispatch_uid='profile_cache:pin_save')
        @receiver(post_delete, sender=PinnedHighlight, dispatch_uid='profile_cache:pin_delete')
        def _pin_changed(sender, instance, **kwargs):  # noqa: ANN001
            _safe_invalidate(_username_from_user_fk(instance))
    except ImportError:
        pass

    try:
        from apps.organizations.models import TeamMembership

        @receiver(post_save, sender=TeamMembership, dispatch_uid='profile_cache:teammembership_save')
        @receiver(post_delete, sender=TeamMembership, dispatch_uid='profile_cache:teammembership_delete')
        def _teammembership_changed(sender, instance, **kwargs):  # noqa: ANN001
            # TeamMembership has either user or profile FK; try both.
            uname = _username_from_user_fk(instance)
            if not uname:
                try:
                    profile = getattr(instance, 'profile', None)
                    if profile:
                        uname = getattr(getattr(profile, 'user', None), 'username', None)
                except Exception:
                    pass
            _safe_invalidate(uname)
    except ImportError:
        pass


_connect_receivers()
