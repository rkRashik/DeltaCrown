"""Signal handlers for keeping passport references consistent."""

from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.db.models import Q

from apps.user_profile.models import GameProfile
from apps.user_profile.models.about import ProfileAboutItem
from apps.user_profile.models.showcase import ProfileShowcase


@receiver(post_delete, sender=GameProfile)
def cleanup_passport_references(sender, instance, **kwargs):
    """
    Remove stale profile references when a game passport is deleted.

    This prevents orphan integer/generic references in showcase/about records.
    """
    ProfileShowcase.objects.filter(
        user_profile__user_id=instance.user_id,
        featured_passport_id=instance.id,
    ).update(featured_passport_id=None)

    ProfileAboutItem.objects.filter(
        user_profile__user_id=instance.user_id,
        item_type=ProfileAboutItem.TYPE_GAME,
        source_id=instance.id,
    ).filter(
        Q(source_model__iexact="GameProfile")
        | Q(source_model__iexact="apps.user_profile.models.GameProfile")
        | Q(source_model__iexact="user_profile.GameProfile")
    ).update(source_model="", source_id=None, is_active=False)
