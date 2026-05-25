"""Central visibility policy for Game Passport reads."""

from apps.user_profile.models import GameProfile


def visible_passport_visibilities(viewer, owner) -> list:
    """
    Returns allowed visibility values for viewer reading owner's passports.
    Pass result into: GameProfile.objects.filter(visibility__in=...)
    """
    if viewer is None or not getattr(viewer, "is_authenticated", False):
        return [GameProfile.VISIBILITY_PUBLIC]

    if viewer.pk == owner.pk:
        return [
            GameProfile.VISIBILITY_PUBLIC,
            GameProfile.VISIBILITY_PROTECTED,
            GameProfile.VISIBILITY_PRIVATE,
        ]

    if getattr(viewer, "is_staff", False):
        return [
            GameProfile.VISIBILITY_PUBLIC,
            GameProfile.VISIBILITY_PROTECTED,
            GameProfile.VISIBILITY_PRIVATE,
        ]

    return [GameProfile.VISIBILITY_PUBLIC, GameProfile.VISIBILITY_PROTECTED]
