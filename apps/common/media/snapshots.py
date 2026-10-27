"""Resolve frozen roster artwork at read time without changing stored snapshots."""
from .fields import enabled


def lineup_with_current_avatars(snapshot):
    if not enabled() or not isinstance(snapshot, list):
        return snapshot
    from apps.user_profile.models import UserProfile

    def user_key(entry):
        try:
            return str(int(entry.get('user_id')))
        except (TypeError, ValueError):
            return ''

    user_ids = {user_key(e) for e in snapshot if isinstance(e, dict) and user_key(e)}
    avatars = {
        str(profile.user_id): profile.avatar.url if profile.avatar else ''
        for profile in UserProfile.objects.filter(user_id__in=user_ids).only('id', 'user_id', 'avatar')
    } if user_ids else {}
    # Missing/deleted users get no image, never the old unrestricted CDN URL.
    return [dict(e, avatar=avatars.get(user_key(e), ''))
            if isinstance(e, dict) else e for e in snapshot]
